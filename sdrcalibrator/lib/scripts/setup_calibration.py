import numpy as np
from matplotlib import pyplot as plt
from copy import copy, deepcopy
import time

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "Calibration Utility for RF Test Setup"

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
                'power_level', 
            ],
            'required_equipment': [ # switch is added when test option requires it
                'siggen',
                'pwrmtr',
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
                # 'switch_correction_factor_file': None # forces the profile to none
            }
        }
        super(SDR_Test, self).__init__(profile, logger)

    # Check the profile
    def check_profile(self):
        print("CHECKING PROFILE IN SETUP CALIBRATION")
        super(SDR_Test, self).check_profile()

    # Initialize the test
    def initialize_test(self):
        print("INITIALIZING TEST IN SETUP CALIBRATION")
        super(SDR_Test, self).initialize_test()

    # Initialize equipment for the test
    def initialize_equipment(self):
        print("INITIALIZING EQUIPMENT IN SETUP CALIBRATION")
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

        # Perform the frequency sweeps
        for j in range(4):
            # Add this sweeps array
            self.measured_powers.append([])

            # Just add the input values to the array
            if j==0:
                self.logger.log("Recording set power level... ")
                for i in range(len(self.f0s)):
                    self.measured_powers[j].append(self.profile.power_level)
                self.logger.logln("Done!")
                continue

            # Alert the user to which port to plug the power meter into
            if j==1:
                self.logger.query("Plug the power meter into the stimulus output and confirm with [ENTER]... ")
                self.logger.logln("Running frequency sweep through port 0...")
            elif j==2:
                self.logger.query("Replace DUT with the power meter and confirm with [ENTER]... ")
                self.logger.log("Turning switch to port 1... ")
                self.switch.select_sdr()
                self.logger.logln("Done!")
                self.logger.logln("Running frequency sweep through port 1...")
            elif j==3:
                self.logger.query("Plug power verification with the power meter and confirm with [ENTER]... ")
                self.logger.log("Turning switch to port 2... ")
                self.switch.select_meter()
                self.logger.logln("Done!")
                self.logger.logln("Running frequency sweep through port 2...")
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
                self.measured_powers[j].append(measured_power)
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
        
        # Calculate the correction factor
        self.logger.log("Calculating the correction factors... ")
        self.s21s = []
        self.s31s = []
        self.c10s = []
        self.c20s = []
        self.c30s = []
        self.c32s = []
        self.c23s = []
        for i in range(len(self.f0s)):
            self.s21s.append( self.measured_powers[2][i] - self.measured_powers[1][i] )
            self.s31s.append( self.measured_powers[3][i] - self.measured_powers[1][i] )
            self.c10s.append( self.measured_powers[1][i] - self.measured_powers[0][i] )
            self.c20s.append( self.measured_powers[2][i] - self.measured_powers[0][i] )
            self.c30s.append( self.measured_powers[3][i] - self.measured_powers[0][i] )
            self.c32s.append( self.measured_powers[3][i] - self.measured_powers[2][i] )
            self.c23s.append( self.measured_powers[2][i] - self.measured_powers[3][i] )

        self.logger.logln("Done!")

    # Save data or construct plot if required
    def save_data(self):

        # Save the test summary if requested
        if self.profile.logging_save_setup_cal_file:
            self.logger.log("Writing test setup calibration data to file... ")
            correction_factor_json_dict = {}
            correction_factor_json_dict['rf_test_setup_calibration_points'] = []
            with open(self.save_file("setup_calibration_data.csv"), 'w+') as file:
                file.write("Frequency (Hz),Input Power (dBm),P1 measured (dBm),P2 measured (dBm),P3 measured (dBm),")
                file.write("S21 (dB),S31 (dB),C10 (dB),C20 (dB),C30 (dB),C32 (dB),C23 (dB)\r\n")
                for i in range(len(self.f0s)):
                    file.write("{},".format(self.f0s[i]))
                    file.write("{},".format(self.measured_powers[0][i]))
                    file.write("{},".format(self.measured_powers[1][i]))
                    file.write("{},".format(self.measured_powers[2][i]))
                    file.write("{},".format(self.measured_powers[3][i]))
                    file.write("{},".format(self.s21s[i]))
                    file.write("{},".format(self.s31s[i]))
                    file.write("{},".format(self.c10s[i]))
                    file.write("{},".format(self.c20s[i]))
                    file.write("{},".format(self.c30s[i]))
                    file.write("{},".format(self.c32s[i]))
                    file.write("{},".format(self.c23s[i]))
                    file.write("\r\n")
                    correction_factor_json_dict['rf_test_setup_calibration_points'].append({
                        "frequency": self.f0s[i],
                        "input_power": self.measured_powers[0][i],
                        "measured_p1_power": self.measured_powers[1][i],
                        "measured_p2_power": self.measured_powers[2][i],
                        "measured_p3_power": self.measured_powers[3][i],
                        "S21": self.s21s[i],
                        "S31": self.s31s[i],
                        "C10": self.c10s[i],
                        "C20": self.c20s[i],
                        "C30": self.c30s[i],
                        "C32": self.c32s[i],
                        "C23": self.c23s[i]
                    })
                file.close()
            cal_file_name = "rf_test_setup_calibration.json"
            self.write_calibration_file(cal_file_name, src_file=None, json_dict=correction_factor_json_dict)
            
            self.logger.logln("Done!")

        # Create the plot if desired
        if self.profile.logging_plot_setup_cal_values:
            # Scale the frequencies to MHz
            for i in range(len(self.f0s)):
                self.f0s[i] /= 1e6
            # Create the plot for the measured power
            plt.subplot(1,2,1)
            plt.plot(self.f0s,self.measured_powers[0])
            plt.plot(self.f0s,self.measured_powers[1])
            plt.plot(self.f0s,self.measured_powers[2])
            plt.plot(self.f0s,self.measured_powers[3])
            plt.gca().set_xlim([self.f0s[0], self.f0s[-1]])
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Measured Power (dBm)")
            plt.legend(['Input','Port 1','Port 2','Port 3'])

            # Create the plot for the correction factor
            plt.subplot(1,2,2)
            plt.plot(self.f0s,self.s21s)
            plt.plot(self.f0s,self.s31s)
            plt.plot(self.f0s,self.c10s)
            plt.plot(self.f0s,self.c20s)
            plt.plot(self.f0s,self.c30s)
            plt.plot(self.f0s,self.c32s)
            plt.plot(self.f0s,self.c23s)
            plt.gca().set_xlim([self.f0s[0], self.f0s[-1]])
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Correction Factors (dB)")
            plt.legend(['S21','S31','C10','C20','C30','C32','C23'])
            plt.show()

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
