import numpy as np
from matplotlib import pyplot as plt
from copy import copy, deepcopy
import datetime, json
import time

import sdrcalibrator.lib.utils.common as utils
from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "Calibrate"

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [
                'scale_factor',
                'swept_power_measurement',
                'bandwidth'
            ],
            'required_profile_parameters': [
                'test_measure_scale_factor',
                'test_measure_enbws',
                'test_measure_noise_figure',
                'test_measure_compression',
                'test_measure_spur_free',
                'test_sample_rates',
                'test_clock_frequencies'
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
                'noise_figure_terminating': False,
                'noise_figure_input_power': -200,
                'compression_skip_sample_rate_cycling': False,
                'compression_decimate_frequencies': False,
                'compression_decimate_gains': False,
                'enbw_measurement_band_stretch': 1.5,
                'enbw_transfer_function_points': 150
            },
            'forced_profile_parameters': {
                'freq_f0': False,
                'power_stimulus': 'single_cw',
                'power_level': -275,
                'sdr_power_scale_factor': 0,
                'sdr_power_scale_factor_file': False,
                'sweep_f_order': 'asc',
                'sweep_g_order': 'asc',
                'sweep_order_1st': 'frequency',
                'sweep_order_2nd': 'gain',
                'sweep_order_3rd': 'power',
                'test_bandwidth_to_measure': False,
                'test_bandwidth_steps': False,
                'test_measure_spur_free': False # This is not implemented yet
            }
        }
        super(SDR_Test, self).__init__(profile, logger)

    # Check the profile
    def check_profile(self):
        # Add profile definitions based on whether scale factors are measured
        if self.profile.test_measure_scale_factor:
            self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                'scale_factor_power_level',
                'scale_factor_measurement_method'
            ])
        
        # Add profile definitions based on whether enbws are measured
        if self.profile.test_measure_enbws:
            self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                'enbw_frequency',
                'enbw_gain',
                'enbw_power_level'
            ])
        
        # Save freq_offset_f0_and_cw because the bandwidth test will overwrite
        saved_freq_offset_f0_and_cw = self.profile.freq_offset_f0_and_cw
        
        # Add profile definitions based on whether noise figures are measured
        if self.profile.test_measure_noise_figure:
            # If not measuring enbws, make sure they are provided noise_figure_enbws
            if not self.profile.test_measure_enbws:
                self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                    'noise_figure_enbws'
                ])
        
        # Add profile definitions based on whether compressions are measured
        if self.profile.test_measure_compression:
            self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                'compression_min_power',
                'compression_max_power',
                'compression_power_step',
                'compression_measurement_method',
                'compression_threshold',
                'compression_linearity_steps',
                'compression_linearity_threshold'
            ])
        
        # Add profile definitions based on whether enbws are measured (NOT IMPLEMENTED YET)
        self.profile.test_measure_spur_free = False
        if self.profile.test_measure_spur_free:
            pass
        
        # Merge and profile definition changes
        self.merge_profile_definitions()

        # Ensure the profile matches the definitions
        super(SDR_Test, self).check_profile()

        # Fix the sweep order after the scale factor test breaks it
        if self.profile.test_measure_scale_factor:
            self.profile.sweep_order_1st = 'frequency'
            self.profile.sweep_order_2nd = 'gain'
            self.profile.sweep_order_3rd = 'power'
        
        # Fix the freq_offset_f0_and_cw after bandwidth breaks it
        self.profile.freq_offset_f0_and_cw = saved_freq_offset_f0_and_cw
        
        # Check that there are the same number of sample rates and clock frequencies
        if not len(self.profile.test_sample_rates) == len(self.profile.test_clock_frequencies):
            ehead = 'Sample rate and clock frequency mismatch'
            ebody = (
                "The number of sample rates and clock frequencies must be the same:\r\n" +
                "    Sample rates:     {}\r\n" +
                "    Clock frequencies {}"
            ).format(
                self.profile.test_sample_rates,
                self.profile.test_clock_frequencies
            )
            err = SDR_Test_Error(10, ehead, ebody)
            Error.error_out(self.logger, err)
        
        # Check that there are the same number of sample rates and enbws if not measuring
        if self.profile.test_measure_noise_figure and not self.profile.test_measure_enbws:
            if not len(self.profile.test_sample_rates) == len(self.profile.noise_figure_enbws):
                ehead = 'Sample rate and equivalent noise bandwidth mismatch'
                ebody = (
                    "The number of sample rates and equivalent noise bandwidths must be the same:\r\n" +
                    "    Sample rates: {}\r\n" +
                    "    EQNBs:        {}"
                ).format(
                    self.profile.test_sample_rates,
                    self.profile.noise_figure_enbws
                )
                err = SDR_Test_Error(10, ehead, ebody)
                Error.error_out(self.logger, err)
        
        # If not decimating frequencies/gains, set decimation rate to 1
        if not self.profile.compression_decimate_frequencies:
            self.profile.compression_decimate_frequencies = 1
        if not self.profile.compression_decimate_gains:
            self.profile.compression_decimate_gains = 1
        
        # Check enbw parameters if running test
        if self.profile.test_measure_enbws:
            # Make sure the ENBW stretch ratio is greater than 1 
            if self.profile.enbw_measurement_band_stretch <= 1:
                ehead = 'ENBW stretch ratio must be greater than 1'
                ebody = (
                    "To accurately measure the equivalent noise bandwidth, the measured band\r\n" +
                    "must be greater than the sample rate (enbw_measurement_band_stretch > 1):\r\n"
                    "    Requested enbw_measurement_band_stretch: {}"
                ).format(
                    self.profile.enbw_measurement_band_stretch
                )
                err = SDR_Test_Error(10, ehead, ebody)
                Error.error_out(self.logger, err)

    # Initialize the test
    def initialize_test(self):
        super(SDR_Test, self).initialize_test()

    # Initialize equipment for the test
    def initialize_equipment(self):
        super(SDR_Test, self).initialize_equipment()
    
    # Pause and wait for the user to press enter
    def pause_for_user_action(self, msg):
        self.logger.logln()
        self.logger.logln()
        self.logger.logln("!!! USER ACTION REQUIRED !!!")
        self.logger.logln(msg)
        self.logger.logln("Press enter to continue...")
        self.logger.logln()
        raw_input()

    # Run the equipment for the test
    def run_test(self):
        # Compute the sweep parameters
        for i in range(len(self.profile.sweep_f_divisions)):
            for j in range(len(self.profile.sweep_f_divisions[i])):
                self.profile.sweep_f_extra.append(self.profile.sweep_f_divisions[i][j])
        self.compute_swept_power_sweep_parameters()

        # Measure noise powers if required
        if self.profile.test_measure_noise_figure:
            # Pause for the user to terminate the SDR if needed
            if self.profile.noise_figure_terminating:
                self.pause_for_user_action("Please terminate the SDR input")
            
            # Run the noise power measurements for each SR/CF pair
            self.logger.logln("Measuring noise powers...")
            self.logger.stepin()
            self.noise_powers = []
            for k in range(len(self.profile.test_sample_rates)):

                self.logger.flush()
                self.logger.logln("Using sample rate: {}".format(
                    self.logger.to_MHz(self.profile.test_sample_rates[k]))
                )
                self.logger.logln("Using clock frequency: {}".format(
                    self.logger.to_MHz(self.profile.test_clock_frequencies[k]))
                )
                self.logger.stepin()

                # Set SDR sample rate and clock frequency
                self.logger.log("Setting SDR clock frequency to {}... ".format(
                    self.logger.to_MHz(self.profile.test_clock_frequencies[k])))
                self.sdr.set_clock_frequency(self.profile.test_clock_frequencies[k])
                self.logger.logln("Done!")
                self.logger.log("Setting SDR sample rate to {}... ".format(
                    self.logger.to_MHz(self.profile.test_sample_rates[k])))
                self.sdr.set_sampling_frequency(self.profile.test_sample_rates[k])
                self.logger.logln("Done!")
                time.sleep(1)

                # Run the noise power measurements
                self.dependency_test_profile_adjustments = {
                    'test_check_for_compression': False,
                    'test_measure_spur_power': False,
                    'sweep_p_min': None,
                    'sweep_p_max': None,
                    'sweep_p_num_steps': False,
                    'sweep_p_lin_spacing': False,
                    'sweep_p_log_steps': False,
                    'sweep_p_extra': [self.profile.noise_figure_input_power],
                    'sweep_order_1st': 'frequency',
                    'sweep_order_2nd': 'gain',
                    'sweep_order_3rd': 'power',
                    'power_stimulus': 'single_cw'
                }
                self.run_dependency_test(
                    self.swept_power_measurement,
                    self.dependency_test_profile_adjustments
                )
                self.logger.stepout()

                # Recover the noise levels
                self.logger.log("Recovering noise power levels... ")
                r = self.swept_power_measurement
                self.noise_powers.append(
                        r.time_domain_averaged_powers
                    )
                self.logger.logln("Done!")
            
            self.logger.stepout()
            self.logger.logln("Finished measuring noise powers!")
        
            # Pause for the user to connect the siggen if needed
            if self.profile.noise_figure_terminating:
                self.pause_for_user_action("Please connect the signal generator to the SDR")
            
            # Flush the logger
            self.logger.flush()
        
        # Measure scale factors if required
        if self.profile.test_measure_scale_factor:
            self.logger.logln("Measuring Scale factors...")
            self.logger.stepin()
            self.scale_factors = []
            for k in range(len(self.profile.test_sample_rates)):

                self.logger.flush()
                self.logger.logln("Using sample rate: {}".format(
                    self.logger.to_MHz(self.profile.test_sample_rates[k]))
                )
                self.logger.logln("Using clock frequency: {}".format(
                    self.logger.to_MHz(self.profile.test_clock_frequencies[k]))
                )
                self.logger.stepin()

                # Set SDR sample rate and clock frequency
                self.logger.log("Setting SDR clock frequency to {}... ".format(
                    self.logger.to_MHz(self.profile.test_clock_frequencies[k])))
                self.sdr.set_clock_frequency(self.profile.test_clock_frequencies[k])
                self.logger.logln("Done!")
                self.logger.log("Setting SDR sample rate to {}... ".format(
                    self.logger.to_MHz(self.profile.test_sample_rates[k])))
                self.sdr.set_sampling_frequency(self.profile.test_sample_rates[k])
                self.logger.logln("Done!")
                time.sleep(1)

                # Run the scale factor measurements
                self.dependency_test_profile_adjustments = {
                    'sweep_p_extra': [self.profile.scale_factor_power_level],
                    'test_power_measurement_method': "{}s".format(self.profile.scale_factor_measurement_method),
                    'test_find_divisions': False,
                    'sweep_order_1st': 'power',
                    'sweep_order_2nd': 'gain',
                    'sweep_order_3rd': 'frequency',
                }
                self.run_dependency_test(
                    self.scale_factor,
                    self.dependency_test_profile_adjustments
                )
                self.logger.stepout()

                # Recover the scale factors
                self.logger.log("Recovering scale factors... ")
                r = self.scale_factor
                self.scale_factors.append(
                        r.sfs
                    )
                self.logger.logln("Done!")

                if self.profile.test_measure_noise_figure:
                    self.logger.log("Applying scale factor to noise powers... ")
                    for i in range(len(self.sweep_list_1)):
                        for j in range(len(self.sweep_list_2)):
                            self.noise_powers[k][i][j][0] = self.noise_powers[k][i][j][0] + self.scale_factors[k][i][j]
                    self.logger.logln("Done!")
                self.logger.flush()
            
            # Convert the scale factors to empirical gains
            self.logger.log("Converting scale factors to empirical gains... ")
            self.scale_factors = np.asarray(self.scale_factors)
            self.empirical_gains = -1*self.scale_factors
            self.logger.logln("Done!")
            
            self.logger.stepout()
            self.logger.logln("Finished measuring scale factors!")
        
        # Measure ENBWs if required
        if self.profile.test_measure_enbws:
            self.logger.logln("Measuring equivalent noise bandwidths...")
            self.logger.stepin()
            self.measured_enbws = []

            # Remind log of gain/frequency settings and set the gain
            self.logger.logln("Using these settings for enbw measurements...")
            self.logger.stepin()
            self.logger.logln("Center frequency: {}".format(self.logger.to_MHz(self.profile.enbw_frequency)))
            self.logger.logln("SDR gain: {}".format(self.logger.to_dBm(self.profile.enbw_gain)))
            self.set_sdr_gain(self.profile.enbw_gain)
            self.logger.stepout()

            # Run test at each sample rate
            for k in range(len(self.profile.test_sample_rates)):

                self.logger.flush()
                self.logger.logln("Using sample rate: {}".format(
                    self.logger.to_MHz(self.profile.test_sample_rates[k]))
                )
                self.logger.logln("Using clock frequency: {}".format(
                    self.logger.to_MHz(self.profile.test_clock_frequencies[k]))
                )
                self.logger.stepin()

                # Set SDR sample rate and clock frequency
                self.logger.log("Setting SDR clock frequency to {}... ".format(
                    self.logger.to_MHz(self.profile.test_clock_frequencies[k])))
                self.sdr.set_clock_frequency(self.profile.test_clock_frequencies[k])
                self.logger.logln("Done!")
                self.logger.log("Setting SDR sample rate to {}... ".format(
                    self.logger.to_MHz(self.profile.test_sample_rates[k])))
                self.sdr.set_sampling_frequency(self.profile.test_sample_rates[k])
                self.logger.logln("Done!")
                time.sleep(1)

                # Run the bandwidth measurements
                self.dependency_test_profile_adjustments = {
                    'freq_offset_f0_and_cw': False,
                    'power_level': self.profile.enbw_power_level,
                    'freq_f0': self.profile.enbw_frequency,
                    'sdr_gain': self.profile.enbw_gain,
                    'test_bandwidth_to_measure': self.profile.enbw_measurement_band_stretch * self.profile.test_sample_rates[k],
                    'test_bandwidth_steps': self.profile.enbw_transfer_function_points
                }
                self.run_dependency_test(
                    self.bandwidth,
                    self.dependency_test_profile_adjustments
                )
                self.logger.stepout()

                # Recover the scale factors
                self.logger.log("Recovering bandwidths... ")
                r = self.bandwidth
                self.measured_enbws.append(
                        r.equivalent_noise_bandwidth
                    )
                self.logger.logln("Done!")
            
            self.logger.stepout()
            self.logger.logln("Finished measuring ENBWs!")
        
        # Run the compression test
        if self.profile.test_measure_compression:
            self.logger.logln("Measuring compression levels...")
            self.logger.stepin()
            self.compression_levels = []

            # Calculate the frequency decimating parameters
            self.logger.log("Calculating frequency decimation parameters... ")
            compression_test_sweep_f_num_steps = self.profile.sweep_f_num_steps
            if compression_test_sweep_f_num_steps:
                compression_test_sweep_f_num_steps = round(compression_test_sweep_f_num_steps / self.profile.compression_decimate_frequencies)
                if compression_test_sweep_f_num_steps < 2:
                    compression_test_sweep_f_num_steps = 2
            compression_test_sweep_f_lin_spacing = self.profile.sweep_f_lin_spacing
            if compression_test_sweep_f_lin_spacing:
                compression_test_sweep_f_lin_spacing = compression_test_sweep_f_lin_spacing * self.profile.compression_decimate_frequencies
            compression_test_sweep_f_log_steps = self.profile.sweep_f_log_steps
            if compression_test_sweep_f_log_steps:
                compression_test_sweep_f_log_steps = round(compression_test_sweep_f_log_steps / self.profile.compression_decimate_frequencies)
                if compression_test_sweep_f_log_steps < 2:
                    compression_test_sweep_f_log_steps = 2
            self.logger.logln("Done!")

            # Calculate the gain decimating parameters
            self.logger.log("Calculating gain decimation parameters... ")
            compression_test_sweep_g_num_steps = self.profile.sweep_g_num_steps
            if compression_test_sweep_g_num_steps:
                compression_test_sweep_g_num_steps = round(compression_test_sweep_g_num_steps / self.profile.compression_decimate_gains)
                if compression_test_sweep_g_num_steps < 2:
                    compression_test_sweep_g_num_steps = 2
            compression_test_sweep_g_lin_spacing = self.profile.sweep_g_lin_spacing
            if compression_test_sweep_g_lin_spacing:
                compression_test_sweep_g_lin_spacing = compression_test_sweep_g_lin_spacing * self.profile.compression_decimate_gains
            compression_test_sweep_g_log_steps = self.profile.sweep_g_log_steps
            if compression_test_sweep_g_log_steps:
                compression_test_sweep_g_log_steps = round(compression_test_sweep_g_log_steps / self.profile.compression_decimate_gains)
                if compression_test_sweep_g_log_steps < 2:
                    compression_test_sweep_g_log_steps = 2
            self.logger.logln("Done!")

            # Run the compression tests at all the sample rates
            for k in range(len(self.profile.test_sample_rates)):

                self.logger.flush()
                self.logger.logln("Using sample rate: {}".format(
                    self.logger.to_MHz(self.profile.test_sample_rates[k]))
                )
                self.logger.logln("Using clock frequency: {}".format(
                    self.logger.to_MHz(self.profile.test_clock_frequencies[k]))
                )
                self.logger.stepin()

                # Set SDR sample rate and clock frequency
                self.logger.log("Setting SDR clock frequency to {}... ".format(
                    self.logger.to_MHz(self.profile.test_clock_frequencies[k])))
                self.sdr.set_clock_frequency(self.profile.test_clock_frequencies[k])
                self.logger.logln("Done!")
                self.logger.log("Setting SDR sample rate to {}... ".format(
                    self.logger.to_MHz(self.profile.test_sample_rates[k])))
                self.sdr.set_sampling_frequency(self.profile.test_sample_rates[k])
                self.logger.logln("Done!")
                time.sleep(1)

                # Run the compression measurements
                self.dependency_test_profile_adjustments = {
                    'test_check_for_compression': True,
                    'sweep_order_1st': 'frequency',
                    'sweep_order_2nd': 'gain',
                    'sweep_order_3rd': 'power',
                    'sweep_f_num_steps': compression_test_sweep_f_num_steps,
                    'sweep_f_lin_spacing': compression_test_sweep_f_lin_spacing,
                    'sweep_f_log_steps': compression_test_sweep_f_log_steps,
                    'sweep_g_num_steps': compression_test_sweep_g_num_steps,
                    'sweep_g_lin_spacing': compression_test_sweep_g_lin_spacing,
                    'sweep_g_log_steps': compression_test_sweep_g_log_steps,
                    'sweep_p_min': self.profile.compression_min_power,
                    'sweep_p_max': self.profile.compression_max_power,
                    'sweep_p_num_steps': False,
                    'sweep_p_lin_spacing': self.profile.compression_power_step,
                    'sweep_p_log_steps': False,
                    'sweep_p_extra': [],
                    'sweep_p_order': 'asc',
                    'test_compression_measurement_method': self.profile.compression_measurement_method,
                    'test_compression_threshold': self.profile.compression_threshold,
                    'test_compression_linearity_steps': self.profile.compression_linearity_steps,
                    'test_compression_linearity_threshold': self.profile.compression_linearity_threshold
                }
                self.run_dependency_test(
                    self.swept_power_measurement,
                    self.dependency_test_profile_adjustments
                )
                self.logger.stepout()

                # Recover the compression points
                self.logger.log("Recovering compression levels... ")
                r = self.swept_power_measurement
                self.decimated_compression_levels = r.compression_powers
                self.compression_sweep_list_1 = r.sweep_list_1  # Compression frequencies
                self.compression_sweep_list_2 = r.sweep_list_2  # Compression gains
                self.logger.logln("Done!")
                print(self.compression_sweep_list_1)
                print(self.sweep_list_1)
                print(self.compression_sweep_list_2)
                print(self.sweep_list_2)

                # Reinterpolate the decimation
                """
                self.logger.log("Reinterpolating compression levels... ")
                self.compression_levels.append([])
                current_compression_f_i = 0
                for i in range(len(self.sweep_list_1)): #Frequency
                    # Check if the frequency matches and skip interpolation (add whole gain row)
                    if self.sweep_list_1[i] == self.compression_sweep_list_1[current_compression_f_i]: #Only likely to catch end points and division freqs
                        self.compression_levels[k].append(self.decimated_compression_levels[current_compression_f_i])
                        current_compression_f_i += 1
                        continue
                    
                    # Check if the needed frequency is greater than last indexed frequency
                    if self.sweep_list_1[i] > self.compression_sweep_list_1[current_compression_f_i]:
                        current_compression_f_i += 1
                    
                    # Interpolate for the entire gain column
                    self.compression_levels[k].append([])
                    for j in range(len(self.sweep_list_2)): #Gain
                        self.compression_levels[k][i].append(
                            utils.interpolate_1d(
                                self.sweep_list_1[i],
                                self.compression_sweep_list_1[current_compression_f_i-1],
                                self.compression_sweep_list_1[current_compression_f_i],
                                self.decimated_compression_levels[current_compression_f_i-1][j],
                                self.decimated_compression_levels[current_compression_f_i][j]
                            )
                        )
                self.logger.logln("Done!")
                """

                # Dummy compression levels
                #for i in range(len(self.decimated_compression_levels)):
                #    for j in range(len(self.decimated_compression_levels[i])):
                #        self.decimated_compression_levels[i][j] = 3*i + 2*j - 5
                #print(json.dumps(self.decimated_compression_levels, indent=4))

                # Reinterpolate the decimation
                self.logger.log("Reinterpolating compression levels... ")
                self.compression_levels.append([])  # Add the sample rate row
                current_compression_f_i = 0
                for i in range(len(self.sweep_list_1)): #Frequency
                    # Add the frequency row
                    self.compression_levels[k].append([])

                    # Check if the frequency matches and skip interpolation (add whole gain row)
                    #if self.sweep_list_1[i] == self.compression_sweep_list_1[current_compression_f_i]: #Only likely to catch end points and division freqs
                    #    self.compression_levels[k].append(self.decimated_compression_levels[current_compression_f_i])
                    #    current_compression_f_i += 1
                    #    continue
                    
                    # Check if the needed frequency is greater than last indexed frequency
                    if self.sweep_list_1[i] > self.compression_sweep_list_1[current_compression_f_i+1]:
                        current_compression_f_i += 1
                    
                    # Interpolate for each gain
                    current_compression_g_i = 0
                    for j in range(len(self.sweep_list_2)): #Gain
                    
                        # Check if the needed frequency is greater than last indexed frequency
                        if self.sweep_list_2[j] > self.compression_sweep_list_2[current_compression_g_i+1]:
                            current_compression_g_i += 1
                        
                        #print("")
                        #print("i:({},{},{})".format(current_compression_f_i,i,current_compression_f_i+1))
                        #print("F:({},{},{})".format(self.compression_sweep_list_1[current_compression_f_i],self.sweep_list_1[i],self.compression_sweep_list_1[current_compression_f_i+1]))
                        #print("j:({},{},{})".format(current_compression_g_i,j,current_compression_g_i+1))
                        #print("G:({},{},{})".format(self.compression_sweep_list_2[current_compression_g_i],self.sweep_list_2[j],self.compression_sweep_list_2[current_compression_g_i+1]))
                        #print("")

                        self.compression_levels[k][i].append(
                            utils.interpolate_2d(  # interpolate_2d(x,y,x1,x2,y1,y2,z11,z21,z12,z22)
                                self.sweep_list_1[i],
                                self.sweep_list_2[j],
                                self.compression_sweep_list_1[current_compression_f_i],
                                self.compression_sweep_list_1[current_compression_f_i+1],
                                self.compression_sweep_list_2[current_compression_g_i],
                                self.compression_sweep_list_2[current_compression_g_i+1],
                                self.decimated_compression_levels[current_compression_f_i+0][current_compression_g_i+0],
                                self.decimated_compression_levels[current_compression_f_i+1][current_compression_g_i+0],
                                self.decimated_compression_levels[current_compression_f_i+0][current_compression_g_i+1],
                                self.decimated_compression_levels[current_compression_f_i+1][current_compression_g_i+1]
                            )
                        )
                self.logger.logln("Done!")

                # If skipping the sampling/clock frequency cycling, break out
                if self.profile.compression_skip_sample_rate_cycling:
                    self.logger.logln("Skipping other sample frequency/clock rate pairs...")
                    self.logger.flush()
                    break
                self.logger.flush()
            
            self.logger.stepout()
            self.logger.logln("Finished measuring compression levels!")

        # Convert noise powers to noise figures if they are being measured
        if self.profile.test_measure_noise_figure:
            self.logger.log("Converting noise powers to noise figures... ")
            kB = 1.3806e-23
            T  = 300
            self.noise_figures = []
            if not self.profile.test_measure_enbws:
                self.measured_enbws = self.profile.noise_figure_enbws
            for k in range(len(self.profile.test_sample_rates)):
                self.noise_figures.append([])
                for i in range(len(self.sweep_list_1)):
                    self.noise_figures[k].append([])
                    for j in range(len(self.sweep_list_2)):
                        enbw = self.measured_enbws[k]
                        ideal_thermal_noise = 10*np.log10(kB*T*enbw) + 30
                        self.noise_figures[k][i].append(self.noise_powers[k][i][j][0] - ideal_thermal_noise)
            self.logger.logln("Done!")

    # Save data or construct plot if required
    def save_data(self):
        # Save the test summary if requested
        if self.profile.logging_save_test_summary:
            self.logger.log("Writing test data to file... ")
            if self.profile.test_measure_enbws:
                fname = "enbw_summary.csv"
                with open(self.save_file(fname), 'w+') as file:
                    file.write("sample_rate,clock_freq,ENBW\r\n")
                    for k in range(len(self.profile.test_sample_rates)):
                        file.write("{},{},{}\r\n".format(
                            self.logger.to_MHz(self.profile.test_sample_rates[k]),
                            self.logger.to_MHz(self.profile.test_clock_frequencies[k]),
                            self.logger.to_MHz(self.measured_enbws[k]),
                        ))
            for k in range(len(self.profile.test_sample_rates)):
                sr = self.profile.test_sample_rates[k]
                cf = self.profile.test_clock_frequencies[k]
                if self.profile.test_measure_compression:
                    fname = "compression_summary_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.sweep_list_2)):
                            file.write(",{}".format(self.sweep_list_2[j]))
                        file.write("\r\n")
                        for i in range(len(self.sweep_list_1)):
                            file.write("{}".format(self.sweep_list_1[i]))
                            for j in range(len(self.sweep_list_2)):
                                if self.profile.compression_skip_sample_rate_cycling:
                                    file.write(",{}".format(self.compression_levels[0][i][j]))
                                else:
                                    file.write(",{}".format(self.compression_levels[k][i][j]))
                            file.write("\r\n")
                        file.close()
                if self.profile.test_measure_scale_factor:
                    fname = "scale_factors_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.sweep_list_2)):
                            file.write(",{}".format(self.sweep_list_2[j]))
                        file.write("\r\n")
                        for i in range(len(self.sweep_list_1)):
                            file.write("{}".format(self.sweep_list_1[i]))
                            for j in range(len(self.sweep_list_2)):
                                file.write(",{}".format(self.scale_factors[k][i][j]))
                            file.write("\r\n")
                        file.close()
                if self.profile.test_measure_noise_figure:
                    fname = "noise_powers_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.sweep_list_2)):
                            file.write(",{}".format(self.sweep_list_2[j]))
                        file.write("\r\n")
                        for i in range(len(self.sweep_list_1)):
                            file.write("{}".format(self.sweep_list_1[i]))
                            for j in range(len(self.sweep_list_2)):
                                file.write(",{}".format(self.noise_powers[k][i][j][0]))
                            file.write("\r\n")
                        file.close()
                    fname = "noise_figures_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.sweep_list_2)):
                            file.write(",{}".format(self.sweep_list_2[j]))
                        file.write("\r\n")
                        for i in range(len(self.sweep_list_1)):
                            file.write("{}".format(self.sweep_list_1[i]))
                            for j in range(len(self.sweep_list_2)):
                                file.write(",{}".format(self.noise_figures[k][i][j]))
                            file.write("\r\n")
                        file.close()
            cal_data_json = {}
            cal_data_json['sensor_uid'] = self.sdr_serial_number
            cal_data_json['calibration_datetime'] = "{}Z".format(datetime.datetime.utcnow().isoformat())
            cal_data_json['calibration_frequency_divisions'] = []
            for i in range(len(self.profile.sweep_f_divisions)):
                cal_data_json['calibration_frequency_divisions'].append({
                    'lower_bound': self.profile.sweep_f_divisions[i][0],
                    'upper_bound': self.profile.sweep_f_divisions[i][1]
                })
            cal_data_json['clock_rate_lookup_by_sample_rate'] = []
            for i in range(len(self.profile.test_sample_rates)):
                cal_data_json['clock_rate_lookup_by_sample_rate'].append({
                    "sample_rate": self.profile.test_sample_rates[i],
                    "clock_frequency": self.profile.test_clock_frequencies[i]
                })
            """cal_data_json['calibration_points'] = []
            for k in range(len(self.profile.test_sample_rates)):
                for i in range(len(self.sweep_list_1)):
                    for j in range(len(self.sweep_list_2)):
                        cal_data_point = {
                            'freq_sigan': self.sweep_list_1[i],
                            'gain_sigan': self.sweep_list_2[j],
                            'sample_rate_sigan': self.profile.test_sample_rates[k]
                        }
                        if self.profile.test_measure_compression:
                            if self.profile.compression_skip_sample_rate_cycling:
                                cal_data_point['1dB_compression'] = self.compression_levels[0][i][j]
                            else:
                                cal_data_point['1dB_compression'] = self.compression_levels[k][i][j]
                        if self.profile.test_measure_scale_factor:
                            cal_data_point['scale_factor'] = self.scale_factors[k][i][j]
                            cal_data_point['empirical_gain'] = self.empirical_gains[k][i][j]
                        if self.profile.test_measure_noise_figure:
                            cal_data_point['noise_figure'] = self.noise_figures[k][i][j]
                        if self.profile.test_measure_enbws:
                            cal_data_point['equivalent_noise_bw'] = self.measured_enbws[k]
                        cal_data_json['calibration_points'].append(cal_data_point)"""
            # Create the JSON architecture
            cal_data_json['calibration_data'] = {}
            cal_data_json['calibration_data']['sample_rates'] = []
            for k in range(len(self.profile.test_sample_rates)):
                cal_data_json_sr = {}
                cal_data_json_sr['sample_rate'] = self.profile.test_sample_rates[k]
                cal_data_json_sr['calibration_data'] = {}
                cal_data_json_sr['calibration_data']['frequencies'] = []
                for i in range(len(self.sweep_list_1)):
                    cal_data_json_f = {}
                    cal_data_json_f['frequency'] = self.sweep_list_1[i]
                    cal_data_json_f['calibration_data'] = {}
                    cal_data_json_f['calibration_data']['gains'] = []
                    for j in range(len(self.sweep_list_2)):
                        cal_data_json_g = {}
                        cal_data_json_g['gain'] = self.sweep_list_2[j]
                        
                        # Add the calibration data
                        cal_data_point = {}
                        if self.profile.test_measure_compression:
                            if self.profile.compression_skip_sample_rate_cycling:
                                cal_data_point['1dB_compression_sigan'] = self.compression_levels[0][i][j]
                            else:
                                cal_data_point['1dB_compression_sigan'] = self.compression_levels[k][i][j]
                        if self.profile.test_measure_scale_factor:
                            cal_data_point['gain_sigan'] = self.empirical_gains[k][i][j]
                        if self.profile.test_measure_noise_figure:
                            cal_data_point['noise_figure_sigan'] = self.noise_figures[k][i][j]
                        if self.profile.test_measure_enbws:
                            cal_data_point['enbw_sigan'] = self.measured_enbws[k]

                        # Add the generated dicts to the parent lists
                        cal_data_json_g['calibration_data'] = deepcopy(cal_data_point)
                        cal_data_json_f['calibration_data']['gains'].append(deepcopy(cal_data_json_g))
                    cal_data_json_sr['calibration_data']['frequencies'].append(deepcopy(cal_data_json_f))
                cal_data_json['calibration_data']['sample_rates'].append(deepcopy(cal_data_json_sr))
            self.write_calibration_file("calibration_file.json", src_file=None, json_dict=cal_data_json)
            self.logger.logln("Done!")
            

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
