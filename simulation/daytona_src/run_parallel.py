# daytona_infra/src/run_parallel.py
"""
Parallel Daytona sandbox orchestrator for the Game Theory Simulator.

- Reads the scenario and actor dossiers produced by the orchestration layer.
- Creates N sandboxes (default N=10), uploads files, runs the simulation loop,
  and downloads the per‑run artifacts.
- Uses the Daytona Python SDK for sandbox lifecycle management
  [web:10][web:5].
- Executes the agent logic inside each sandbox via `process.exec`
  [web:8][web:9].
"""

import os
import json
import time
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from daytona_sdk import Daytona, DaytonaConfig, CreateSandboxBaseParams, SessionExecuteRequest

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

# -------------------- Configuration --------------------
# Adjust these paths if your repo layout differs.
ORCHESTRATION_OUT = ROOT_DIR / "orchestration" / "output"
SIMULATION_RUNS = ROOT_DIR / "simulation" / "runs"
ANALYSIS_INCOMING = ROOT_DIR / "analysis" / "incoming"
SIMULATION_RUNS.mkdir(parents=True, exist_ok=True)
ANALYSIS_INCOMING.mkdir(parents=True, exist_ok=True)

# Number of parallel simulations to launch for a given case study.
NUM_SIMS = 10  # <-- change this to scale up/down

# Daytona client initialization – replace with your API key or
# set the DAYTONA_API_KEY environment variable.
daytona = Daytona(DaytonaConfig())  # reads DAYTONA_API_KEY from env [web:2]

SANDBOX_ENV_KEYS = [
    "ANTHROPIC_API_KEY",
    "SIM_MODEL",
    "SIM_MAX_TOKENS",
]

