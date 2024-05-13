#
# Test profile for measuring 3dB and equivalent noise bandwidth
#

# Test parameters
test_type = 'bandwidth'
test_bandwidth_to_measure = 24e6
test_bandwidth_steps = 200

# Frequency Parameters
freq_f0 = 100e6

# Power Parameters
#power_level_mode = 'normal'
#power_base_power = 0
power_level = -20 # [USER SET] # TODO: Change back to blank for release
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
#logging_save_transfer_function = False
#logging_plot_transfer_function = True
