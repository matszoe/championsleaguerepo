import numpy as np

import config
from nodal_flexibility_approximation import (
    compute_hp_baseline,
    map_load_time_series,
)


def _polygon_halfspaces(
    apparent_power_limit: float,
    n_sides: int | None = None,
    polygon_type: str | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Builds H, h for a polygonal approximation of P^2 + Q^2 <= S^2.

    outer: tangent polygon, contains the circle.
    inner: inscribed polygon, contained in the circle.
    """
    apparent_power_limit = max(float(apparent_power_limit), 0.0)
    n_sides = int(n_sides or getattr(config, "benchmark_polygon_sides", 16))
    polygon_type = polygon_type or getattr(config, "benchmark_polygon_type", "outer")

    if n_sides < 4:
        raise ValueError("benchmark polygon needs at least 4 sides")

    angles = np.linspace(0.0, 2.0 * np.pi, n_sides, endpoint=False)
    H = np.column_stack((np.cos(angles), np.sin(angles)))

    if polygon_type == "outer":
        radius = apparent_power_limit
    elif polygon_type == "inner":
        radius = apparent_power_limit * np.cos(np.pi / n_sides)
    else:
        raise ValueError(
            "benchmark_polygon_type must be either 'outer' or 'inner'"
        )

    h = np.full(n_sides, radius, dtype=float)
    h[np.abs(h) < 1e-12] = 0.0
    return H, h


def compute_nodal_approx_benchmark_polygon(
    P_pv_max: float,
    P_hp_flex_min: float,
    P_hp_flex_max: float,
    P_chg_max: float = 0.0,
    P_dis_max: float = 0.0,
    S_bat_max: float = 0.0,
    n_sides: int | None = None,
    polygon_type: str | None = None,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Simple benchmark nodal aggregation.

    The refined model aggregates device-level flexibility through a Minkowski
    outer approximation. This benchmark instead collapses all available nodal
    capability into:
      - one active-power interval
      - one polygonal apparent-power envelope

    Returns H, h, d_soc in the same format as the refined implementation.
    """
    P_pv_max = max(float(P_pv_max), 0.0)
    P_hp_flex_min = float(P_hp_flex_min)
    P_hp_flex_max = float(P_hp_flex_max)
    P_chg_max = max(float(P_chg_max), 0.0)
    P_dis_max = max(float(P_dis_max), 0.0)
    S_bat_max = max(float(S_bat_max), 0.0)

    if P_hp_flex_min > P_hp_flex_max:
        raise ValueError(
            "Invalid HP bounds: "
            f"P_hp_flex_min={P_hp_flex_min}, "
            f"P_hp_flex_max={P_hp_flex_max}"
        )

    P_min = P_hp_flex_min - P_chg_max
    P_max = P_pv_max + P_hp_flex_max + P_dis_max

    # Benchmark apparent-power aggregation: add the nodal capabilities into
    # one equivalent S limit, then approximate that circle by a polygon.
    S_pv = P_pv_max / max(float(config.pv_cf_lower_limit), 1e-9)
    S_hp = max(abs(P_hp_flex_min), abs(P_hp_flex_max))
    S_node = S_pv + S_hp + S_bat_max

    H_poly, h_poly = _polygon_halfspaces(
        apparent_power_limit=S_node,
        n_sides=n_sides,
        polygon_type=polygon_type,
    )

    H_p = np.array([
        [1.0, 0.0],
        [-1.0, 0.0],
    ])
    h_p = np.array([P_max, -P_min])

    H = np.vstack([H_p, H_poly])
    h = np.concatenate([h_p, h_poly])
    h[np.abs(h) < 1e-12] = 0.0

    # Kept positive for battery buses so the shared OPF can add SOC dynamics.
    d_soc = S_bat_max if S_bat_max > 1e-9 else 0.0
    return H, h, float(d_soc)
