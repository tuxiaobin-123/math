from cumcm_lens.cases.mooring import (
    MooringConfig,
    numerical_catenary_audit,
    solve_state,
)


def test_catenary_closed_form_matches_numerical_integral() -> None:
    state = solve_state(MooringConfig(wind_ms=24))
    audit = numerical_catenary_audit(state)
    assert audit["absolute_x_error_m"] < 1e-8
    assert audit["absolute_y_error_m"] < 1e-8


def test_solved_state_closes_equations() -> None:
    state = solve_state(MooringConfig(wind_ms=12))
    assert state["equation_residual_max"] < 1e-8
    assert 0 < state["draft_m"] < 2
    assert state["suspended_chain_m"] <= state["chain_length_m"]


def test_reported_robust_candidate_passes_extreme_state() -> None:
    state = solve_state(
        MooringConfig(
            depth_m=20,
            wind_ms=36,
            current_ms=1.5,
            chain_type="I",
            chain_length_m=36,
            ballast_mass_kg=5000,
        )
    )
    assert all(item["passed"] for item in state["audits"])
