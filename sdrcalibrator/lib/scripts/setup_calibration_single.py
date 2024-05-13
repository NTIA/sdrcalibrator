import numpy as np
from matplotlib import pyplot as plt
from copy import copy, deepcopy
import time

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "Calibration Utility for RF Test Setup - Single Port"

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [],
            'required_profile_parameters': [
                'test_type',
                'sweep_f_min',
                'sweep_f_max',
                'sweep_f_num_steps',
                'sweep_f_lin_spacing',
                'sweep_f_log_steps',
                'sweep_f_extra',
                'sweep_f_order',
                'power_level'
            ],
            'required_equipment': [
                'siggen',
                'pwrmtr',
                'switch'
            ],
            'possible_functionality': [
                'apply_stimulus'
            ],
            'profile_parameter_defaults': {
                'logging_quiet_mode': False,
                'logging_save_setup_cal_file': False,
                'logging_plot_setup_cal_values': True
            },
            'forced_profile_parameters': {
                'freq_f0': False,
                'fft_number_of_bins': False,
                'power_stimulus': 'single_cw_for_calibration',
                'power_level_mode': 'normal',
                'power_verification': None,
                'sdr_sampling_frequency': 0,
                # 'switch_correction_factor_file': None # this means you can't load switch correction factor
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
        # Compute the frequency sweep parameters
        self.f0s = self.create_swept_parameter(
            self.profile.sweep_f_min,
            self.profile.sweep_f_max,
            self.profile.sweep_f_num_steps,
            self.profile.sweep_f_lin_spacing,
            self.profile.sweep_f_log_steps,
            self.profile.sweep_f_extra,
            self.profile.sweep_f_order
        )

        # Initialize the data array
        self.measured_powers = []
            
        self.logger.query("Replace DUT with the power meter and confirm with [ENTER]... ")
        if self.profile.measure_port == 1:
            self.logger.log("Turning switch to port 1... ")
            self.switch.select_sdr()
            self.logger.logln("Done!")
        else:
            self.logger.log("Turning switch to port 2... ")
            self.switch.select_meter()
            self.logger.logln("Done!")
        self.logger.logln("Running frequency sweep through port...")
        self.logger.stepin()
            
        # Perform the actual frequency sweep
        for i in range(len(self.f0s)):
            self.logger.logln("Measuring at {}...".format(self.logger.to_MHz(self.f0s[i])))
            self.logger.stepin()

            # Setup the CW input
            self.setup_stimulus(self.f0s[i], self.profile.power_level)

            # Tune the power meter to the CW frequency
            self.logger.log("Tuning power meter to {}... ".format(self.logger.to_MHz(self.f0s[i])))
            self.pwrmtr.tune_to_frequency(self.f0s[i])
            self.logger.logln("Done!")

            # Turn on the power
            self.stimulus_on()

            # Measure the power with the power meter
            self.logger.log("Measuring power with the power meter... ")
            measured_power = self.pwrmtr.take_measurement(self.profile.power_level)
            self.measured_powers.append(measured_power)
            self.logger.logln("Done!")
            self.logger.stepin()
            self.logger.logln("Measured power: {}".format(self.logger.to_dBm(measured_power)))
            self.logger.stepout()

            # Turn on the power
            self.stimulus_off()

            self.logger.stepout()

        # Set siggen to preset for changing connections
        self.logger.log("Returning signal generator to preset so it is safe to adjust connections... ")
        self.siggen.preset()
        self.logger.logln("Done!")
        self.logger.stepout()

    # Save data or construct plot if required
    def save_data(self):

        # Save the test summary if requested
        if self.profile.logging_save_setup_cal_file:
            self.logger.log("Writing test setup calibration data to file... ")
            correction_factor_json_dict = {}
            correction_factor_json_dict['rf_test_setup_calibration_points'] = []
            with open(self.save_file("setup_calibration_data.csv"), 'w+') as file:
                file.write("Frequency (Hz),Measured Power (dBm)\r\n")
                for i in range(len(self.f0s)):
                    file.write("{},".format(self.f0s[i]))
                    file.write("{},".format(self.measured_powers[i]))
                    file.write("\r\n")
                    correction_factor_json_dict['rf_test_setup_calibration_points'].append({
                        "frequency": self.f0s[i],
                        "measured_power": self.measured_powers[i]
                    })
                file.close()
            cal_file_name = "rf_test_setup_calibration_single.json"
            self.write_calibration_file(cal_file_name, src_file=None, json_dict=correction_factor_json_dict)
            
            self.logger.logln("Done!")

        # Create the plot if desired
        if self.profile.logging_plot_setup_cal_values:
            # Scale the frequencies to MHz
            for i in range(len(self.f0s)):
                self.f0s[i] /= 1e6
            # Create the plot for the measured power
            plt.plot(self.f0s,self.measured_powers)
            plt.gca().set_xlim([self.f0s[0], self.f0s[-1]])
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Measured Power (dBm)")
            plt.show()

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
