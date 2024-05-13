import numpy as np
from matplotlib import pyplot as plt
from copy import copy, deepcopy
import time

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "Calibration Utility for an RF Switch"

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
                'logging_save_switch_cal_file': False,
                'logging_save_log_file': False,
                'logging_plot_switch_cal_values': True
            },
            'forced_profile_parameters': {
                'freq_f0': False,
                'fft_number_of_bins': False,
                'power_stimulus': 'single_cw_for_calibration',
                'power_level_mode': 'normal',
                'power_verification': None,
                'sdr_sampling_frequency': 0,
                'switch_correction_factor_file': None
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

        # Initialize the data arrays
        self.p1_measured = np.zeros(len(self.f0s)).tolist()
        self.p2_measured = np.zeros(len(self.f0s)).tolist()

        # Perform the frequency sweeps
        for j in range(2):
            # Alert the user to which port to plug the power meter into
            power_record = np.zeros(len(self.f0s)).tolist()
            if j==0:
                self.logger.query("Plug the power meter into the SDR port of the switch and confirm with [ENTER]... ")
                self.logger.log("Turning switch to sdr port... ")
                self.switch.select_sdr()
                self.logger.logln("Done!")
                self.logger.logln("Running frequency sweep through port 1...")
            else:
                self.logger.query("Plug the power meter into the power meter of the switch and confirm with [ENTER]... ")
                self.logger.log("Turning switch to power meter port... ")
                self.switch.select_meter()
                self.logger.logln("Done!")
                self.logger.logln("Running frequency sweep through port 2...")
            self.logger.stepin()
            
            # Perform the actual frequency sweep
            for i in range(len(power_record)):
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
                power_record[i] = self.pwrmtr.take_measurement(self.profile.power_level)
                self.logger.logln("Done!")
                self.logger.stepin()
                self.logger.logln("Measured power: {}".format(self.logger.to_dBm(power_record[i])))
                self.logger.stepout()

                # Turn on the power
                self.stimulus_off()

                self.logger.stepout()
            # Consolidate data
            self.logger.log("Consolidating data... ")
            if j==0:
                self.p1_measured = deepcopy(power_record)
            else:
                self.p2_measured = deepcopy(power_record)
            self.logger.logln("Done!")

            # Set siggen to preset for changing connections
            self.logger.log("Returning signal generator to preset so it is safe to adjust connections... ")
            self.siggen.preset()
            self.logger.logln("Done!")
            self.logger.stepout()
        
        # Calculate the correction factor
        self.logger.log("Calculating the correction factors... ")
        self.correction_factors = np.zeros(len(self.f0s)).tolist()
        for i in range(len(self.f0s)):
            self.correction_factors[i] = self.p1_measured[i] - self.p2_measured[i]
        self.logger.logln("Done!")

        # Save the switch name for output
        self.switch_name = self.switch.SWITCH_NAME

    # Save data or construct plot if required
    def save_data(self):

        # Save the test summary if requested
        if self.profile.logging_save_switch_cal_file:
            self.logger.log("Writing correction data to file... ")
            correction_factor_json_dict = {}
            correction_factor_json_dict['pwrmtr_correction_factors'] = []
            with open(self.save_file("correction_factors.csv"), 'w+') as file:
                file.write("Cal power:,{}\r\n".format(self.logger.to_dBm(self.profile.power_level)))
                file.write("Frequency (Hz),Cal factor (dB), P1 measured (dBm), P2 measured (dBm)\r\n")
                for i in range(len(self.f0s)):
                    file.write("{},".format(self.f0s[i]))
                    file.write("{},".format(self.correction_factors[i]))
                    file.write("{},".format(self.p1_measured[i]))
                    file.write("{}\r\n".format(self.p2_measured[i]))
                    correction_factor_json_dict['pwrmtr_correction_factors'].append({
                        "frequency": self.f0s[i],
                        "correction_factor": self.correction_factors[i]
                    })
                file.close()
            cal_file_name = "rf_switch_{}_calibration.json".format(self.switch_name)
            self.write_calibration_file(cal_file_name, src_file=None, json_dict=correction_factor_json_dict)
            
            self.logger.logln("Done!")

        # Create the plot if desired
        if self.profile.logging_plot_switch_cal_values:
            # Scale the frequencies to MHz
            for i in range(len(self.f0s)):
                self.f0s[i] /= 1e6
            # Create the plot for the measured power
            plt.subplot(1,2,1)
            plt.plot(self.f0s,self.p1_measured)
            plt.plot(self.f0s,self.p2_measured)
            plt.gca().set_xlim([self.f0s[0], self.f0s[-1]])
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Measured Power (dBm)")
            plt.legend(['Port 1','Port 2'])

            # Create the plot for the correction factor
            plt.subplot(1,2,2)
            plt.plot(self.f0s,self.correction_factors)
            plt.gca().set_xlim([self.f0s[0], self.f0s[-1]])
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Correction Factor (dB)")
            plt.show()

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
