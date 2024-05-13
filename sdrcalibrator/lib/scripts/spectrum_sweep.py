import numpy as np
from matplotlib import pyplot as plt

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "Spectrum Sweep"

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [
                'single_fft'
            ],
            'required_profile_parameters': [
                'test_freq_min',
                'test_freq_max'
            ],
            'required_equipment': [
                'sdr'
            ],
            'possible_functionality': [
                'apply_stimulus'
            ],
            'profile_parameter_defaults': {
                'test_cw_freq': 100e6,
                'test_fft_window_narrowing': 0e6,
                'test_fft_simple_stitching': True,
                'logging_save_spectrum': False,
                'logging_plot_spectrum': True
            },
            'forced_profile_parameters': {
                'freq_f0': False,
                'freq_use_offset': False
            }
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
        # Compute the power levels to sweep
        self.logger.log("Computing sweep frequencies... ")
        f0s = self.compute_spectrum_f0s(self.profile.test_fft_simple_stitching)
        self.computed_f0s = f0s
        self.logger.logln("Done!")
        
        # Compute the block indeces
        self.logger.log("Computing the FFT batch indeces... ")
        self.compute_spectrum_sweep_indeces(self.profile.test_fft_simple_stitching)
        self.logger.log("Done!")

        # Initialize the data arrays
        self.fft_freqs = np.array([])
        self.fft = np.array([])
        lower_f0 = True

        # Setup the stimulus if needed and prevent dependency test from using the stimulus
        if self.using_stimulus:
            self.setup_stimulus(self.profile.test_freq_cw,self.profile.power_level)
            self.single_fft.iq_dump.using_stimulus = False  # I need to figure a better way to do this...
        
        # Turn on the stimulus if using it
        if self.using_stimulus:
            self.stimulus_on()

        # Sweep the frequency and perform a power test at each level
        for i in range(len(self.computed_f0s)):
            self.logger.logln("Getting FFT at {}...".format(
                    self.logger.to_MHz(self.computed_f0s[i])
                ))
            self.logger.stepin()
            self.dependency_test_profile_adjustments = {
                'freq_f0': self.computed_f0s[i],
                'power_stimulus': None
            }
            self.run_dependency_test(
                    self.single_fft,
                    self.dependency_test_profile_adjustments
                )

            # Get the data back out of the test
            self.logger.log("Processing FFT block... ")
            r = self.single_fft
            if self.profile.test_fft_simple_stitching:
                self.fft_freqs = np.append(self.fft_freqs,r.fft_freqs[self.lwli:self.lwui:1])
                self.fft = np.append(self.fft,r.fft[self.lwli:self.lwui:1])
            else:
                lw_fft_freqs = r.fft_freqs[self.lwli:self.lwui:1]
                lw_fft = r.fft[self.lwli:self.lwui:1]
                uw_fft_freqs = r.fft_freqs[self.uwli:self.uwui:1]
                uw_fft = r.fft[self.uwli:self.uwui:1]
                self.fft_freqs = np.append(self.fft_freqs,lw_fft_freqs)
                self.fft = np.append(self.fft,lw_fft)
                if lower_f0:
                    save_fft_freqs = uw_fft_freqs
                    save_fft = uw_fft
                else:
                    self.fft_freqs = np.append(self.fft_freqs,save_fft_freqs)
                    self.fft = np.append(self.fft,save_fft)
                    self.fft_freqs = np.append(self.fft_freqs,uw_fft_freqs)
                    self.fft = np.append(self.fft,uw_fft)
                lower_f0 = not lower_f0
            self.logger.logln("Done!")
            self.logger.stepout()
            self.logger.flush()
        
        # Turn off the stimulus if using it
        if self.using_stimulus:
            self.stimulus_off()

    # Save data or construct plot if required
    def save_data(self):

        # Save the spectrum data if requested
        if self.profile.logging_save_spectrum:
            self.logger.log("Writing spectrum data to file... ")
            with open(self.save_file("spectrum.csv"), 'w+') as file:
                file.write("Frequency (Hz),Power (dBm)\r\n")
                for i in range(len(self.fft)):
                    file.write("{},{}\r\n".format(
                            self.fft_freqs[i],
                            self.fft[i]
                        ))
                file.close()
            self.logger.logln("Done!")

        # Create the plot if desired
        if self.profile.logging_plot_spectrum:
            plt.plot(self.fft_freqs/1e6, self.fft)
            plt.gca().set_ylim([1.1*np.min(self.fft), 0])
            plt.gca().set_xlim([
                    self.fft_freqs[0]/1e6,
                    self.fft_freqs[-1]/1e6
                ])
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Power (dBm)")
            plt.show()

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
