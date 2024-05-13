#
# Test profile extracting the power scale factor at multiple frequencies and gains
#

# Test parameters
test_type = 'rf_switch_cal'

# Sweep parameters
sweep_f_min = 70e6
sweep_f_max = 6000e6
sweep_f_num_steps = 350
sweep_f_lin_spacing = False
sweep_f_log_steps = False
sweep_f_extra = []
sweep_f_order = 'asc'

# Power Parameters
power_level = -10

# Logging parameters
#logging_quiet_mode = False
logging_save_switch_cal_file = True
logging_save_log_file = False
logging_plot_switch_cal_values = True

