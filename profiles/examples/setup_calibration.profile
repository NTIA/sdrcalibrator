#
# Calibration Utility for RF Test Setup
#     run on 2020-08-10_13_47_44
#

# switch parameters
#switch_connect_params = {'ip_addr': '10.25.70.23'}
# switch_swap_inputs = False
#switch_module = "x300"

# test parameters
test_type = "setup_calibration"

# sweep parameters
sweep_g_extra = []
sweep_f_lin_spacing = 100000000.0 # 100 MHz
sweep_p_lin_spacing = False
sweep_p_order = "asc"
sweep_p_log_steps = False
sweep_g_order = "asc"
sweep_g_lin_spacing = False
sweep_g_log_steps = False
sweep_f_log_steps = False
sweep_f_num_steps = False
sweep_p_num_steps = False
sweep_g_num_steps = False
sweep_f_order = "asc"
sweep_f_max = 700000000 # int(3.8e9) #110000000.0 # 6000000000.0 # should be no larger than sdr max
sweep_f_min = 400000000 # int(325e6) #100000000.0
sweep_f_extra = []
sweep_p_extra = []

# power parameters
power_scale_cw_power_with_sdr_gain = False
power_base_power = 0
power_level = -10
power_inline_attenuator = 0
power_limit_output_power = True

# pwrmtr parameters
#pwrmtr_connect_params = {'ip_addr': '10.25.70.24'}

# freq parameters
freq_offset_f0_and_cw = "DEFAULT"
freq_offset_using_sdr = False
freq_use_offset = False

# logging parameters
logging_save_setup_cal_file = True
logging_plot_setup_cal_values = True
logging_quiet_mode = False
logging_save_log_file = False

# sdr parameters

# siggen parameters
siggen_rf_on_settling_time = 2
siggen_rf_off_settling_time = 0.5

# fft parameters
fft_averaging_number = 1
fft_minimum_frequency_resolution = False
fft_window = None