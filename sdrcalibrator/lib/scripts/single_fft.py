import numpy as np
from matplotlib import pyplot as plt

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = 'Single FFT'

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [
                'iq_dump'
            ],
            'required_profile_parameters': [],
            'required_equipment': [
                'sdr'
            ],
            'possible_functionality': [
                'apply_stimulus'
            ],
            'profile_parameter_defaults': {
                'logging_save_fft_data': False,
                'logging_save_iq_data': False,
                'logging_plot_fft': True
            },
            'forced_profile_parameters': {}
        }
        super(SDR_Test, self).__init__(profile, logger)

    # Check the profile
    def check_profile(self):
        super(SDR_Test, self).check_profile()

    # Initialize the test
    def initialize_test(self):
        super(SDR_Test, self).initialize_test()

    # Initialize equipment for the test
    def initialize_equipment(self):
        super(SDR_Test, self).initialize_equipment()

    # Run the equipment for the test
    def run_test(self):
        # Calculate the number of bins if necessary
        print("FFT BINS BEFORE CALC",self.profile.fft_number_of_bins)
        self.calculate_fft_num_bins()
        print("FFT BINS AFTER CALC",self.profile.fft_number_of_bins)
        # Create the FFT window
        self.construct_fft_window(self.profile.fft_window, self.profile.fft_number_of_bins)

        # Run the IQ_dump test to get the actual data
        n = self.profile.fft_averaging_number * self.profile.fft_number_of_bins
        self.dependency_test_profile_adjustments = {
            'test_number_of_samples': n
        }
        self.run_dependency_test(
                self.iq_dump,
                self.dependency_test_profile_adjustments
            )
        self.iq_data = self.iq_dump.iq_data
        self.f_f0 = self.iq_dump.f_f0
        self.actual_f0 = self.iq_dump.actual_f0

        # Compute the average FFT
        self.logger.log("Computing the averaged FFT... ")
        print("ACTUAL F0:", self.actual_f0)
        self.fft, self.fft_freqs = self.compute_avg_fft(
                self.iq_data,
                self.actual_f0,
                self.profile.fft_averaging_number
            )
        self.fft = self.normalize_dBm_fft(self.fft)
        self.logger.logln("Done!")

    # Save data or construct plot if required
    def save_data(self):

        # Save the FFT data if requested
        if self.profile.logging_save_fft_data:
            self.logger.log("Writing FFT data to file... ")
            with open(self.save_file("FFT.csv"), 'w+') as file:
                file.write("Frequency (Hz),Power (dBm)\r\n")
                for i in range(len(self.fft)):
                    file.write("{},{}\r\n".format(
                            self.fft_freqs[i],
                            self.fft[i]
                        ))
                file.close()
            self.logger.logln("Done!")

        # Save the IQ data if requested
        if self.profile.logging_save_iq_data:
            self.logger.log("Writing IQ data to file... ")
            with open(self.save_file("iq_dump.csv"), 'w+') as file:
                file.write("I,Q\r\n")
                for datum in self.iq_data:
                    file.write("{},{}\r\n".format(
                            np.real(datum),
                            np.imag(datum)
                        ))
                file.close()
            self.logger.logln("Done!")

        # Create the plot if desired
        if self.profile.logging_plot_fft:
            plt.plot(self.fft_freqs/1e6, self.fft)
            plt.grid(which="both")
            plt.gca().set_xlim([
                    self.fft_freqs[0]/1e6,
                    self.fft_freqs[-1]/1e6
                ])
            plt.xlabel("Frequency (MHz)")
            plt.gca().set_ylim([1.1*np.min(self.fft), 0])
            plt.ylabel("Power (dBm)")
            plt.show()

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
