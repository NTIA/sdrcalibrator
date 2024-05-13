#
# Test profile for single LO FFT
#

# Test parameters
test_type = 'single_fft'

# Frequency Parameters
freq_f0 = 2.3998e9 # ofthen is set to 100 MHz 
#freq_use_offset = False
#freq_offset_lo_and_cw = 'DEFAULT'
#freq_offset_using_sdr = False

# Power Parameters
#power_stimulus = None
#power_level_mode = 'normal'
#power_base_power = 0
#power_verification = None
#power_level = [USER_SET]
#power_inline_attenuator = 0
#power_limit_output_power = True
#power_scale_cw_power_with_sdr_gain = False

# FFT parameters 
fft_number_of_bins = 8192 #4086 #8192
#fft_minimum_frequency_resolution = 1e3
#fft_averaging_number = 100
# fft_window = 'flattop'

# Logging parameters
#logging_quiet_mode = False
#logging_save_log_file = False
logging_save_fft_data = True
logging_save_iq_data = True
logging_plot_fft = True
logging_note = "noise"

# sdr_conditioning_samples = 100000

# Notes:
# No input signal, just doing measurements for noise variance and fft window size