# -------------------- Helper Functions --------------------
def load_json(path: Path) -> dict:
    """Utility to load a JSON file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def upload_file(sandbox, local_path: Path, remote_path: str):
    """Copy a local file into the sandbox workspace."""
    sandbox.fs.upload_file(str(remote_path), local_path.read_text(encoding="utf-8"))


def get_sandbox_env() -> dict:
    """Pass through the simulation env vars the sandbox actually needs."""
    env = {}
    for key in SANDBOX_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def write_live_snapshot(run_id: str, decision_log: list, snapshot_idx: int):
    """Write a unique live snapshot for the analysis layer to ingest."""
    snapshot = {
        "simulation_id": run_id,
        "status": "running",
        "events_seen": len(decision_log),
        "last_event": decision_log[-1] if decision_log else None,
        "decision_log": decision_log,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    target = ANALYSIS_INCOMING / f"{run_id}_tick_{snapshot_idx:04d}.json"
    target.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def try_download_json(sandbox, remote_path: str):
    """Download JSON from the sandbox when present; return None otherwise."""
    try:
        return json.loads(sandbox.fs.download_file(remote_path))
    except Exception:
        return None

def run_one_simulation(run_id: str, scenario: dict, dossiers: dict, agent_script: str) -> dict:
    """
    Spin up a single Daytona sandbox, run the simulation, and return the result JSON.
    """
    print(f"[{run_id}] 🚀 Creating sandbox...")
    sandbox = daytona.create(
        CreateSandboxBaseParams(language="python", env_vars=get_sandbox_env())
    )

    try:
        # 1️⃣ Upload static assets needed by every simulation
        upload_file(sandbox, ORCHESTRATION_OUT / "scenario.json", "/workspace/scenario.json")
        upload_file(sandbox, Path(agent_script), "/workspace/simulation_loop.py")

        # 2️⃣ Upload each actor's dossier into /workspace/dossiers/
        sandbox.process.exec("mkdir -p /workspace/dossiers")
        for actor_id, dossier_data in dossiers.items():
            dossier_path = Path(f"/workspace/dossiers/{actor_id}.json")
            sandbox.fs.upload_file(str(dossier_path), json.dumps(dossier_data, indent=2))

        # 3️⃣ Run the agent loop inside a background session so we can poll the
        # decision log while the simulation is still running.
        print(f"[{run_id}] ▶️ Starting simulation loop...")
        session_id = f"session-{run_id}-{uuid.uuid4().hex[:8]}"
        sandbox.process.create_session(session_id)
        exec_res = sandbox.process.execute_session_command(
            session_id,
            SessionExecuteRequest(
                command=(
                    "python -m pip install anthropic > /tmp/pip_install.log 2>&1 && "
                    "python /workspace/simulation_loop.py"
                ),
                run_async=True,
            ),
            timeout=300,
        )

        run_dir = SIMULATION_RUNS / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        last_log = None
        snapshot_idx = 0
        command_id = exec_res.cmd_id

        while True:
            command = sandbox.process.get_session_command(session_id, command_id)
            live_log = try_download_json(sandbox, "/workspace/decision_log.json")

            if live_log is not None and live_log != last_log:
                snapshot_idx += 1
                last_log = live_log
                (run_dir / "decision_log.json").write_text(
                    json.dumps(live_log, indent=2),
                    encoding="utf-8",
                )
                write_live_snapshot(run_id, live_log, snapshot_idx)

            if command.exit_code is not None:
                if command.exit_code != 0:
                    raise RuntimeError(
                        f"Simulation loop failed with exit code {command.exit_code}"
                    )
                break

            time.sleep(2)

        # 4️⃣ Pull back the artifacts the analysis layer expects
        result_json_str = sandbox.fs.download_file("/workspace/result.json")
        decision_log_str = sandbox.fs.download_file("/workspace/decision_log.json")

        # 5️⃣ Persist locally under simulation/runs/<run_id>/
        (run_dir / "result.json").write_text(result_json_str, encoding="utf-8")
        (run_dir / "decision_log.json").write_text(decision_log_str, encoding="utf-8")
        (ANALYSIS_INCOMING / f"{run_id}_final.json").write_text(
            result_json_str,
            encoding="utf-8",
        )

        print(f"[{run_id}] ✅ Finished – artifacts saved to {run_dir}")
        return json.loads(result_json_str)

    finally:
        # Always clean up the sandbox to avoid leaking resources
        print(f"[{run_id}] 🗑️ Removing sandbox...")
        daytona.remove(sandbox)  # [web:10]

# -------------------- Main Execution --------------------
def main():
    # Load the scenario and dossiers produced by the orchestration layer
    scenario = load_json(ORCHESTRATION_OUT / "scenario.json")
    dossier_dir = ORCHESTRATION_OUT / "dossiers"
    dossiers = {
        f.stem: json.load(f.open("r", encoding="utf-8"))
        for f in dossier_dir.glob("*.json")
    }

    # Point to the agent logic that will live inside each sandbox
    agent_script_path = str((ROOT_DIR / "simulation" / "src" / "simulation_loop.py").resolve())

    print(f"🔧 Loaded scenario '{scenario.get('scenario_id')}' with {len(dossiers)} actors.")
    print(f"🚦 Launching {NUM_SIMS} parallel simulations...")

    start = time.time()
    results = []

    # Use a thread pool to run simulations concurrently.
    # Daytona provisions sandboxes quickly (~90 ms each) so this scales well [web:7].
    with ThreadPoolExecutor(max_workers=NUM_SIMS) as executor:
        future_to_run = {
            executor.submit(
                run_one_simulation,
                f"run_{str(i).zfill(3)}",   # e.g., run_000, run_001, …
                scenario,
                dossiers,
                agent_script_path,
            ): i
            for i in range(NUM_SIMS)
        }

        for future in as_completed(future_to_run):
            run_idx = future_to_run[future]
            try:
                result = future.result()
                results.append(result)
                print(f"✅ Run {run_idx} completed with payoff: {result.get('outcomes')}")
            except Exception as exc:
                print(f"❌ Run {run_idx} generated an exception: {exc}")

    elapsed = time.time() - start
    print(f"\n🏁 All {NUM_SIMS} simulations finished in {elapsed:.1f}s.")
    print(f"📁 Results are available under {SIMULATION_RUNS.resolve()}")

    # Optional: write a manifest that lists all completed run IDs for the analysis layer
    manifest = {
        "scenario_id": scenario.get("scenario_id"),
        "num_runs": NUM_SIMS,
        "run_ids": [f"run_{str(i).zfill(3)}" for i in range(NUM_SIMS)],
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (SIMULATION_RUNS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"🗒️ Manifest written to {SIMULATION_RUNS / 'manifest.json'}")

if __name__ == "__main__":
    main()