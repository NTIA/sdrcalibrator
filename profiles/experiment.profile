import sdrcalibrator.lib.utils.common as utils

############# SDR PARAMETERS #############

# from sdrcalibrator.lib.equipment.sdr import rtl_sdr as sdr_module
# sdr_module = 'rtl_sdr' # module name 
# sdr_module = 'mock_sdr'
# sdr_module = 'adalm2000'
sdr_module = 'adalm_pluto'

# sdr module import for setting defaults 
# sdr = utils.import_object("sdrcalibrator.lib.equipment.sdr.{}".format(sdr_module), "SDR")()
sdr_connect_params = {
    'ip_addr' : '' # none for RTL SDR
}

# sdr_clock_frequency = sdr.SDR_DEFAULT_CLOCK_FREQUENCY #40e6
sdr_sampling_frequency = 1e6 #sdr.SDR_DEFAULT_SAMPLING_FREQUENCY #5e6
#sdr_auto_dc_offset = True
#sdr_auto_iq_imbalance = True
sdr_gain = 0 # sdr.SDR_DEFAULT_GAIN #60
#sdr_f0_tuning_error_threshold = 1e6
#sdr_use_dsp_lo_shift = False
#sdr_dsp_lo_shift = -6e6
# sdr_conditioning_samples = sdr.SDR_DEFAULT_CONDITIONING_SAMPLES
#sdr_power_limit = -15
sdr_power_scale_factor = 0 #-49.8291927888
#sdr_power_scale_factor_file = './path/to/file/scale_factors.csv'


############# NETWORK SETTINGS #############
# Siggen parameters
# siggen_rf_on_settling_timesiggen_rf_on_settling_timeSiggen parameters
# siggen_module = 'n5182b' 
siggen_module = 'mock_siggen'
siggen_connect_params = {
    'ip_addr' : '192.168.82.121', 
    'port' : '5025'
}
siggen_rf_on_settling_time = 0.5
siggen_rf_off_settling_time = 0.5

# Power meter paramters 
# pwrmtr_module = 'n1912a' #pwrmtr_module = 'n9030b'
pwrmtr_module = 'mock_pwrmtr'
pwrmtr_connect_params = {
    'ip_addr' : '192.168.82.123',
    'perform_calibration_at_startup' : False,
    'perform_calibration_during_run' : False
}

# RF Switch parameters
switch_module = 'x300'
switch_module = 'mock_switch'
switch_connect_params = {
    'ip_addr' : '192.168.82.124'
}
switch_swap_inputs = False
switch_correction_factor_file = './test_results/2024-02-21_14_58_34___setup_calibration/rf_test_setup_calibration.json' #'./test_results/2024-02-21_14_58_34___setup_calibration/rf_test_setup_calibration.json'

############# Logging Parameters #############
logging_save_log_file = True
