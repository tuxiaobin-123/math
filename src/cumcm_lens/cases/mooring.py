"""2016 CUMCM A: static catenary model with numerical and constraint audits."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.optimize import least_squares

from cumcm_lens.core.audit import numeric_constraint

G = 9.80665
STEEL_DENSITY = 7850.0
CHAIN_TYPES = {
    "I": {"link_length_mm": 78.0, "mass_kgm": 3.2},
    "II": {"link_length_mm": 105.0, "mass_kgm": 7.0},
    "III": {"link_length_mm": 120.0, "mass_kgm": 12.5},
    "IV": {"link_length_mm": 150.0, "mass_kgm": 19.5},
    "V": {"link_length_mm": 180.0, "mass_kgm": 28.12},
}


@dataclass(frozen=True)
class MooringConfig:
    depth_m: float = 18.0
    wind_ms: float = 12.0
    current_ms: float = 0.0
    seawater_density_kgm3: float = 1025.0
    chain_type: str = "II"
    chain_length_m: float = 22.05
    ballast_mass_kg: float = 1200.0
    wind_coefficient: float = 0.625
    current_coefficient: float = 374.0


def effective_mass(mass_kg: float, seawater_density: float) -> float:
    return mass_kg * (1 - seawater_density / STEEL_DENSITY)


def horizontal_load(config: MooringConfig, draft_m: float) -> float:
    exposed_buoy_area = 2.0 * np.clip(2.0 - draft_m, 0.0, 2.0)
    submerged_buoy_area = 2.0 * np.clip(draft_m, 0.0, 2.0)
    underwater_component_area = 4 * 1.0 * 0.05 + 1.0 * 0.30
    wind = config.wind_coefficient * exposed_buoy_area * config.wind_ms**2
    current = (
        config.current_coefficient
        * (submerged_buoy_area + underwater_component_area)
        * config.current_ms**2
    )
    return float(wind + current)


def catenary_xy(
    horizontal_tension_n: float,
    anchor_vertical_n: float,
    weight_per_length_nm: float,
    suspended_length_m: float,
) -> tuple[float, float]:
    h = max(horizontal_tension_n, 1e-6)
    v0 = max(anchor_vertical_n, 0.0)
    w = weight_per_length_nm
    length = suspended_length_m
    x = h / w * (np.arcsinh((v0 + w * length) / h) - np.arcsinh(v0 / h))
    y = (
        np.hypot(h, v0 + w * length) - np.hypot(h, v0)
    ) / w
    return float(x), float(y)


def element_geometry(
    horizontal_tension_n: float,
    chain_top_vertical_n: float,
    config: MooringConfig,
) -> tuple[float, float, list[float]]:
    rho = config.seawater_density_kgm3
    ballast_weight = effective_mass(config.ballast_mass_kg, rho) * G
    barrel_weight = effective_mass(100.0, rho) * G
    pipe_weight = effective_mass(10.0, rho) * G
    vertical = chain_top_vertical_n + ballast_weight
    angles = []
    vertical_height = 0.0
    horizontal_span = 0.0
    # Bottom barrel first, followed by four identical steel pipes.
    for weight in [barrel_weight, *([pipe_weight] * 4)]:
        angle = float(np.arctan2(horizontal_tension_n, vertical + weight / 2))
        angles.append(np.degrees(angle))
        vertical_height += np.cos(angle)
        horizontal_span += np.sin(angle)
        vertical += weight
    return float(vertical_height), float(horizontal_span), angles


def buoy_draft(
    config: MooringConfig, suspended_length_m: float, anchor_vertical_n: float
) -> float:
    rho = config.seawater_density_kgm3
    chain_mass = CHAIN_TYPES[config.chain_type]["mass_kgm"]
    supported_equivalent_mass = (
        1000.0
        + effective_mass(config.ballast_mass_kg + 100.0 + 4 * 10.0, rho)
        + effective_mass(chain_mass * suspended_length_m, rho)
        + anchor_vertical_n / G
    )
    waterplane_area = np.pi * 1.0**2
    return float(supported_equivalent_mass / (rho * waterplane_area))


def _residuals(
    variables: np.ndarray, config: MooringConfig, grounded: bool
) -> np.ndarray:
    horizontal, draft, third = variables
    chain_mass = CHAIN_TYPES[config.chain_type]["mass_kgm"]
    w = effective_mass(chain_mass, config.seawater_density_kgm3) * G
    if grounded:
        suspended_length = third
        anchor_vertical = 0.0
    else:
        suspended_length = config.chain_length_m
        anchor_vertical = third
    _, chain_height = catenary_xy(horizontal, anchor_vertical, w, suspended_length)
    element_height, _, _ = element_geometry(
        horizontal, anchor_vertical + w * suspended_length, config
    )
    required_height = config.depth_m - draft
    return np.array(
        [
            (horizontal - horizontal_load(config, draft)) / 1000,
            draft - buoy_draft(config, suspended_length, anchor_vertical),
            chain_height + element_height - required_height,
        ]
    )


def solve_state(config: MooringConfig) -> dict[str, Any]:
    if config.chain_type not in CHAIN_TYPES:
        raise ValueError(f"Unknown chain type {config.chain_type}")
    grounded_solution = least_squares(
        _residuals,
        x0=np.array([max(500.0, horizontal_load(config, 0.7)), 0.7, 0.6 * config.chain_length_m]),
        bounds=([1.0, 0.05, 0.01], [2e6, 1.999, config.chain_length_m]),
        args=(config, True),
        xtol=1e-11,
        ftol=1e-11,
        gtol=1e-11,
        max_nfev=3000,
    )
    horizontal, draft, suspended = grounded_solution.x
    grounded_valid = bool(
        grounded_solution.cost < 1e-9 and suspended < config.chain_length_m - 1e-5
    )
    if grounded_valid:
        regime = "seabed_contact"
        anchor_vertical = 0.0
        residual = grounded_solution.fun
    else:
        full_solution = least_squares(
            _residuals,
            x0=np.array([max(1000.0, horizontal_load(config, 0.8)), 0.8, 500.0]),
            bounds=([1.0, 0.05, 0.0], [2e6, 1.999, 2e6]),
            args=(config, False),
            xtol=1e-11,
            ftol=1e-11,
            gtol=1e-11,
            max_nfev=5000,
        )
        horizontal, draft, anchor_vertical = full_solution.x
        suspended = config.chain_length_m
        residual = full_solution.fun
        regime = "fully_suspended"
    chain_mass = CHAIN_TYPES[config.chain_type]["mass_kgm"]
    w = effective_mass(chain_mass, config.seawater_density_kgm3) * G
    chain_x, chain_y = catenary_xy(horizontal, anchor_vertical, w, suspended)
    element_y, element_x, angles = element_geometry(
        horizontal, anchor_vertical + w * suspended, config
    )
    anchor_angle = float(np.degrees(np.arctan2(anchor_vertical, horizontal)))
    result = {
        **asdict(config),
        "regime": regime,
        "horizontal_tension_n": float(horizontal),
        "anchor_vertical_tension_n": float(anchor_vertical),
        "suspended_chain_m": float(suspended),
        "chain_on_seabed_m": float(config.chain_length_m - suspended),
        "chain_horizontal_span_m": chain_x,
        "chain_vertical_rise_m": chain_y,
        "component_horizontal_span_m": element_x,
        "excursion_radius_m": chain_x + element_x,
        "draft_m": float(draft),
        "anchor_angle_deg": anchor_angle,
        "barrel_angle_deg": angles[0],
        "pipe_angles_deg_bottom_to_top": angles[1:],
        "equation_residual_max": float(np.max(np.abs(residual))),
    }
    result["audits"] = audit_state(result)
    return result


def audit_state(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        numeric_constraint("barrel_tilt_deg", state["barrel_angle_deg"], upper=5.0).to_dict(),
        numeric_constraint("anchor_angle_deg", state["anchor_angle_deg"], upper=16.0).to_dict(),
        numeric_constraint("draft_m", state["draft_m"], lower=0.0, upper=2.0).to_dict(),
        numeric_constraint(
            "equation_residual_max",
            state["equation_residual_max"],
            upper=1e-6,
        ).to_dict(),
    ]


def numerical_catenary_audit(state: dict[str, Any]) -> dict[str, Any]:
    config = MooringConfig(
        **{key: state[key] for key in MooringConfig.__dataclass_fields__}
    )
    chain_mass = CHAIN_TYPES[config.chain_type]["mass_kgm"]
    w = effective_mass(chain_mass, config.seawater_density_kgm3) * G
    h = state["horizontal_tension_n"]
    v0 = state["anchor_vertical_tension_n"]
    length = state["suspended_chain_m"]
    x_num = quad(lambda s: h / np.hypot(h, v0 + w * s), 0, length, epsabs=1e-10)[0]
    y_num = quad(
        lambda s: (v0 + w * s) / np.hypot(h, v0 + w * s),
        0,
        length,
        epsabs=1e-10,
    )[0]
    return {
        "analytic_x_m": state["chain_horizontal_span_m"],
        "numeric_x_m": x_num,
        "absolute_x_error_m": abs(state["chain_horizontal_span_m"] - x_num),
        "analytic_y_m": state["chain_vertical_rise_m"],
        "numeric_y_m": y_num,
        "absolute_y_error_m": abs(state["chain_vertical_rise_m"] - y_num),
    }


def design_grid() -> pd.DataFrame:
    records = []
    for chain_type in CHAIN_TYPES:
        for length in np.arange(20.0, 36.1, 2.0):
            for ballast in np.arange(1000.0, 5501.0, 250.0):
                scenario_states = []
                feasible = True
                for depth in (16.0, 18.0, 20.0):
                    state = solve_state(
                        MooringConfig(
                            depth_m=depth,
                            wind_ms=36.0,
                            current_ms=1.5,
                            chain_type=chain_type,
                            chain_length_m=float(length),
                            ballast_mass_kg=float(ballast),
                        )
                    )
                    scenario_states.append(state)
                    feasible &= all(item["passed"] for item in state["audits"])
                max_tilt = max(state["barrel_angle_deg"] for state in scenario_states)
                max_anchor = max(state["anchor_angle_deg"] for state in scenario_states)
                max_excursion = max(state["excursion_radius_m"] for state in scenario_states)
                max_draft = max(state["draft_m"] for state in scenario_states)
                objective = (
                    max_excursion
                    + 2 * max_tilt
                    + 0.002 * ballast
                    + 0.1 * CHAIN_TYPES[chain_type]["mass_kgm"] * length
                )
                records.append(
                    {
                        "chain_type": chain_type,
                        "chain_length_m": length,
                        "ballast_mass_kg": ballast,
                        "feasible": feasible,
                        "max_barrel_tilt_deg": max_tilt,
                        "max_anchor_angle_deg": max_anchor,
                        "max_excursion_m": max_excursion,
                        "max_draft_m": max_draft,
                        "objective": objective,
                    }
                )
    return pd.DataFrame(records).sort_values(["feasible", "objective"], ascending=[False, True])


def sensitivity_table(base: MooringConfig) -> pd.DataFrame:
    records = []
    for parameter, factors in {
        "wind_ms": [0.8, 0.9, 1.0, 1.1, 1.2],
        "current_ms": [0.8, 0.9, 1.0, 1.1, 1.2],
        "ballast_mass_kg": [0.8, 0.9, 1.0, 1.1, 1.2],
        "seawater_density_kgm3": [0.98, 0.99, 1.0, 1.01, 1.02],
    }.items():
        for factor in factors:
            values = asdict(base)
            values[parameter] = values[parameter] * factor
            state = solve_state(MooringConfig(**values))
            records.append(
                {
                    "parameter": parameter,
                    "factor": factor,
                    "barrel_angle_deg": state["barrel_angle_deg"],
                    "anchor_angle_deg": state["anchor_angle_deg"],
                    "draft_m": state["draft_m"],
                    "excursion_radius_m": state["excursion_radius_m"],
                }
            )
    return pd.DataFrame(records)


def run_case(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    problem_states = []
    for wind in (12.0, 24.0, 36.0):
        state = solve_state(MooringConfig(wind_ms=wind))
        state["numerical_catenary_audit"] = numerical_catenary_audit(state)
        problem_states.append(state)
    grid = design_grid()
    grid.head(50).to_csv(output_dir / "design_candidates.csv", index=False)
    best_row = grid[grid["feasible"]].iloc[0] if grid["feasible"].any() else grid.iloc[0]
    robust_config = MooringConfig(
        depth_m=20.0,
        wind_ms=36.0,
        current_ms=1.5,
        chain_type=str(best_row["chain_type"]),
        chain_length_m=float(best_row["chain_length_m"]),
        ballast_mass_kg=float(best_row["ballast_mass_kg"]),
    )
    robust_state = solve_state(robust_config)
    sensitivity = sensitivity_table(robust_config)
    sensitivity.to_csv(output_dir / "sensitivity.csv", index=False)
    pd.DataFrame(
        [
            {
                key: value
                for key, value in state.items()
                if not isinstance(value, (list, dict))
            }
            for state in problem_states
        ]
    ).to_csv(output_dir / "question_1_2_states.csv", index=False)
    summary = {
        "case": "2016A",
        "source": "official problem statement; no separate data attachment",
        "official_parameters": {
            "buoy": "diameter 2 m, height 2 m, mass 1000 kg",
            "pipes": "4 × (length 1 m, diameter 0.05 m, mass 10 kg)",
            "barrel": "length 1 m, diameter 0.30 m, total mass 100 kg",
            "anchor_mass_kg": 600,
            "chain_types": CHAIN_TYPES,
            "wind_force": "F = 0.625 S v^2 N",
            "current_force": "F = 374 S v^2 N",
        },
        "problem_states": problem_states,
        "robust_design": robust_state,
        "design_objective": (
            "minimize excursion + 2×max barrel tilt + ballast penalty + chain mass-length "
            "penalty over depth {16,18,20} m at wind 36 m/s and current 1.5 m/s"
        ),
        "assumptions": [
            "静力、同向稳态风流；未计波浪、涡激振动和锚链弯曲刚度。",
            "钢制构件按密度7850 kg/m³折算浮力；重物球按同一密度处理。",
            "锚链接地点采用可接触海床/全悬浮两种互斥状态求解。",
            "游动区域报告为水平偏移半径，其实际方向由环境载荷方向决定。",
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
