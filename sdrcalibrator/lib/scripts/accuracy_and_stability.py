import time
import numpy as np

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.common as utils
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "Accuracy and Stability Measurement"

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [
                'swept_power_measurement'
            ],
            'required_profile_parameters': [
                'test_delay_between_sweeps',
                'test_cycle_use_time',
                'test_cycle_sweeping_time',
                'test_cycle_number_of_sweeps',
                'sweep_order_1st',
                'sweep_order_2nd',
                'sweep_order_3rd'
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
                'test_power_measurement_method': 'normalized_fft_maximum_powers',
                'logging_distribute_data_files': False,
                'logging_save_test_results': False
            },
            'forced_profile_parameters': {
                'test_check_for_compression': False,
                'test_measure_spur_power': False,
                'freq_f0': False,
                'power_stimulus': 'single_cw',
                'power_level': False,
                'sdr_gain': 0
            }
        }
        super(SDR_Test, self).__init__(profile, logger)

    # Check the profile
    def check_profile(self):
        # Check that the power measurement method is valid
        if self.profile_parameter_exists('test_power_measurement_method'):
            check_list = [
                'time_domain_averaged_power',
                'freq_domain_integrated_power',
                'normalized_fft_maximum_power'
            ]
            if not self.profile.test_power_measurement_method in check_list:
                ehead = 'Invalid power measurement method'
                ebody = "Power measurement method '{}' not supported. Please choose from:\r\n".format(
                    self.profile.test_power_measurement_method
                )
                for i in range(len(check_list)):
                    ebody += "    {}\r\n".format(check_list[i])
                err = SDR_Test_Error(10, ehead, ebody)
                Error.error_out(self.logger, err)
            self.profile.test_power_measurement_method += 's'
        super(SDR_Test, self).check_profile()

    # Initialize the test
    def initialize_test(self):
        super(SDR_Test, self).initialize_test()

    # Initialize equipment for the test
    def initialize_equipment(self):
        super(SDR_Test, self).initialize_equipment()
    
    # Construct a save file based on gain
    def gain_save_file(self, gain):
        return self.save_file("{}dB_gain_data.csv".format(gain))
    
    # Construct a save file based on power
    def power_save_file(self, power):
        return self.save_file("{}_power_data.csv".format(self.logger.to_dBm(power)))
    
    # Construct a save file based on frequency
    def frequency_save_file(self, f):
        return self.save_file("{}_data.csv".format(self.logger.to_MHz(f)))
    
    # Construct the default save file
    def default_save_file(self, dummy=None):
        return self.save_file('data.csv')

    # Run the equipment for the test
    def run_test(self):
        # Keep track of cycle number
        self.cycle_num = 0

        # Determine the save file name function
        if self.profile.sweep_order_1st == 'frequency':
            self.gen_save_file = self.frequency_save_file
        elif self.profile.sweep_order_1st == 'gain':
            self.gen_save_file = self.gain_save_file
        else:
            self.gen_save_file = self.power_save_file
        if not self.profile.logging_distribute_data_files:
            self.gen_save_file = self.default_save_file

        # Run test until completion
        while not self.cycling_complete(self.cycle_num):

            # Wait if needed
            if self.cycle_num > 0:
                self.logger.log("Waiting {}s for next cycle... ".format(
                    self.profile.test_delay_between_sweeps))
                time.sleep(self.profile.test_delay_between_sweeps)
                self.logger.logln("Done!")

            # Run the cycle
            self.cycle_num += 1
            self.logger.logln("Running cycle number {}...".format(self.cycle_num))
            self.logger.stepin()

            # Run the Swept Power Measurement Test
            self.run_dependency_test(
                self.swept_power_measurement,
                {}
            )
            r = self.swept_power_measurement
            self.logger.stepout()

            # Save the output data
            if self.profile.logging_save_test_results:
                # Check if the files need to be generated
                if self.cycle_num == 1:
                    self.logger.log("Generating output files... ")
                    for i in range(len(r.sweep_list_1)):
                        with open(self.gen_save_file(r.sweep_list_1[i]), 'w+') as file:
                            file.write(
                                "Cycle," +
                                "Time (s)," +
                                "f0 (Hz)," +
                                "Actual f0 (Hz)," +
                                "CW (Hz)," +
                                "Measured CW (Hz)," +
                                "P out (dBm)," +
                                "P in (dBm)," +
                                "Gain (dBm)," +
                                "Measured power (dBm)," +
                                "SDR power (dBm)\r\n"
                            )
                            file.close()
                    self.logger.logln("Done!")
                
                # Append the data to the file/s
                self.logger.log("Writing data to file/s... ")
                for i in range(len(r.sweep_list_1)):
                    with open(self.gen_save_file(r.sweep_list_1[i]), 'a+') as file:
                        for j in range(len(r.sweep_list_2)):
                            for k in range(len(r.sweep_list_3)):
                                data_line = "{}".format(self.cycle_num)
                                data_line += ",{}".format(time.time() - self.start_time)
                                data_line += ",{}".format(r.f_f0s[i][j][k])
                                data_line += ",{}".format(r.actual_f0s[i][j][k])
                                data_line += ",{}".format(r.f_cws[i][j][k])
                                data_line += ",{}".format(r.normalized_fft_maximum_power_freqs[i][j][k])
                                data_line += ",{}".format(r.p_outs[i][j][k])
                                data_line += ",{}".format(r.p_ins[i][j][k])
                                data_line += ",{}".format(r.gains[i][j][k])
                                data_line += ",{}".format(r.measured_powers[i][j][k])
                                sdr_powers = getattr(r, self.profile.test_power_measurement_method)
                                data_line += ",{}".format(sdr_powers[i][j][k])
                                data_line += "\r\n"
                                file.write(data_line)
                self.logger.logln("Done!")

    # Save data or construct plot if required
    def save_data(self):
        self.logger.logln("Data was saved during test...")
        return

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
