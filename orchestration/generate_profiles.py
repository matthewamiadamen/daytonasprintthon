#!/usr/bin/env python3
"""
Agent Profile Generator
=======================

Generates structured agent profiles for competitive scenarios.
Domain-agnostic: works for airlines, tech companies, nations, etc.

Called by orchestrator.py after scenario_config_builder.py produces
the scenario_config.json that this module consumes.

Usage (standalone):
    python generate_profiles.py --scenario <scenario_config.json> --output <output_dir>

Usage (programmatic):
    from generate_profiles import AgentProfileGenerator
    gen = AgentProfileGenerator(scenario_config_dict)
    profiles = gen.generate_all_profiles()
"""

import json
import argparse
from datetime import datetime
from typing import Any
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class AgentProfile:
    """Structured profile for a competitive agent."""
    id: str
    archetype: str
    role_description: str
    market_position: str
    resource_constraints: list[str] = field(default_factory=list)
    competitive_advantages: list[str] = field(default_factory=list)
    behavioral_traits: list[str] = field(default_factory=list)
    decision_variables: list[dict[str, Any]] = field(default_factory=list)
    objectives: list[dict[str, Any]] = field(default_factory=list)
    utility_function: dict[str, Any] = field(default_factory=dict)
    information_access: dict[str, list[str]] = field(default_factory=dict)
    risk_profile: dict[str, Any] = field(default_factory=dict)
    rationality_bounds: dict[str, Any] = field(default_factory=dict)


