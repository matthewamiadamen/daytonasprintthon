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
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from daytona_sdk import Daytona, DaytonaConfig, CreateSandboxParams  # [web:10]

# -------------------- Configuration --------------------
# Adjust these paths if your repo layout differs.
ORCHESTRATION_OUT = Path("../orchestration/output")
SIMULATION_RUNS = Path("../simulation/runs")
SIMULATION_RUNS.mkdir(parents=True, exist_ok=True)

# Number of parallel simulations to launch for a given case study.
NUM_SIMS = 10  # <-- change this to scale up/down

# Daytona client initialization – replace with your API key or
# set the DAYTONA_API_KEY environment variable.
daytona = Daytona(DaytonaConfig())  # reads DAYTONA_API_KEY from env [web:2]

# -------------------- Helper Functions --------------------
def load_json(path: Path) -> dict:
    """Utility to load a JSON file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def upload_file(sandbox, local_path: Path, remote_path: str):
    """Copy a local file into the sandbox workspace."""
    sandbox.fs.upload_file(str(remote_path), local_path.read_text(encoding="utf-8"))

def run_one_simulation(run_id: str, scenario: dict, dossiers: dict, agent_script: str) -> dict:
    """
    Spin up a single Daytona sandbox, run the simulation, and return the result JSON.
    """
    print(f"[{run_id}] 🚀 Creating sandbox...")
    sandbox = daytona.create(CreateSandboxParams(language="python"))

    try:
        # 1️⃣ Upload static assets needed by every simulation
        upload_file(sandbox, ORCHESTRATION_OUT / "scenario.json", "/workspace/scenario.json")
        upload_file(sandbox, Path(agent_script), "/workspace/simulation_loop.py")

        # 2️⃣ Upload each actor's dossier into /workspace/dossiers/
        sandbox.process.exec("mkdir -p /workspace/dossiers")
        for actor_id, dossier_data in dossiers.items():
            dossier_path = Path(f"/workspace/dossiers/{actor_id}.json")
            sandbox.fs.upload_file(str(dossier_path), json.dumps(dossier_data, indent=2))

        # 3️⃣ Run the agent loop inside the sandbox
        print(f"[{run_id}] ▶️ Starting simulation loop...")
        exec_res = sandbox.process.exec(
            "python /workspace/simulation_loop.py",
            cwd="/workspace",
            timeout=300,  # 5 minutes should be plenty for a short game
        )
        if exec_res.exit_code != 0:
            raise RuntimeError(f"Simulation loop failed: {exec_res.result}")

        # 4️⃣ Pull back the artifacts the analysis layer expects
        result_json_str = sandbox.fs.download_file("/workspace/result.json")
        decision_log_str = sandbox.fs.download_file("/workspace/decision_log.json")

        # 5️⃣ Persist locally under simulation/runs/<run_id>/
        run_dir = SIMULATION_RUNS / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "result.json").write_text(result_json_str, encoding="utf-8")
        (run_dir / "decision_log.json").write_text(decision_log_str, encoding="utf-8")

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
    agent_script_path = str(Path("../simulation/src/simulation_loop.py").resolve())

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