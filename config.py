import pandas as pd

<<<<<<< HEAD
scenario = "with_battery" # "base", "with_battery"
=======
scenario = "with_battery"
>>>>>>> josua
pv_cf_lower_limit = 0.9
SOC_inital = 0.5
soc_min = 0.2
soc_max = 0.8
battery_capacity_at_FC = 1
T_room_initial = 20

single_timestep = pd.Timestamp("2018-04-01 12:00:00")

# New: a single anchor + a list of durations to sweep
start_time = pd.Timestamp("2018-04-01 12:00:00")
sustained_durations_h = [1, 2, 4, 8]   # paper Fig. 6 uses 15min, 30min, 1h, 2h, 4h, 8h
timestep_freq = "h"

alpha = 1.0
beta = 0
n_ffor_directions = 32

benchmark_polygon_sides = 16
benchmark_polygon_type = "outer"  # "outer" polygon or "inner" polygon
