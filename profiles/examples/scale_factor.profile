#
# Test profile extracting the power scale factor at multiple frequencies and gains
#

# Test parameters
test_type = 'scale_factor'
test_power_measurement_method = 'normalized_fft_maximum_power'
#test_find_divisions = False
#test_division_slope_averaging_factor = 3
#test_division_slope_ratio_threshold = 0.25
#test_division_resolution = 0.01
#test_division_narrowing_num = 20
#test_division_narrowing_buffer = 0.25
#test_division_narrowing_slope_ratio_threshold = 1
#test_division_observe = True
#test_known_divisions = []

# Sweep parameters
sweep_f_min = 100e6
sweep_f_max = 6000e6
sweep_f_num_steps = False
sweep_f_lin_spacing = 50e6
sweep_f_log_steps = False
sweep_f_extra = [70e6]
sweep_f_order = 'asc'
sweep_g_min = 0
sweep_g_max = 76
sweep_g_num_steps = False
sweep_g_lin_spacing = False
sweep_g_log_steps = False
sweep_g_extra = [0,20,40,60]
sweep_g_order = 'asc'

# Frequency Parameters
freq_use_offset = True
#freq_offset_f0_and_cw = 'DEFAULT'
#freq_offset_using_sdr = False

# Power Parameters
#power_level_mode = 'normal'
#power_base_power = 0
#power_verification = None
power_level = -20 # [USER_SET]
#power_inline_attenuator = 0
#power_limit_output_power = True
#power_scale_cw_power_with_sdr_gain = False

# FFT parameters
fft_number_of_bins = 1024
#fft_minimum_frequency_resolution = 1e3
#fft_averaging_number = 100
#fft_window = 'flattop'

# Logging parameters
#logging_quiet_mode = False
#logging_save_log_file = False
#logging_save_scale_factors = False
#logging_plot_scale_factors = True