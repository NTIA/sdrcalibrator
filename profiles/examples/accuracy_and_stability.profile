#
# Test profile for accuracy and stability measurements

# Notes for running this profile: 
#   - see which parameters need to be set in here, which can be with SDR default
#       - ideally add a way to pull from SDR defaults for fields where this might be appropriate
#   - make sure gain/max power and frequency params don't push sweep outside SDR operating ranges 
#       - there's no bounds checking, but maybe we can do a check so it doesn't discard everything
#

# Test parameters
test_type = 'accuracy_and_stability'
test_power_measurement_method = 'normalized_fft_maximum_power'
test_delay_between_sweeps = 30
test_cycle_use_time = True
test_cycle_sweeping_time = 2*60
test_cycle_number_of_sweeps = 1

# Sweep parameters
sweep_f_min = 100e6
sweep_f_max = 1.7e9 # 6000e6 # can this default to SDR max?
sweep_f_num_steps = 2
sweep_f_lin_spacing = False
sweep_f_log_steps = False
sweep_f_extra = []
sweep_f_order = 'asc'
sweep_p_min = -40
sweep_p_max = -15.1
sweep_p_num_steps = False
sweep_p_lin_spacing = 10
sweep_p_log_steps = False
sweep_p_extra = []
sweep_p_order = 'desc'
sweep_g_min = 0
sweep_g_max = 76
sweep_g_num_steps = False
sweep_g_lin_spacing = False
sweep_g_log_steps = False
sweep_g_extra = [0] # has to be an array 
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
# TODO: Document what all the logging parameters do
# logging_quiet_mode = True
#logging_save_log_file = False
#logging_save_test_results = False
# logging_save_log_file = True
#logging_distribute_data_files = True

