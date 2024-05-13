import numpy as np
from matplotlib import pyplot as plt

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


""" Definition of the SDR_Test class for IQ Data Dump """
class SDR_Test(SDR_Test_Class):

    """ Test name and profile setup"""
    TEST_NAME = 'IQ Data Dump'

    """ Create the test """
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [],
            'required_profile_parameters': [
                'test_number_of_samples'
            ],
            'required_equipment': [
                'sdr'
            ],
            'possible_functionality': [
                'apply_stimulus',
                'verify_power'
            ],
            'profile_parameter_defaults': {
                'logging_save_iq_data': False,
                'logging_plot_histogram': False,
                'logging_plot_num_hist_bins': 30
            },
            'forced_profile_parameters': {}
        }
        super(SDR_Test, self).__init__(profile, logger)

    """ Initialize the test """
    def initialize_test(self):
        super(SDR_Test, self).initialize_test()

    """ Check the profile """
    def check_profile(self):
        # If this is the base test, load dummy value for fft_num_bins
        if self.profile.test_type == 'iq_dump':
            self.profile.fft_number_of_bins = None
        # Otherwise, do not require test_num_samples
        else:
            self.PROFILE_DEFINITIONS['required_profile_parameters'].remove('test_number_of_samples')
        
        # Run the check profile routine
        super(SDR_Test, self).check_profile()

    """ Initialize equipment for the test """
    def initialize_equipment(self):
        super(SDR_Test, self).initialize_equipment()

    """ Run the test """
    def run_test(self):
        # Setup stimulus if using it
        self.f_f0 = self.profile.freq_f0
        if self.using_stimulus:
            self.f_f0 = self.setup_stimulus(self.profile.freq_f0, self.profile.power_level)

        # Tune the SDR the correct frequency
        self.actual_f0 = self.tune_sdr_to_frequency(self.f_f0)

        # Get the scale factor for the setup
        self.calculate_scale_factor()

        # Turn on the stimulus if using it
        if self.using_stimulus:
            self.stimulus_on()

        # Read in the samples
        self.iq_data = self.acquire_samples(self.profile.test_number_of_samples)

        # Turn off the stimulus if using it
        if self.using_stimulus:
            self.stimulus_off()
        
        # Grab the Keysight scale factor and dump to file
        if self.profile.sdr_module == 'keysight':
            keysight_freq = self.sdr.current_tuned_frequency()
            keysight_sample_rate = self.sdr.get_sampling_frequency()
            keysight_attenuation = self.sdr.get_attenuation()
            keysight_voltage_scale_factor = self.sdr.get_last_scale_factor()
            keysight_power_scale_factor = 20*np.log10(keysight_voltage_scale_factor)


    """ Save the test data as defined in the profile """
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
        
        # Create the plot if desired
        if self.profile.logging_plot_histogram:
            fig, axs = plt.subplots(1,3)
            # Create the I data histogram
            axs[0].hist(np.real(self.iq_data),self.profile.logging_plot_num_hist_bins)
            axs[0].set_title("I histogram")
            axs[0].set_xlabel("V (V)")
            axs[0].set_ylabel("Number")
            # Create the Q data histogram
            axs[1].hist(np.imag(self.iq_data),self.profile.logging_plot_num_hist_bins)
            axs[1].set_title("Q histogram")
            axs[1].set_xlabel("V (V)")
            axs[1].set_ylabel("Number")
            # Create the power data histogram
            axs[2].hist((np.abs(self.iq_data)**2)/50,self.profile.logging_plot_num_hist_bins)
            axs[2].set_title("Power histogram")
            axs[2].set_xlabel("P (W)")
            axs[2].set_ylabel("Number")
            
            plt.show()
            
            # Create test distribution for the APD APD
            test_len = 1000
            test_iq = np.random.randn(test_len) + 1j*np.random.randn(test_len)
            #amplitudes = np.sort(np.abs(test_iq))

            # Create the amplitudes/probabilities for the APD
            amplitudes = np.sort(np.abs(self.iq_data))
            probabilities = 1 - ((np.arange(len(amplitudes)) + 1) / len(amplitudes))
            #plt.plot(probabilities)
            #plt.show()

            # Scale the APD to Rayleigh axes
            xticklabels = ['0.0001', '0.01', '0.1', '1', '5', '10', '20', '30', '40', '50', '60', '70', '80', '90', '95', '98', '99', '99.9']
            ptick = np.array([0.0001, 0.01, 0.1, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98, 99, 99.9]) / 100
            porigin = ptick[0]
            xtick = 10 * np.log10(-1 * np.log(porigin)) - 10 * np.log10(-1 * np.log(ptick))
            amplitudes = amplitudes.astype(float)
            amplitudes[amplitudes==0] = np.nan
            probabilities[-1] = np.nan
            apd_x = 10 * np.log10(-1 * np.log(porigin)) - 10 * np.log10(-1 * np.log(probabilities))
            apd_y = 20 * np.log10(amplitudes)
            #plt.plot(apd_x)
            #plt.show()

            # Create the APD plot
            fix, ax = plt.subplots()
            print(len(apd_x))
            ax.plot(apd_x, apd_y)
            ax.set_xlabel('Percent Exceeding Ordinate (%)')
            #ax.set_xlim(np.min(xtick), np.max(xtick))
            ax.set_xticks(xtick)
            ax.set_xticklabels(xticklabels, rotation=-90)
            ax.grid(True, 'minor', 'y', alpha=0.75)
            ax.grid(True, 'major', 'both', alpha=0.5)
            ax.set_ylabel('Amplitude (dBV)')
            plt.show()

            if self.profile.logging_save_iq_data:
                self.logger.log("Writing apd data to file... ")
                with open(self.save_file("apd_dump.csv"), 'w+') as file:
                    file.write("Per_exceeding_ord, Magnitude\r\n")
                    for i in range(len(apd_x)):
                        file.write("{},{}\r\n".format(
                                apd_x[i],
                                apd_y[i]
                            ))
                    file.close()
                self.logger.logln("Done!")

    """ Perform cleanup as necessary """
    def cleanup(self):
        super(SDR_Test, self).cleanup()
