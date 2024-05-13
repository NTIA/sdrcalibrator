#
# Test profile for a single frequency and single power measurement of power
#

# Test parameters
test_type = 'power_measurement'

# Frequency Parameters
# TODO: Document what these parameters do
freq_f0 = 1000e6
freq_use_offset = True
freq_offset_f0_and_cw = 0.5e6
#freq_offset_using_sdr = False

# Power Parameters
power_stimulus = 'single_cw'
power_level_mode = 'normal'
#power_base_power = 0
power_verification = None #'power_meter'
power_level = -50
#power_inline_attenuator = 0
power_limit_output_power = False
power_scale_cw_power_with_sdr_gain = False

# FFT parameters
fft_number_of_bins = 1024
#fft_minimum_frequency_resolution = 1e3
fft_averaging_number = 100
fft_window = 'flattop'

# Logging parameters
logging_quiet_mode = False
# logging_save_log_file = True
logging_save_test_summary = False
#logging_save_fft_data = True
#logging_save_iq_data = False
logging_plot_fft = True