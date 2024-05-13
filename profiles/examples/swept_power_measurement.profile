#
# Test profile for power measurements with swept parameters
#

# Test parameters
test_type = 'swept_power_measurement'
#test_check_for_compression = True
#test_compression_measurement_method = 'normalized_fft_maximum_power'
#test_compression_threshold = 3
#test_compression_linearity_steps = 10
#test_compression_linearity_threshold = 0.01
#test_measure_spur_power = True
#test_spur_measurement_remove_ranges = [
#    [-25,25]
#]
#test_spur_danl_num = 10
#test_spur_threshold = 5

# Sweep parameters
sweep_f_min = 100e6
sweep_f_max = 6000e6
sweep_f_num_steps = 10
sweep_f_lin_spacing = False
sweep_f_log_steps = False
sweep_f_extra = []
sweep_f_order = 'asc'
sweep_p_min = -40
sweep_p_max = 0
sweep_p_num_steps = False
sweep_p_lin_spacing = 1
sweep_p_log_steps = False
sweep_p_extra = []
sweep_p_order = 'desc'
sweep_g_min = 0
sweep_g_max = 76
sweep_g_num_steps = False
sweep_g_lin_spacing = False
sweep_g_log_steps = False
sweep_g_extra = [30]
sweep_g_order = 'asc'
sweep_order_1st = 'frequency'
sweep_order_2nd = 'gain'
sweep_order_3rd = 'power'

# Frequency Parameters
#freq_use_offset = False
#freq_offset_lo_and_cw = 'DEFAULT'
#freq_offset_using_sdr = False

# Power Parameters
#power_level_mode = 'normal'
#power_base_power = 0
#power_verification = None
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
#logging_save_test_summary = False
#logging_plot_power_summary = True