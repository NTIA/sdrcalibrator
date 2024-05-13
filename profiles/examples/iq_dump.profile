#
# Test profile for an IQ data dump
#

# Test parameters
test_type = 'iq_dump'
test_number_of_samples = 1024

# Frequency Parameters
freq_f0 = 2.3995e9 #100e6
sdr_sampling_frequency = int(4e6) 
sdr_gain = 0 #30
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

# Logging parameters
#logging_quiet_mode = False
logging_save_log_file = True
logging_save_iq_data = True
logging_plot_histogram = True
#logging_plot_num_hist_bins = 30
logging_note = "" # notes for individial runs