import numpy as np
from matplotlib import pyplot as plt

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = 'Power Measurement'

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [
                'iq_dump'
            ],
            'required_profile_parameters': [],
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
        self.calculate_fft_num_bins()

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
        self.f_lo = self.sdr.current_lo_frequency()
        self.f_dsp = self.sdr.current_dsp_frequency()
        self.recover_stimulus_parameters_from_dependency_test(self.iq_dump)

        # Calculate the power each way
        self.logger.logln("Computing the SDR measured power... ")
        self.logger.stepin()
        tdip = self.compute_time_domain_averaged_power(
                self.iq_data
            )
        self.time_domain_averaged_power = tdip
        self.logger.logln("Time domain average: {} dBm".format(tdip))
        fft, fft_freqs = self.compute_avg_dBm_fft(
                self.iq_data,
                self.actual_f0,
                self.profile.fft_averaging_number
            )
        fdip = self.compute_freq_domain_integrated_power(
                self.iq_data
            )
        self.freq_domain_integrated_power = fdip
        self.logger.logln("Freq domain integrated: {} dBm".format(fdip))
        #fft, fft_freqs = self.compute_avg_dBm_fft(
        #        self.iq_data,
        #        self.actual_f0,
        #        self.profile.fft_averaging_number
        #    )
        fft, fft_freqs = self.compute_avg_fft(
                self.iq_data,
                self.actual_f0,
                self.profile.fft_averaging_number
            )
        fft = self.normalize_dBm_fft(fft)
        self.fft, self.fft_freqs = fft, fft_freqs
        nfmp, nfmp_freq = self.compute_normalized_fft_maximum_power_from_fft(
                self.fft,
                self.fft_freqs
            )
        self.normalized_fft_maximum_power = nfmp
        self.normalized_fft_maximum_power_freq = nfmp_freq
        self.logger.logln("Normalized FFT max: {} dBm".format(nfmp))
        self.logger.stepout()

    # Save data or construct plot if required
    def save_data(self):

        # Save the test summary if requested
        if self.profile.logging_save_test_summary:
            self.logger.log("Writing test summary to file... ")
            with open(self.save_file("Power_summary.csv"), 'w+') as file:
                file.write("Set f0 (Hz),{}\r\n".format(
                        self.f_f0
                    ))
                file.write("Actual_f0 (Hz),{}\r\n".format(
                        self.actual_f0
                    ))
                if hasattr(self,'f_cw'):
                    file.write("Set f_CW (Hz),{}\r\n".format(
                            self.f_cw
                        ))
                    file.write("Measured f_CW (Hz),{}\r\n".format(
                            self.normalized_fft_maximum_power_freq
                        ))
                    file.write("P set (dBm),{}\r\n".format(
                            self.p_out
                        ))
                    file.write("P applied (dBm),{}\r\n".format(
                            self.p_in
                        ))
                    file.write("P Measured (dBm),{}\r\n".format(
                            self.measured_power
                        ))
                file.write("P time domain integrated (dBm),{}\r\n".format(
                        self.time_domain_averaged_power
                    ))
                file.write("P freq domain integrated (dBm),{}\r\n".format(
                        self.freq_domain_integrated_power
                    ))
                file.write("P normalized FFT (dBm),{}\r\n".format(
                        self.normalized_fft_maximum_power
                    ))
                file.close()
            self.logger.logln("Done!")

        # Save the FFT if requested
        if self.profile.logging_save_fft_data:
            self.logger.log("Writing FFT data to file... ")
            with open(self.save_file("SDR_FFT.csv"), 'w+') as file:
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
            plt.plot(
                    self.fft_freqs/1e6,
                    self.fft
                )
            plt.gca().set_ylim([
                    1.1*np.amin(self.fft),
                    0
                ])
            plt.gca().set_xlim([
                    self.fft_freqs[0]/1e6,
                    self.fft_freqs[-1]/1e6
                ])
            plt.title("Normalized Signal FFT")
            text_x_offset = (
                    self.fft_freqs[0] +
                    0.05*self.profile.sdr_sampling_frequency
                )/1e6
            plt.text(
                    text_x_offset,
                    -10,
                    "Time domain averaged power: {}".format(
                        self.logger.to_dBm(
                            self.time_domain_averaged_power
                        )
                    )
                )
            plt.text(
                    text_x_offset,
                    -20,
                    "Frequency domain integrated power: {}".format(
                        self.logger.to_dBm(
                            self.freq_domain_integrated_power
                        )
                    )
                )
            plt.text(
                    text_x_offset,
                    -30,
                    "Normalized FFT maximum: {}".format(
                        self.logger.to_dBm(
                            self.normalized_fft_maximum_power
                        )
                    )
                )
            plt.text(
                    text_x_offset,
                    -40,
                    "Measured CW frequency: {}".format(
                        self.logger.to_MHz(
                            self.normalized_fft_maximum_power_freq
                        )
                    )
                )
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Power (dBm)")
            plt.show()

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
