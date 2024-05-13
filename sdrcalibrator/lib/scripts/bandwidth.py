import numpy as np
from matplotlib import pyplot as plt

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "Receiver Bandwidth Measurement"
    

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [
                'power_measurement'
            ],
            'required_profile_parameters': [
                'test_type',
                'test_bandwidth_to_measure',
                'test_bandwidth_steps'
            ],
            'required_equipment': [
                'sdr',
                'siggen'
            ],
            'possible_functionality': [
                'apply_stimulus',
                'verify_power'
            ],
            'profile_parameter_defaults': {
                'logging_save_test_summary': False,
                'logging_save_transfer_function': False,
                'logging_plot_transfer_function': True
            },
            'forced_profile_parameters': {
                'power_stimulus': 'single_cw',
                'freq_use_offset': True,
                'freq_offset_f0_and_cw': False,
                'freq_offset_using_sdr': False,
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
        # Compute offsets needed to sweep the input frequency
        self.logger.log(
                "Computing offsets to create desired frequency sweep... "
            )
        self.f_offsets = np.linspace(
                -1*self.profile.test_bandwidth_to_measure/2,
                self.profile.test_bandwidth_to_measure/2,
                self.profile.test_bandwidth_steps
            )
        self.f_cws = self.f_offsets + self.profile.freq_f0
        self.f_cws = self.f_cws.tolist()
        self.logger.logln("Done!")

        # Sweep the power and perform a power test at each level
        self.sdr_power_levels = np.zeros(len(self.f_offsets)).tolist()
        self.measured_power_levels = np.zeros(len(self.f_offsets)).tolist()
        for i in range(len(self.f_offsets)):
            self.logger.logln("Measuring power at {}...".format(
                    self.logger.to_MHz(self.f_cws[i])
                ))
            self.logger.stepin()
            self.dependency_test_profile_adjustments = {
                    'freq_offset_f0_and_cw': self.f_offsets[i]
                }
            self.run_dependency_test(
                    self.power_measurement,
                    self.dependency_test_profile_adjustments
                )
            r = self.power_measurement
            self.sdr_power_levels[i] = r.normalized_fft_maximum_power
            self.measured_power_levels[i] = r.measured_power
            self.logger.stepout()
            self.logger.flush()

        # Calculate the transfer function and the bandwidths
        self.logger.log("Calculating the tranfer function and ENBW... ")
        self.h_dB = self.compute_dB_transfer_function(
                self.sdr_power_levels, self.measured_power_levels
            )
        self.bandwidth_3dB = self.compute_dB_bandwidth(
                self.h_dB, self.f_offsets, 3
            )
        enb = self.compute_equivalent_noise_bandwidth(
                self.h_dB, self.f_offsets
            )
        self.equivalent_noise_bandwidth = enb

    # Save data or construct plot if required
    def save_data(self):
        if self.profile.logging_save_test_summary:
            self.logger.log("Writing test summary data to file... ")
            with open(self.save_file("Test_summary.txt"), 'w+') as file:
                file.write("3dB bandwidth (Hz): {}\r\n".format(
                        self.logger.to_MHz(self.bandwidth_3dB)
                    ))
                file.write("Equivalent Noise Bandwidth (Hz): {}".format(
                        self.logger.to_MHz(self.equivalent_noise_bandwidth)
                    ))
                file.close()
            self.logger.logln("Done!")
        if self.profile.logging_save_transfer_function:
            self.logger.log("Writing transfer function to file... ")
            with open(self.save_file("Transfer_function.csv"), 'w+') as file:
                file.write("Frequency (Hz),|H| (dB),")
                file.write("Applied power (dBm),")
                file.write("Measured power (dBm)\r\n")
                for i in range(len(self.f_cws)):
                    file.write("{},{},{},{}\r\n".format(
                            self.f_cws[i],
                            self.h_dB[i],
                            self.measured_power_levels[i],
                            self.sdr_power_levels[i]
                        ))
                file.close()
            self.logger.logln("Done!")

        # Create the plot if desired
        if self.profile.logging_plot_transfer_function:
            plt.plot(np.asarray(self.f_cws)/1e6, self.h_dB)
            yrange_buffer = 0.1*(np.amax(self.h_dB) - np.amin(self.h_dB))
            plt.gca().set_ylim([
                    np.amin(self.h_dB)-yrange_buffer,
                    np.amax(self.h_dB)+yrange_buffer
                ])
            plt.gca().set_xlim([
                    self.f_cws[0]/1e6,
                    self.f_cws[-1]/1e6
                ])
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("|H| (dB)")
            plt.text(
                    (self.f_cws[0]
                        + 0.02 * self.profile.test_bandwidth_to_measure)/1e6,
                    np.amax(self.h_dB) - (1 * yrange_buffer),
                    "3dB bandwidth: {}".format(
                        self.logger.to_MHz(self.bandwidth_3dB)
                    )
                )
            plt.text(
                    (self.f_cws[0]
                        + 0.02 * self.profile.test_bandwidth_to_measure)/1e6,
                    np.amax(self.h_dB) - (2 * yrange_buffer),
                    "Equivalent noise bandwidth: {}".format(
                        self.logger.to_MHz(self.equivalent_noise_bandwidth)
                    )
                )
            plt.show()

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
