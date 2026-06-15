# Distribution Grid Flexibility Approximation

This repository computes flexibility feasible operating regions (FFORs) for a
medium-voltage distribution grid with photovoltaic generation, heat pumps, and
optional battery storage. The model estimates local flexible resource
capabilities from time-series data, aggregates them into nodal flexibility
regions, and solves a linearized AC optimal power flow (OPF) to determine the
active and reactive power flexibility that can be provided at the point of
common coupling (PCC).

The main workflow is implemented for multi-timestep sustained flexibility. For
each configured duration, the OPF enforces a constant PCC power deviation over
all time steps in the horizon and samples the FFOR boundary by solving the model
in multiple active/reactive power directions.

## What the Code Does

The repository combines four modelling layers:

1. **Network model**
   - Loads the CINELDI MV reference grid from CSV input files.
   - Builds a pandapower network and runs a base power flow.
   - Extracts the admittance matrix and constructs Jacobian matrices for a
     linearized AC power-flow approximation.
   - Applies voltage limits, line-flow equations, and thermal line limits.

2. **Flexible resource estimation**
   - Maps hourly load time series to grid buses.
   - Estimates PV and heat-pump capacities from correlations between load,
     PV capacity-factor data, and ambient temperature.
   - Adds battery capacity at fast-charging-station buses for the
     `with_battery` scenario.

3. **Nodal flexibility aggregation**
   - Builds per-bus, per-timestep flexibility bounds for PV, heat pumps, and
     batteries.
   - Computes a Minkowski outer approximation of the combined nodal
     active/reactive flexibility region.
   - Optionally includes battery apparent-power capability and state-of-charge
     coupling.
   - Provides a benchmark polygon approximation for comparison.

4. **FFOR optimization**
   - Solves a Pyomo OPF model using Gurobi.
   - Samples directions
     `alpha = -cos(theta)` and `beta = -sin(theta)`.
   - For each direction, optimizes the PCC flexibility point.
   - Saves FFOR vertices, PCC time series, and nodal flexibility dispatches.

## Main Files

| File | Purpose |
| --- | --- |
| `config.py` | Central configuration for scenario, timestamps, durations, solver directions, and model constants. |
| `run_multi_timestep.py` | Main script for sustained multi-timestep FFOR computation. |
| `run_single_timestep.py` | Single-timestep FFOR workflow. Useful for quick tests or one-hour studies. |
| `run_benchmark.py` | Runs the benchmark polygon aggregation model over the same sustained-duration workflow. |
| `optimal_power_flow.py` | Builds and solves the linearized AC OPF, including network constraints, flexibility constraints, HP thermal dynamics, and battery SOC dynamics. |
| `nodal_flexibility_approximation.py` | Computes HP baselines, maps load time series, and builds Minkowski outer approximations of nodal flexibility. |
| `nodal_flexibility_approximation_benchmark.py` | Computes the simpler benchmark polygon approximation. |
| `plot_and_estimate_correlations.py` | Estimates PV, HP, and battery capacities from input data and provides helper plotting functions. |
| `pandapower_read_csv.py` | Reads the CINELDI CSV files into a pandapower network. |

## Input Data

Input data are stored in `00-INPUT-DATA/`:

- `norway_data/`: CINELDI MV reference grid, load mapping, line data, bus data,
  and scenario data for future loads / fast-charging stations.
- `PV-DATA/PV_timeseries.csv`: hourly PV capacity-factor time series.
- `TEMP-DATA/TEMP_timeseries.csv`: hourly ambient temperature time series.
- `HP-DATA/hp_profile.csv`: heat-pump thermal response profile used in the
  multi-timestep room-temperature dynamics.

The annual input time series are used to construct selected optimization
horizons. The default sustained-duration study starts at
`2018-04-01 12:00:00` and solves horizons of 1, 2, 4, and 8 hours.

## Configuration

The most important settings are defined in `config.py`:

```python
scenario = "with_battery"      # "base" or "with_battery"
pv_cf_lower_limit = 0.9        # minimum PV power factor
SOC_inital = 0.5               # initial battery SOC
soc_min = 0.2
soc_max = 0.8
T_room_initial = 20
start_time = pd.Timestamp("2018-04-01 12:00:00")
sustained_durations_h = [1, 2, 4, 8]
timestep_freq = "h"
n_ffor_directions = 32
benchmark_polygon_sides = 16
benchmark_polygon_type = "outer"
```

Set `scenario = "base"` to run without battery flexibility. Set
`scenario = "with_battery"` to include fast-charging-station battery capacity,
battery apparent-power limits, and SOC dynamics.

## Installation

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

The optimization model is solved with Gurobi through Pyomo:

- Gurobi must be installed separately.
- A valid Gurobi license is required.
- The `gurobi` executable must be available to Pyomo.

## Running the Models

Run the main sustained multi-timestep model:

```bash
python run_multi_timestep.py
```

Run the benchmark polygon model:

```bash
python run_benchmark.py
```

Run the single-timestep model:

```bash
python run_single_timestep.py
```

The scripts read the settings from `config.py`, build the required input data,
construct the OPF, solve all configured FFOR directions, and write the results
to `01-RESULTS/`.

## Output Files

For each sustained duration, `run_multi_timestep.py` creates an output folder
with a name such as:

```text
01-RESULTS/multi_ts_with_battery_04-01_12-00_d4h/
```

The main output files are:

| File | Contents |
| --- | --- |
| `ffor_vertices.csv` | One optimized PCC flexibility point for each sampled direction. |
| `pcc_results_all_directions.csv` | PCC active/reactive power for all time steps and directions. |
| `flex_results_all_directions.csv` | Nodal active/reactive flexibility and device-level dispatch values. |
| `gurobi_logs/` | Solver logs for each sampled direction. |

The benchmark script writes analogous files in folders named
`multi_ts_benchmark_<scenario>_...`.

## Mathematical Model Summary

The OPF uses a linearized AC power-flow model around a base operating point:

- voltage-angle variables `theta`
- voltage-magnitude deviation variables `dV`
- active/reactive nodal injections `P_inj`, `Q_inj`
- PCC variables `P_pcc`, `Q_pcc`
- line-flow variables `P_line`, `Q_line`

Nodal flexibility is represented by aggregate variables `P_flex` and `Q_flex`.
When device-level data are available, these are decomposed into:

- `P_pv_flex`, `Q_pv_flex`
- `P_hp_flex`
- `P_bat_flex`, `Q_bat_flex`

PV flexibility is limited by available PV power and a minimum power factor.
Heat-pump flexibility is bounded by a temperature-dependent baseline and
includes a room-temperature evolution constraint in the multi-timestep model.
Battery flexibility is limited by charging/discharging bounds, apparent-power
capability, and SOC dynamics.

For the multi-timestep FFOR, the PCC deviation is constrained to be constant:

```text
P_pcc[t] - P_pcc_base[t] = P_flex_pcc
Q_pcc[t] - Q_pcc_base[t] = Q_flex_pcc
```

Each sampled direction solves:

```text
min sum_t alpha * (P_pcc[t] - P_pcc_base[t])
          + beta  * (Q_pcc[t] - Q_pcc_base[t])
```

The optimized points form the sampled boundary of the FFOR.

## Notes

- All OPF quantities are represented in per unit unless stated otherwise.
- The code uses hourly time steps by default.
- The benchmark model is not the main aggregation method; it is included for
  comparison against the refined Minkowski outer approximation.
- Some post-processing and plotting workflows are contained in notebooks and
  helper scripts.