class AgentProfileGenerator:
    """Generates agent profiles from scenario configuration."""

    def __init__(self, scenario_config: dict[str, Any]):
        self.config = scenario_config
        self.scenario = scenario_config.get("scenario", {})
        self.market = scenario_config.get("market", {})
        self.agent_templates = scenario_config.get("agents", [])
        self.decision_vars = scenario_config.get("decision_variables", [])
        self.objectives = scenario_config.get("objectives", [])
        self.constraints = scenario_config.get("constraints", [])
        self.info_asymmetry = scenario_config.get("information_asymmetry", [])

        self.archetype_behaviors: dict[str, dict[str, Any]] = {
            "incumbent": {
                "risk_tolerance": "low",
                "innovation_orientation": "incremental",
                "market_focus": "defensive",
                "decision_speed": "deliberate",
                "typical_strategies": ["maintain market share", "leverage economies of scale", "respond to threats"]
            },
            "challenger": {
                "risk_tolerance": "medium-high",
                "innovation_orientation": "disruptive",
                "market_focus": "offensive",
                "decision_speed": "agile",
                "typical_strategies": ["undercut pricing", "niche targeting", "rapid expansion"]
            },
            "specialist": {
                "risk_tolerance": "medium",
                "innovation_orientation": "focused",
                "market_focus": "niche",
                "decision_speed": "adaptive",
                "typical_strategies": ["premium positioning", "differentiation", "selective competition"]
            },
            "disruptor": {
                "risk_tolerance": "high",
                "innovation_orientation": "radical",
                "market_focus": "market-creating",
                "decision_speed": "rapid",
                "typical_strategies": ["new business models", "technology leverage", "boundary expansion"]
            },
            "follower": {
                "risk_tolerance": "low-medium",
                "innovation_orientation": "adaptive",
                "market_focus": "reactive",
                "decision_speed": "measured",
                "typical_strategies": ["fast-follower", "cost optimization", "segment specialization"]
            }
        }

        self.utility_templates: dict[str, dict[str, Any]] = {
            "profit_maximization": {
                "primary": "profit = revenue - costs",
                "components": ["revenue", "operating_costs", "fixed_costs", "marginal_costs"],
                "factors": ["market_share", "price_point", "cost_efficiency", "capacity_utilization"]
            },
            "market_share": {
                "primary": "share = own_output / total_market_output",
                "components": ["own_output", "competitor_outputs", "market_growth"],
                "factors": ["pricing", "quality", "distribution", "brand"]
            },
            "welfare_maximization": {
                "primary": "welfare = consumer_surplus + producer_surplus",
                "components": ["consumer_surplus", "producer_surplus", "externalities"],
                "factors": ["price", "quality", "access", "innovation"]
            }
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_all_profiles(self) -> dict[str, Any]:
        """Generate complete profile set for all agents."""
        profiles = [self._generate_single_profile(t) for t in self.agent_templates]
        cross_analysis = self._analyze_interactions(profiles)

        return {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "scenario_name": self.scenario.get("name", "Unnamed Scenario"),
                "domain": self.scenario.get("domain", "Unspecified"),
                "agent_count": len(profiles),
                "market_structure": self.market.get("structure", "unspecified")
            },
            "agent_profiles": profiles,
            "decision_space": self._generate_decision_space(),
            "information_structure": self._generate_information_structure(profiles),
            "interaction_matrix": cross_analysis["interaction_matrix"],
            "strategic_groups": cross_analysis["strategic_groups"]
        }

    # ── Profile construction ──────────────────────────────────────────────────

    def _generate_single_profile(self, template: dict[str, Any]) -> dict[str, Any]:
        agent_id = template.get("id", "agent_unknown")
        archetype = template.get("archetype", "follower")
        behaviors = self.archetype_behaviors.get(archetype, self.archetype_behaviors["follower"])
        objectives = self._generate_objectives(archetype, template)

        profile = AgentProfile(
            id=agent_id,
            archetype=archetype,
            role_description=template.get("role_description", ""),
            market_position=template.get("market_position", "undefined"),
            resource_constraints=template.get("resource_constraints", []),
            competitive_advantages=template.get("competitive_advantages", []),
            behavioral_traits=template.get("behavioral_traits", behaviors.get("typical_strategies", [])),
            decision_variables=self._assign_decision_variables(agent_id, archetype),
            objectives=objectives,
            utility_function=self._build_utility_function(agent_id, archetype, objectives),
            information_access=self._determine_information_access(agent_id),
            risk_profile=self._generate_risk_profile(archetype),
            rationality_bounds=self._generate_rationality_bounds(archetype)
        )
        return asdict(profile)

    def _assign_decision_variables(self, agent_id: str, archetype: str) -> list[dict[str, Any]]:
        return [
            {
                "name": var.get("name"),
                "type": var.get("type"),
                "range": var.get("range"),
                "description": var.get("description"),
                "agent_specific": True,
                "importance_weight": self._calculate_variable_importance(var.get("name", ""), archetype)
            }
            for var in self.decision_vars
        ]

    def _calculate_variable_importance(self, var_name: str, archetype: str) -> float:
        importance_matrix: dict[str, dict[str, float]] = {
            "price":      {"incumbent": 0.6, "challenger": 0.9, "specialist": 0.4, "disruptor": 0.7, "follower": 0.5},
            "capacity":   {"incumbent": 0.8, "challenger": 0.7, "specialist": 0.5, "disruptor": 0.6, "follower": 0.6},
            "quality":    {"incumbent": 0.5, "challenger": 0.4, "specialist": 0.9, "disruptor": 0.5, "follower": 0.5},
            "marketing":  {"incumbent": 0.6, "challenger": 0.8, "specialist": 0.7, "disruptor": 0.9, "follower": 0.4},
            "innovation": {"incumbent": 0.4, "challenger": 0.7, "specialist": 0.6, "disruptor": 0.95, "follower": 0.3}
        }
        var_lower = var_name.lower()
        for key, weights in importance_matrix.items():
            if key in var_lower:
                return weights.get(archetype, 0.5)
        return 0.5

    def _generate_objectives(self, archetype: str, template: dict) -> list[dict[str, Any]]:
        objectives = []
        for obj in self.objectives:
            weight = obj.get("weight", 0.5)
            modifier = self._get_objective_modifier(obj.get("name", ""), archetype)
            adjusted = round(min(1.0, weight * modifier), 2)
            objectives.append({
                "name": obj.get("name"),
                "optimization": obj.get("optimization", "maximize"),
                "weight": adjusted,
                "description": obj.get("description", ""),
                "priority": "primary" if adjusted > 0.7 else "secondary" if adjusted > 0.4 else "tertiary"
            })
        objectives.sort(key=lambda x: x["weight"], reverse=True)
        return objectives

    def _get_objective_modifier(self, obj_name: str, archetype: str) -> float:
        modifiers: dict[str, dict[str, float]] = {
            "profit":       {"incumbent": 1.0, "challenger": 0.8, "specialist": 0.9, "disruptor": 0.7, "follower": 0.9},
            "market_share": {"incumbent": 0.9, "challenger": 1.2, "specialist": 0.6, "disruptor": 1.1, "follower": 0.7},
            "growth":       {"incumbent": 0.7, "challenger": 1.2, "specialist": 0.8, "disruptor": 1.3, "follower": 0.6},
            "quality":      {"incumbent": 0.8, "challenger": 0.6, "specialist": 1.3, "disruptor": 0.7, "follower": 0.7}
        }
        obj_lower = obj_name.lower()
        for key, mods in modifiers.items():
            if key in obj_lower:
                return mods.get(archetype, 1.0)
        return 1.0

    def _build_utility_function(self, agent_id: str, archetype: str, objectives: list[dict]) -> dict[str, Any]:
        primary_obj = objectives[0]["name"] if objectives else "profit"
        utility_type = "profit_maximization"
        if "market_share" in primary_obj.lower():
            utility_type = "market_share"
        elif "welfare" in primary_obj.lower():
            utility_type = "welfare_maximization"

        tmpl = self.utility_templates.get(utility_type, self.utility_templates["profit_maximization"])
        return {
            "type": utility_type,
            "formula": f"U_{agent_id} = sum(w_i * V_i)",
            "primary_formula": tmpl["primary"],
            "components": tmpl["components"],
            "weighted_components": [
                {"component": o["name"], "weight": o["weight"], "optimization": o["optimization"]}
                for o in objectives[:3]
            ],
            "constraints": [c.get("description") for c in self.constraints if c.get("type") == "hard"]
        }

    def _determine_information_access(self, agent_id: str) -> dict[str, list[str]]:
        default_public  = ["market_structure", "historical_prices", "aggregate_demand", "regulatory_framework"]
        default_private = ["own_costs", "own_capacity", "own_strategy", "private_forecasts"]
        for asym in self.info_asymmetry:
            if asym.get("agent_id") == agent_id:
                return {
                    "private": asym.get("private_information", default_private),
                    "public":  asym.get("public_information", default_public)
                }
        return {"private": default_private, "public": default_public}

    def _generate_risk_profile(self, archetype: str) -> dict[str, Any]:
        behaviors = self.archetype_behaviors.get(archetype, {})
        return {
            "risk_tolerance":    behaviors.get("risk_tolerance", "medium"),
            "risk_preference":   "risk_averse" if archetype == "incumbent" else "risk_seeking" if archetype == "disruptor" else "risk_neutral",
            "downside_sensitivity": 0.7 if archetype == "incumbent" else 0.4 if archetype == "disruptor" else 0.5,
            "upside_sensitivity":   0.5 if archetype == "incumbent" else 0.8 if archetype == "disruptor" else 0.6
        }

    def _generate_rationality_bounds(self, archetype: str) -> dict[str, Any]:
        bounds: dict[str, dict[str, Any]] = {
            "incumbent":  {"computational_depth": "high",        "information_processing": "systematic", "biases": ["status_quo", "sunk_cost"]},
            "challenger": {"computational_depth": "medium",      "information_processing": "heuristic",  "biases": ["overconfidence", "availability"]},
            "specialist": {"computational_depth": "medium-high", "information_processing": "focused",    "biases": ["confirmation", "anchoring"]},
            "disruptor":  {"computational_depth": "variable",    "information_processing": "rapid",      "biases": ["optimism", "representativeness"]},
            "follower":   {"computational_depth": "medium",      "information_processing": "reactive",   "biases": ["bandwagon", "herding"]}
        }
        return bounds.get(archetype, bounds["follower"])

    # ── Decision space ────────────────────────────────────────────────────────

    def _generate_decision_space(self) -> dict[str, Any]:
        buckets: dict[str, list] = {"continuous": [], "discrete": [], "binary": [], "categorical": []}
        for var in self.decision_vars:
            entry = {"name": var.get("name"), "range": var.get("range"), "description": var.get("description")}
            buckets.get(var.get("type", "continuous"), buckets["continuous"]).append(entry)
        return {
            "continuous_variables":  buckets["continuous"],
            "discrete_variables":    buckets["discrete"],
            "binary_variables":      buckets["binary"],
            "categorical_variables": buckets["categorical"],
            "total_dimensions":      len(self.decision_vars),
            "joint_space_size":      "infinite" if buckets["continuous"] else "finite"
        }

    # ── Information structure ─────────────────────────────────────────────────

    def _generate_information_structure(self, profiles: list[dict]) -> dict[str, Any]:
        agents = [p["id"] for p in profiles]
        matrix = {
            a: {"knows_own": True, "knows_public": True, "knows_private_of_others": False, "can_infer_about": []}
            for a in agents
        }
        for asym in self.info_asymmetry:
            aid = asym.get("agent_id")
            if aid in matrix:
                matrix[aid]["custom_private"] = asym.get("private_information", [])
        return {
            "agents": agents,
            "knowledge_matrix": matrix,
            "information_partition": {
                "common_knowledge": ["market_structure", "rules_of_game", "payoff_functions"],
                "private_knowledge": ["own_costs", "own_type", "own_strategy"]
            }
        }

    # ── Interaction analysis ──────────────────────────────────────────────────

    def _analyze_interactions(self, profiles: list[dict]) -> dict[str, Any]:
        agents = [p["id"] for p in profiles]
        matrix: dict[str, dict] = {}
        for i, ai in enumerate(agents):
            matrix[ai] = {}
            for j, aj in enumerate(agents):
                if i == j:
                    matrix[ai][aj] = {"type": "self", "intensity": 0}
                else:
                    intensity = self._calculate_interaction_intensity(
                        profiles[i].get("archetype", "follower"),
                        profiles[j].get("archetype", "follower")
                    )
                    matrix[ai][aj] = {
                        "type": "competitive",
                        "intensity": intensity,
                        "description": "Direct competition in shared market space"
                    }
        return {
            "interaction_matrix": matrix,
            "strategic_groups": self._identify_strategic_groups(profiles)
        }

    def _calculate_interaction_intensity(self, arch_i: str, arch_j: str) -> float:
        intensity_matrix: dict[str, dict[str, float]] = {
            "incumbent":  {"incumbent": 0.9, "challenger": 0.8, "specialist": 0.3, "disruptor": 0.7, "follower": 0.4},
            "challenger": {"incumbent": 0.8, "challenger": 0.7, "specialist": 0.5, "disruptor": 0.6, "follower": 0.4},
            "specialist": {"incumbent": 0.3, "challenger": 0.5, "specialist": 0.4, "disruptor": 0.3, "follower": 0.2},
            "disruptor":  {"incumbent": 0.7, "challenger": 0.6, "specialist": 0.3, "disruptor": 0.5, "follower": 0.5},
            "follower":   {"incumbent": 0.4, "challenger": 0.4, "specialist": 0.2, "disruptor": 0.5, "follower": 0.3}
        }
        return intensity_matrix.get(arch_i, {}).get(arch_j, 0.5)

    def _identify_strategic_groups(self, profiles: list[dict]) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for p in profiles:
            arch = p.get("archetype", "follower")
            groups.setdefault(arch, []).append(p["id"])
        return groups


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate agent profiles from a scenario config JSON")
    parser.add_argument("--scenario", required=True, help="Path to scenario_config.json")
    parser.add_argument("--output",   required=True, help="Directory to write agent_profiles.json")
    args = parser.parse_args()

    config = json.loads(Path(args.scenario).read_text())
    gen = AgentProfileGenerator(config)
    result = gen.generate_all_profiles()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "agent_profiles.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Wrote {len(result['agent_profiles'])} profiles → {out_path}")


if __name__ == "__main__":
    main()
