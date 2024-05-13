import numpy as np
from matplotlib import pyplot as plt
from copy import copy, deepcopy
import time

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "Power Measurement with Swept Parameters"

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [
                'power_measurement'
            ],
            'required_profile_parameters': [
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
                'test_check_for_compression': False,
                'test_compression_measurement_method': 'normalized_fft_maximum_power',
                'test_compression_threshold': 1,
                'test_compression_linearity_steps': 5,
                'test_compression_linearity_threshold': 0.1,
                'test_measure_spur_power': False,
                'test_spur_measurement_remove_ranges': [],
                'test_spur_danl_num': 10,
                'test_spur_threshold': 5,
                'logging_save_test_summary': False
            },
            'forced_profile_parameters': {
                'freq_f0': False,
                'power_stimulus': 'single_cw',
                'power_level': False,
                'sdr_gain': 0
            }
        }
        super(SDR_Test, self).__init__(profile, logger)

    # Check the profile
    def check_profile(self):
        super(SDR_Test, self).check_profile()

        # If checking for compression or spur power, ensure that power is swept last
        if self.profile.test_check_for_compression:
            self.profile.sweep_order_3rd = 'power'
            self.profile.sweep_p_order = 'asc'

        # Check to make sure that each parameter is swept
        l1 = ['frequency', 'power', 'gain']
        l2 = [
            self.profile.sweep_order_1st,
            self.profile.sweep_order_2nd,
            self.profile.sweep_order_3rd
        ]
        l1.sort()
        l2.sort()
        if not l1 == l2:
            ehead = 'Parameter sweep order is not valid'
            ebody = 'Sweep order [{},{},{}]\r\n'.format(
                self.profile.sweep_order_1st,
                self.profile.sweep_order_2nd,
                self.profile.sweep_order_3rd
            )
            ebody += 'If you do not want to sweep a parameter, set the num_steps to 0 and the value you wish for the extra.'
            err = SDR_Test_Error(10, ehead, ebody)
            Error.error_out(self.logger, err)
        
        # Check that the compression power measurement method is valid
        check_list = [
            'time_domain_averaged_power',
            'freq_domain_integrated_power',
            'normalized_fft_maximum_power'
        ]
        if not self.profile.test_compression_measurement_method in check_list:
            ehead = 'Invalid power measurement method'
            ebody = "Power measurement method '{}' not supported. Please choose from:\r\n".format(
                self.profile.test_compression_measurement_method
            )
            for i in range(len(check_list)):
                ehead += "    {}\r\n".format(check_list[i])
            err = SDR_Test_Error(10, ehead, ebody)
            Error.error_out(self.logger, err)

    # Initialize the test
    def initialize_test(self):
        super(SDR_Test, self).initialize_test()

    # Initialize equipment for the test
    def initialize_equipment(self):
        super(SDR_Test, self).initialize_equipment()

    # Run the equipment for the test
    def run_test(self):
        # Compute the sweep parameters
        self.compute_swept_power_sweep_parameters()

        # Initialize the data arrays
        empty_data = np.zeros((
            len(self.sweep_list_1),
            len(self.sweep_list_2),
            len(self.sweep_list_3)
        )).tolist()
        self.f_f0s = deepcopy(empty_data)
        self.actual_f0s = deepcopy(empty_data)
        self.f_los = deepcopy(empty_data)
        self.f_dsps = deepcopy(empty_data)
        self.f_cws = deepcopy(empty_data)
        self.normalized_fft_maximum_power_freqs = deepcopy(empty_data)
        self.p_outs = deepcopy(empty_data)
        self.p_ins = deepcopy(empty_data)
        self.gains = deepcopy(empty_data)
        self.measured_powers = deepcopy(empty_data)
        self.time_domain_averaged_powers = deepcopy(empty_data)
        self.freq_domain_integrated_powers = deepcopy(empty_data)
        self.normalized_fft_maximum_powers = deepcopy(empty_data)

        # Add data arrays and variables for compression testing
        if self.profile.test_check_for_compression:
            self.projected_powers = deepcopy(empty_data)
            self.linearity_achieved = None
            self.sdr_powers = None
            self.compression_powers = (np.zeros((
                len(self.sweep_list_1),
                len(self.sweep_list_2)
            ))+100).tolist()
        
        # Add data arrays and variables for spur measurement
        if self.profile.test_measure_spur_power:
            self.spur_powers = deepcopy(empty_data)
            self.spur_frequencies = deepcopy(empty_data)
            self.spur_limit_powers = (np.zeros((
                len(self.sweep_list_1),
                len(self.sweep_list_2)
            ))+100).tolist()

        # Sweep the first parameter
        for i in range(len(self.sweep_list_1)):
            # Set the first parameter
            param = self.sweep_list_1[i]
            if self.profile.sweep_order_1st == 'power':
                power = param
                self.logger.logln("Running power measurement with {} input power...".format(self.logger.to_dBm(power)))
            elif self.profile.sweep_order_1st == 'gain':
                gain = param
                self.logger.logln("Running power measurement with gain of {}dB...".format(gain))
            else:
                f0 = param
                self.logger.logln("Running power measurement with center frequency of {}...".format(self.logger.to_MHz(f0)))
            self.logger.stepin()

            # Sweep the second parameter
            for j in range(len(self.sweep_list_2)):
                # Set the second parameter
                param = self.sweep_list_2[j]
                if self.profile.sweep_order_2nd == 'power':
                    power = param
                    self.logger.logln("Running power measurement with {} input power...".format(self.logger.to_dBm(power)))
                elif self.profile.sweep_order_2nd == 'gain':
                    gain = param
                    self.logger.logln("Running power measurement with gain of {}dB...".format(gain))
                else:
                    f0 = param
                    self.logger.logln("Running power measurement with center frequency of {}...".format(self.logger.to_MHz(f0)))
                self.logger.stepin()

                # If we will check compression, reset parameters associated with the check
                if self.profile.test_check_for_compression:
                    self.linearity_achieved = False
                    self.sdr_powers = []
                
                # If measuring spurious responses, reset parameters associated with the check
                if self.profile.test_measure_spur_power:
                    self.spur_limit_powers[i][j] = 100
                    self.danl_for_spur = 0

                # Sweep the third parameter
                for k in range(len(self.sweep_list_3)):
                    # Set the parameter
                    param = self.sweep_list_3[k]
                    if self.profile.sweep_order_3rd == 'power':
                        power = param
                        self.logger.logln("Running power measurement with {} input power...".format(self.logger.to_dBm(power)))
                    elif self.profile.sweep_order_3rd == 'gain':
                        gain = param
                        self.logger.logln("Running power measurement with gain of {}dB...".format(gain))
                    else:
                        f0 = param
                        self.logger.logln("Running power measurement with center frequency of {}...".format(self.logger.to_MHz(f0)))
                    self.logger.stepin()

                    # Dump the logger file before running the test
                    self.logger.flush()

                    # Set the sdr gain
                    self.set_sdr_gain(gain)

                    # Run the power measurement
                    self.dependency_test_profile_adjustments = {
                        'freq_f0': f0,
                        'power_level': power,
                        'sdr_gain': gain
                    }
                    self.run_dependency_test(
                        self.power_measurement,
                        self.dependency_test_profile_adjustments
                    )

                    # Recover the resultant data
                    r = self.power_measurement
                    self.f_f0s[i][j][k] = r.f_f0
                    self.actual_f0s[i][j][k] = r.actual_f0
                    self.f_los[i][j][k] = r.f_lo
                    self.f_dsps[i][j][k] = r.f_dsp
                    self.f_cws[i][j][k] = r.f_cw
                    self.normalized_fft_maximum_power_freqs[i][j][k] = (
                            r.normalized_fft_maximum_power_freq
                        )
                    self.p_outs[i][j][k] = r.p_out
                    self.p_ins[i][j][k] = r.p_in
                    self.gains[i][j][k] = gain
                    self.measured_powers[i][j][k] = r.measured_power
                    self.time_domain_averaged_powers[i][j][k] = (
                            r.time_domain_averaged_power
                        )
                    self.freq_domain_integrated_powers[i][j][k] = (
                            r.freq_domain_integrated_power
                        )
                    self.normalized_fft_maximum_powers[i][j][k] = (
                            r.normalized_fft_maximum_power
                        )
                    
                    # Measure spur power if requested
                    if self.profile.test_measure_spur_power:
                        # Get the normalized FFT from the power measurement test
                        fft = r.fft.tolist()
                        fft_freqs = r.fft_freqs.tolist()

                        # Remove the requested ranges
                        self.logger.log("Computing spur power after removing requested ranges... ")
                        mid = len(fft_freqs)/2
                        for rem_range in self.profile.test_spur_measurement_remove_ranges:
                            for fft_index in range(len(fft_freqs)-1,-1,-1):
                                scaled_fft_index = 100*(fft_index-mid)/mid
                                if scaled_fft_index >= rem_range[0] and scaled_fft_index <= rem_range[1]:
                                    del fft[fft_index]
                                    del fft_freqs[fft_index]
                        #plt.plot(fft_freqs,fft)
                        #plt.show()

                        # Compute the spur/danl power
                        spur_power, spur_freq = self.compute_normalized_fft_maximum_power_from_fft(
                            fft,
                            fft_freqs
                        )
                        self.spur_powers[i][j][k] = spur_power
                        self.spur_frequencies[i][j][k] = spur_freq
                        self.logger.logln("Done!")
                        self.logger.stepin()
                        self.logger.logln("Computed spur power: {}".format(self.logger.to_dBm(self.spur_powers[i][j][k])))
                        self.logger.logln("Computed spur frequency: {}".format(self.logger.to_MHz(self.spur_frequencies[i][j][k])))
                        self.logger.stepout()

                        # Add the power into the DANL average
                        if k < self.profile.test_spur_danl_num:
                            self.logger.log("Adding spur power to estimated DANL... ")
                            self.danl_for_spur += spur_power/self.profile.test_spur_danl_num
                            self.logger.logln("Done!")
                        # Check if the spur power is above the threshold (if it hasn't already been thresholded)
                        elif self.spur_limit_powers[i][j] == 100:
                            self.logger.log("Checking if the spur power is above the threshold... ")
                            if spur_power > self.danl_for_spur+self.profile.test_spur_threshold:
                                self.logger.logln("Done!")
                                self.spur_limit_powers[i][j] = self.measured_powers[i][j][k]
                                self.logger.stepin()
                                self.logger.logln("Spurious free power limit: {}".format(self.logger.to_dBm(self.spur_limit_powers[i][j])))
                                self.logger.stepout()
                            else:
                                self.logger.logln("Done!")
                    
                    # Do compression checking if requested
                    if self.profile.test_check_for_compression:
                        # Reset variables if starting new freq/gain pair
                        if self.linearity_achieved is None:
                            self.linearity_achieved = False
                        if self.sdr_powers is None:
                            self.sdr_powers = []
                        
                        # Get the SDR power as requested by the profile
                        self.sdr_powers.append(getattr(r, self.profile.test_compression_measurement_method))

                        # If linearity has been achieved, look for the power difference
                        if self.linearity_achieved:
                            self.logger.logln("Checking for compression... ")
                            self.logger.stepin()

                            # Compute the projected power
                            self.projected_powers[i][j][k] = self.lin_vals['lin_eq'](
                                    self.measured_powers[i][j][k]
                                )
                            self.logger.logln("Computed projected power: {}".format(
                                    self.logger.to_dBm(self.projected_powers[i][j][k])
                                ))
                            # Compute the power difference
                            power_dif = np.abs(
                                    self.projected_powers[i][j][k] -
                                    self.sdr_powers[-1]
                                )
                            self.logger.logln("Power difference: {}".format(
                                    self.logger.to_dBm(power_dif)
                                ))
                            # Check if compression has been reached
                            if power_dif > self.profile.test_compression_threshold:
                                self.logger.logln("Compression found at {}".format(
                                        self.measured_powers[i][j][k]
                                    ))
                                self.compression_powers[i][j] = self.sdr_powers[-1]

                                # Label unused data points as None to prevent writing to file
                                self.logger.log("Removing unused points... ")
                                end_del = len(self.sweep_list_3)
                                for del_index in range(k+1, end_del):
                                    self.measured_powers[i][j][del_index] = None
                                self.logger.logln("Done!")

                                # Don't continue power sweep if compression has been reached
                                self.logger.stepout(step_out_num=2)
                                break
                            else:
                                self.logger.stepout()
                        # If sufficient points have been taken, test for linearity
                        elif len(self.sdr_powers) >= self.profile.test_compression_linearity_steps:
                            self.logger.logln("Checking for linearity... ")
                            self.logger.stepin()

                            # Take only the most recent samples
                            sub_measured_powers = []
                            sub_sdr_powers = []
                            for sub_index in range(self.profile.test_compression_linearity_steps):
                                sub_measured_powers.append(self.measured_powers[i][j][k-sub_index])
                                sub_sdr_powers.append(self.sdr_powers[-1-sub_index])

                            # Check for linearity
                            self.linearity_achieved, self.lin_vals = self.check_linearity(
                                    sub_measured_powers,
                                    sub_sdr_powers,
                                    self.profile.test_compression_linearity_threshold,
                                    pin_slope=1, pin_intercept=None
                                )

                            # Compute projected powers if we reached linearity
                            if self.linearity_achieved:
                                for previous_k in range(k+1):
                                    self.projected_powers[i][j][previous_k] = self.lin_vals['lin_eq'](
                                            self.measured_powers[i][j][previous_k]
                                        )
                            self.logger.stepout()
                        else:
                            self.logger.logln("Waiting for {} measurements before checking for linearity...".format(self.profile.test_compression_linearity_steps))
                    # Step the logger out
                    self.logger.stepout()
                # Step the logger out
                self.logger.stepout()
            # Step the logger out
            self.logger.stepout()
        self.logger.logln("Finished sweeping all parameters...")
        self.logger.flush()

    # Save data or construct plot if required
    def save_data(self):

        # Save the test summary if requested
        if self.profile.logging_save_test_summary:
            self.logger.log("Writing test summary data to file... ")
            with open(self.save_file("test_summary.csv"), 'w+') as file:
                file.write(
                        "f0 (Hz),actual_f0 (Hz)," +
                        "f_lo (Hz),f_dsp (Hz),f_CW (Hz)," +
                        "measured_f_CW (Hz),P_out (dBm),P_in (dBm)," +
                        "Gain (dB),measured_power (dBm)," +
                        "time_domain_averaged_power (dBm)," +
                        "freq_domain_integrated_power (dBm)," +
                        "normalized_FFT_maximum_power (dBm)")
                if self.profile.test_check_for_compression:
                    file.write(",projected_powers (dBm)")
                if self.profile.test_measure_spur_power:
                    file.write(",spur_power (dBm),spur_f (Hz)")
                file.write("\r\n")
                for i in range(len(self.sweep_list_1)):
                    for j in range(len(self.sweep_list_2)):
                        for k in range(len(self.sweep_list_3)):
                            # Don't write values labelled with measured_power == None
                            if self.measured_powers[i][j][k] is None:
                                continue
                            file.write("{},{},".format(
                                    self.f_f0s[i][j][k],
                                    self.actual_f0s[i][j][k]
                                ))
                            file.write("{},{},".format(
                                    self.f_los[i][j][k],
                                    self.f_dsps[i][j][k]
                                ))
                            file.write("{},{},".format(
                                    self.f_cws[i][j][k],
                                    self.normalized_fft_maximum_power_freqs[i][j][k]
                                ))
                            file.write("{},{},{},".format(
                                    self.p_outs[i][j][k],
                                    self.p_ins[i][j][k],
                                    self.gains[i][j][k]
                                ))
                            file.write("{},{},{},{}".format(
                                    self.measured_powers[i][j][k],
                                    self.time_domain_averaged_powers[i][j][k],
                                    self.freq_domain_integrated_powers[i][j][k],
                                    self.normalized_fft_maximum_powers[i][j][k]
                                ))
                            if self.profile.test_check_for_compression:
                                file.write(",{}".format(self.projected_powers[i][j][k]))
                            if self.profile.test_measure_spur_power:
                                file.write(",{},{}".format(self.spur_powers[i][j][k],self.spur_frequencies[i][j][k]))
                            file.write("\r\n")
                file.close()
            if self.profile.test_check_for_compression:
                with open(self.save_file("compression_summary.csv"), 'w+') as file:
                    for j in range(len(self.sweep_list_2)):
                        file.write(",{}".format(self.sweep_list_2[j]))
                    file.write("\r\n")
                    for i in range(len(self.sweep_list_1)):
                        file.write("{}".format(self.sweep_list_1[i]))
                        for j in range(len(self.sweep_list_2)):
                            file.write(",{}".format(self.compression_powers[i][j]))
                        file.write("\r\n")
                    file.close()
            if self.profile.test_measure_spur_power:
                with open(self.save_file("spurious free_summary.csv"), 'w+') as file:
                    for j in range(len(self.sweep_list_2)):
                        file.write(",{}".format(self.sweep_list_2[j]))
                    file.write("\r\n")
                    for i in range(len(self.sweep_list_1)):
                        file.write("{}".format(self.sweep_list_1[i]))
                        for j in range(len(self.sweep_list_2)):
                            file.write(",{}".format(self.spur_limit_powers[i][j]))
                        file.write("\r\n")
                    file.close()
            self.logger.logln("Done!")

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
