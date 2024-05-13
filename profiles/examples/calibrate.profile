#
# Test profile to run through an autonomous calibration routine
# changing to have different types of calibrate
#

# TODO: explain how to configure hardware for this 

# Test parameters
test_type = 'calibrate'
test_measure_scale_factor = True
test_measure_enbws = True
test_measure_noise_figure = True
test_measure_compression = True
#test_measure_spur_free = False NOT IMPLEMENTED YET

test_sample_rates =      [1e6, 2e6] # [10e6, 15.36e6, 40e6]
test_clock_frequencies = [10e6, 10e6] #[40e6, 30.72e6, 40e6]

# Sweep parameters
sweep_f_min = 400e6
sweep_f_max = 600e6 #5000e6
sweep_f_num_steps = False
sweep_f_lin_spacing = 100e6
sweep_f_log_steps = False
sweep_f_extra = []
# these are part of frequencies it sweeps
sweep_f_divisions = [
    # [1299999999,1300000000],
    # [2199999998,2200000000],
    # [3999999995,4000000000]
]
sweep_g_min = 40
sweep_g_max = 49 #60
sweep_g_num_steps = 2
sweep_g_lin_spacing = False
sweep_g_log_steps = False
sweep_g_extra = []

# Scale factor specific parameters
scale_factor_power_level = -20
scale_factor_measurement_method = 'normalized_fft_maximum_power'

# Equivalent noise bandwidth specific parameters
enbw_frequency = 700e6
enbw_gain = 40
enbw_power_level = -20
enbw_measurement_band_stretch = 1.5
enbw_transfer_function_points = 10 #250

# Noise figure specific parameters
noise_figure_enbws = [10e6, 15e6, 40e6]
noise_figure_terminating = False
noise_figure_input_power = -200

# Compression specific parameters
compression_skip_sample_rate_cycling = True
compression_decimate_frequencies = 10
compression_min_power = -25
compression_max_power = 40
compression_power_step = 1
compression_measurement_method = 'normalized_fft_maximum_power'
compression_threshold = 3
compression_linearity_steps = 5 #10
compression_linearity_threshold = 0.01

# Spurious free specific parameters NOT IMPLEMENTED
spur_free_measurement_remove_ranges = [
    [-25,25]
]
spur_free_danl_num = 10 #HAVE THIS EVENTUALLY LOAD A DANL FILE
spur_free_threshold = 5

# Frequency Parameters
freq_use_offset = True
freq_offset_f0_and_cw = 'DEFAULT'
#freq_offset_using_sdr = False

# Power Parameters
#power_inline_attenuator = 0
power_limit_output_power = False
power_scale_cw_power_with_sdr_gain = True
power_level_mode = 'Normal'
power_verification = None #'power_meter'

# FFT parameters
fft_averaging_number = 10 #100
fft_window = 'flattop'
fft_number_of_bins = 1024
#fft_minimum_frequency_resolution = 1e3

# Logging parameters
#logging_quiet_mode = False
# logging_save_test_summary = True
# logging_save_log_file = False