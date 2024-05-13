import numpy as np
from matplotlib import pyplot as plt

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error

class SDR_Test(SDR_Test_Class):

    # test-specific constants 
    TEST_NAME = 'SDR Connection Test'

    # test constructor 
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [ # other test scripts that will be run by this test script
                'iq_dump'
            ],
            'required_profile_parameters': [],
            'required_equipment': [
                'sdr'
            ],
            'possible_functionality': [
                    
            ],
            'profile_parameter_defaults': {
                'logging_save_test_summary': False,
                'logging_save_fft_data': False,
                'logging_save_iq_data': False,
                'logging_plot_fft': True
            },
            'forced_profile_parameters': {}
        }
        super(SDR_Test, self).__init__(profile, logger)

    # initialize the test
    def initialize_test(self):
        return super().initialize_test()

    # check the profile
    def check_profile(self):
        # If this is the base test, load dummy value for fft_num_bins (dont' need FFT for this test)
        if self.profile.test_type == 'sdr_connection_test':
            self.profile.fft_number_of_bins = None
        # # Otherwise, do not require test_num_samples
        # else:
        #     self.PROFILE_DEFINITIONS['required_profile_parameters'].remove('test_number_of_samples')
        
        # Run the check profile routine
        super(SDR_Test, self).check_profile()

    # initialize equipment for the test 
    def initialize_equipment(self):
        super(SDR_Test, self).initialize_equipment()

    # this function is copied from IQ dump to not break 
    def save_data(self):
        if self.profile.logging_save_iq_data:
            self.logger.log("Writing data to file... ")
            with open(self.save_file("iq_dump.csv"), 'w+') as file:
                file.write("I,Q\r\n")
                for datum in self.iq_data:
                    file.write("{},{}\r\n".format(
                            np.real(datum),
                            np.imag(datum)
                        ))
                file.close()
            self.logger.logln("Done!")

    # Run the test 
    def run_test(self):
        print("RUNNING SDR CONNECTION TEST")

        # Setup stimulus if using it
        self.f_f0 = self.profile.freq_f0
        if self.using_stimulus:
            self.f_f0 = self.setup_stimulus(self.profile.freq_f0, self.profile.power_level)
        
        # Tune the SDR the correct frequency
        self.actual_f0 = self.tune_sdr_to_frequency(self.f_f0)

    