import numpy as np
from matplotlib import pyplot as plt
from copy import copy, deepcopy
import datetime, json
import os

import sdrcalibrator.lib.utils.common as utils
from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "SCOS Calibrate"

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [
                'calibrate'
            ],
            'required_profile_parameters': [
                'cal_sdr_measure_scale_factor',
                'cal_sdr_measure_enbws',
                'cal_sdr_measure_noise_figure',
                'cal_sdr_measure_compression',
                'cal_sdr_measure_spur_free',
                'cal_scos_measure_scale_factor',
                'cal_scos_measure_enbws',
                'cal_scos_measure_noise_figure',
                'cal_scos_measure_compression',
                'cal_scos_measure_spur_free',
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
                'cal_sdr_additional_calibration_fields': {},
                'cal_sdr_noise_figure_terminating': False,
                'cal_sdr_noise_figure_input_power': -200,
                'cal_sdr_compression_skip_sample_rate_cycling': False,
                'cal_sdr_compression_decimate_frequencies': False,
                'cal_sdr_enbw_measurement_band_stretch': 1.5,
                'cal_sdr_enbw_transfer_function_points': 150,
                'cal_scos_additional_calibration_fields': {},
                'cal_scos_noise_figure_terminating': False,
                'cal_scos_noise_figure_input_power': -200,
                'cal_scos_compression_skip_sample_rate_cycling': False,
                'cal_scos_compression_decimate_frequencies': False,
                'cal_scos_enbw_measurement_band_stretch': 1.5,
                'cal_scos_enbw_transfer_function_points': 150
            },
            'forced_profile_parameters': {
                'freq_f0': False,
                'power_stimulus': 'single_cw',
                'power_level': -200,
                'sdr_power_scale_factor': 0,
                'sdr_power_scale_factor_file': False,
                'sweep_f_order': 'asc',
                'sweep_g_order': 'asc',
                'sweep_order_1st': 'frequency',
                'sweep_order_2nd': 'gain',
                'sweep_order_3rd': 'power',
                'test_bandwidth_to_measure': False,
                'test_bandwidth_steps': False,
                'test_measure_scale_factor': False,
                'test_measure_enbws': False,
                'test_measure_noise_figure': False,
                'test_measure_compression': False,
                'test_measure_spur_free': False,
                'cal_sdr_measure_spur_free': False, # This is not implemented yet
                'cal_scos_measure_spur_free': False, # This is not implemented yet
                'cal_scos_measure_compression': False # Assuming simple attenuation, just scales
            }
        }
        super(SDR_Test, self).__init__(profile, logger)

    # Check the profile
    def check_profile(self):
        # Add profile definitions based on whether scale factors are measured
        if self.profile.cal_sdr_measure_scale_factor:
            self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                'cal_sdr_scale_factor_power_level',
                'cal_sdr_scale_factor_measurement_method'
            ])
        if self.profile.cal_scos_measure_scale_factor:
            self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                'cal_scos_scale_factor_power_level',
                'cal_scos_scale_factor_measurement_method'
            ])
        
        # Add profile definitions based on whether enbws are measured
        if self.profile.cal_sdr_measure_enbws:
            self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                'cal_sdr_enbw_frequency',
                'cal_sdr_enbw_gain',
                'cal_sdr_enbw_power_level'
            ])
        if self.profile.cal_scos_measure_enbws:
            self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                'cal_scos_enbw_frequency',
                'cal_scos_enbw_gain',
                'cal_scos_enbw_power_level'
            ])
        
        # Save freq_offset_f0_and_cw because the bandwidth test will overwrite
        saved_freq_offset_f0_and_cw = self.profile.freq_offset_f0_and_cw
        
        # Add profile definitions based on whether noise figures are measured
        if self.profile.cal_sdr_measure_noise_figure:
            # If not measuring enbws, make sure they are provided noise_figure_enbws
            if not self.profile.cal_sdr_measure_enbws:
                self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                    'cal_sdr_noise_figure_enbws'
                ])
        if self.profile.cal_scos_measure_noise_figure:
            # If not measuring enbws, make sure they are provided noise_figure_enbws
            if not self.profile.cal_scos_measure_enbws:
                self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                    'cal_scos_noise_figure_enbws'
                ])
        
        # Add profile definitions based on whether compressions are measured
        if self.profile.cal_sdr_measure_compression:
            self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                'cal_sdr_compression_min_power',
                'cal_sdr_compression_max_power',
                'cal_sdr_compression_power_step',
                'cal_sdr_compression_measurement_method',
                'cal_sdr_compression_threshold',
                'cal_sdr_compression_linearity_steps',
                'cal_sdr_compression_linearity_threshold'
            ])
        if self.profile.cal_scos_measure_compression:
            self.TEST_PROFILE_DEFINITIONS['required_profile_parameters'].extend([
                'cal_scos_compression_min_power',
                'cal_scos_compression_max_power',
                'cal_scos_compression_power_step',
                'cal_scos_compression_measurement_method',
                'cal_scos_compression_threshold',
                'cal_scos_compression_linearity_steps',
                'cal_scos_compression_linearity_threshold'
            ])
        
        # Add profile definitions based on whether enbws are measured (NOT IMPLEMENTED YET)
        self.profile.cal_sdr_measure_spur_free = False
        if self.profile.cal_sdr_measure_spur_free:
            pass
        self.profile.cal_scos_measure_spur_free = False
        if self.profile.cal_scos_measure_spur_free:
            pass
        
        # Merge and profile definition changes
        self.merge_profile_definitions()

        # Ensure the profile matches the definitions
        super(SDR_Test, self).check_profile()

        # Fix the sweep order after the scale factor test breaks it
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
        if self.profile.cal_sdr_measure_noise_figure and not self.profile.cal_sdr_measure_enbws:
            if not len(self.profile.test_sample_rates) == len(self.profile.cal_sdr_noise_figure_enbws):
                ehead = 'Sample rate and equivalent noise bandwidth mismatch'
                ebody = (
                    "The number of sample rates and equivalent noise bandwidths must be the same for calibrating the sdr:\r\n" +
                    "    Sample rates: {}\r\n" +
                    "    SDR EQNBs:    {}"
                ).format(
                    self.profile.test_sample_rates,
                    self.profile.cal_sdr_noise_figure_enbws
                )
                err = SDR_Test_Error(10, ehead, ebody)
                Error.error_out(self.logger, err)
        if self.profile.cal_scos_measure_noise_figure and not self.profile.cal_scos_measure_enbws:
            if not len(self.profile.test_sample_rates) == len(self.profile.cal_scos_noise_figure_enbws):
                ehead = 'Sample rate and equivalent noise bandwidth mismatch'
                ebody = (
                    "The number of sample rates and equivalent noise bandwidths must be the same for calibrating the SCOS:\r\n" +
                    "    Sample rates: {}\r\n" +
                    "    SCOS EQNBs:   {}"
                ).format(
                    self.profile.test_sample_rates,
                    self.profile.cal_scos_noise_figure_enbws
                )
                err = SDR_Test_Error(10, ehead, ebody)
                Error.error_out(self.logger, err)
        
        # If not decimating frequencies, set decimation rate to 1
        if not self.profile.cal_sdr_compression_decimate_frequencies:
            self.profile.cal_sdr_compression_decimate_frequencies = 1
        if not self.profile.cal_scos_compression_decimate_frequencies:
            self.profile.cal_scos_compression_decimate_frequencies = 1
        
        # Check enbw parameters if running test
        if self.profile.cal_sdr_measure_enbws:
            # Make sure the ENBW stretch ratio is greater than 1 
            if self.profile.cal_sdr_enbw_measurement_band_stretch <= 1:
                ehead = 'ENBW stretch ratio must be greater than 1'
                ebody = (
                    "To accurately measure the equivalent noise bandwidth for the sdr, the measured band\r\n" +
                    "must be greater than the sample rate (enbw_measurement_band_stretch > 1):\r\n"
                    "    Requested cal_sdr_enbw_measurement_band_stretch: {}"
                ).format(
                    self.profile.cal_sdr_enbw_measurement_band_stretch
                )
                err = SDR_Test_Error(10, ehead, ebody)
                Error.error_out(self.logger, err)
        if self.profile.cal_scos_measure_enbws:
            # Make sure the ENBW stretch ratio is greater than 1 
            if self.profile.cal_scos_enbw_measurement_band_stretch <= 1:
                ehead = 'ENBW stretch ratio must be greater than 1'
                ebody = (
                    "To accurately measure the equivalent noise bandwidth for the scos, the measured band\r\n" +
                    "must be greater than the sample rate (enbw_measurement_band_stretch > 1):\r\n"
                    "    Requested cal_scos_enbw_measurement_band_stretch: {}"
                ).format(
                    self.profile.cal_scos_enbw_measurement_band_stretch
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
        if utils.is_python3():
            input()
        else:
            raw_input()

    # Run the equipment for the test
    def run_test(self):
        # Construct data dict
        self.test_calibration_data = {}
        self.test_calibration_data['sdr'] =       {}
        self.test_calibration_data['front_end'] = {}
        self.test_calibration_data['scos'] =      {}

        # Ask the user to connect the entire scos sensor
        self.pause_for_user_action("Please connect the entire SCOS sensor as the DUT")
        self.logger.logln("Running calibration on SCOS sensor...")
        self.logger.stepin()

        # Run the calibration on the entire SCOS sensor
        self.dependency_test_profile_adjustments = {
            'test_measure_scale_factor': self.profile.cal_scos_measure_scale_factor,
            'test_measure_enbws':        self.profile.cal_scos_measure_enbws,
            'test_measure_noise_figure': self.profile.cal_scos_measure_noise_figure,
            'test_measure_compression':  self.profile.cal_scos_measure_compression,
            'test_measure_spur_free':    self.profile.cal_scos_measure_spur_free,

            'sweep_f_min':         self.profile.cal_scos_sweep_f_min,
            'sweep_f_max':         self.profile.cal_scos_sweep_f_max,
            'sweep_f_num_steps':   self.profile.cal_scos_sweep_f_num_steps,
            'sweep_f_lin_spacing': self.profile.cal_scos_sweep_f_lin_spacing,
            'sweep_f_log_steps':   self.profile.cal_scos_sweep_f_log_steps,
            'sweep_f_extra':       self.profile.cal_scos_sweep_f_extra,
            'sweep_f_divisions':   self.profile.cal_scos_sweep_f_divisions,
            'sweep_g_min':         self.profile.cal_scos_sweep_g_min,
            'sweep_g_max':         self.profile.cal_scos_sweep_g_max,
            'sweep_g_num_steps':   self.profile.cal_scos_sweep_g_num_steps,
            'sweep_g_lin_spacing': self.profile.cal_scos_sweep_g_lin_spacing,
            'sweep_g_log_steps':   self.profile.cal_scos_sweep_g_log_steps,
            'sweep_g_extra':       self.profile.cal_scos_sweep_g_extra,
            
            'scale_factor_power_level':        self.profile.cal_scos_scale_factor_power_level,
            'scale_factor_measurement_method': self.profile.cal_scos_scale_factor_measurement_method,

            'enbw_frequency':                self.profile.cal_scos_enbw_frequency,
            'enbw_gain':                     self.profile.cal_scos_enbw_gain,
            'enbw_power_level':              self.profile.cal_scos_enbw_power_level,
            'enbw_measurement_band_stretch': self.profile.cal_scos_enbw_measurement_band_stretch,
            'enbw_transfer_function_points': self.profile.cal_scos_enbw_transfer_function_points,


            'noise_figure_enbws':       self.profile.cal_scos_noise_figure_enbws,
            'noise_figure_terminating': self.profile.cal_scos_noise_figure_terminating,
            'noise_figure_input_power': self.profile.cal_scos_noise_figure_input_power,
            
            'compression_skip_sample_rate_cycling': self.profile.cal_scos_compression_skip_sample_rate_cycling,
            'compression_decimate_frequencies':     self.profile.cal_scos_compression_decimate_frequencies,
            'compression_min_power':                self.profile.cal_scos_compression_min_power,
            'compression_max_power':                self.profile.cal_scos_compression_max_power,
            'compression_power_step':               self.profile.cal_scos_compression_power_step,
            'compression_measurement_method':       self.profile.cal_scos_compression_measurement_method,
            'compression_threshold':                self.profile.cal_scos_compression_threshold,
            'compression_linearity_steps':          self.profile.cal_scos_compression_linearity_steps,
            'compression_linearity_threshold':      self.profile.cal_scos_compression_linearity_threshold,

            'spur_free_measurement_remove_ranges': self.profile.cal_scos_spur_free_measurement_remove_ranges,
            'spur_free_danl_num':                  self.profile.cal_scos_spur_free_danl_num,
            'spur_free_threshold':                 self.profile.cal_scos_spur_free_threshold
        }
        subtest_save_directory = "{}/scos_calibration".format(self.save_directory)
        self.run_dependency_test(
            self.calibrate,
            self.dependency_test_profile_adjustments#,
            #run_save_function=True,
            #save_directory=subtest_save_directory
        )
        self.logger.stepout()
        self.logger.logln("Finished calibrating SCOS sensor!")

        # Recover the data from the test
        self.logger.log("Recovering calibration data... ")
        r = self.calibrate
        self.test_calibration_data['scos']['fs'] = deepcopy(r.sweep_list_1)
        self.test_calibration_data['scos']['gs'] = deepcopy(r.sweep_list_2)
        if self.profile.cal_scos_measure_scale_factor:
            self.test_calibration_data['scos']['scale_factors'] = deepcopy(r.scale_factors)
            self.test_calibration_data['scos']['empirical_gains'] = deepcopy(r.empirical_gains)
        if self.profile.cal_scos_measure_enbws:
            self.test_calibration_data['scos']['enbws'] = deepcopy(r.measured_enbws)
        if self.profile.cal_scos_measure_noise_figure:
            self.test_calibration_data['scos']['noise_figures'] = deepcopy(r.noise_figures)
            self.test_calibration_data['scos']['noise_powers'] = deepcopy(r.noise_powers)
        if self.profile.cal_scos_measure_compression:
            self.test_calibration_data['scos']['compression_levels'] = deepcopy(r.compression_levels)
        self.logger.logln("Done!")

        # Save the data into a sub folder
        #self.logger.log("Saving SCOS sensor calibration data... ")
        #self.root_save_directory = self.save_directory
        #self.save_directory = "{}/scos_calibration".format(self.save_directory)
        #if not os.path.exists(self.save_directory):
        #    os.makedirs(self.save_directory)
        #r.sdr_serial_number = self.sdr_serial_number
        #r.save_data()
        #self.save_directory = self.root_save_directory
        #self.logger.logln("Done!")
        self.logger.flush()

        # Preset th siggen so the user can change connections
        self.logger.log("Returning signal generator to preset so it is safe to adjust connections... ")
        self.siggen.preset()
        self.logger.logln("Done!")
        
        # Ask the user to connect the entire sdr in the scos sensor
        self.pause_for_user_action("Please connect the SDR in the SCOS sensor as the DUT")
        self.logger.logln("Running calibration on SCOS SDR...")
        self.logger.stepin()

        # Run the calibration on the entire SCOS SDR
        self.dependency_test_profile_adjustments = {
            'test_measure_scale_factor': self.profile.cal_sdr_measure_scale_factor,
            'test_measure_enbws':        self.profile.cal_sdr_measure_enbws,
            'test_measure_noise_figure': self.profile.cal_sdr_measure_noise_figure,
            'test_measure_compression':  self.profile.cal_sdr_measure_compression,
            'test_measure_spur_free':    self.profile.cal_sdr_measure_spur_free,

            'sweep_f_min':         self.profile.cal_sdr_sweep_f_min,
            'sweep_f_max':         self.profile.cal_sdr_sweep_f_max,
            'sweep_f_num_steps':   self.profile.cal_sdr_sweep_f_num_steps,
            'sweep_f_lin_spacing': self.profile.cal_sdr_sweep_f_lin_spacing,
            'sweep_f_log_steps':   self.profile.cal_sdr_sweep_f_log_steps,
            'sweep_f_extra':       self.profile.cal_sdr_sweep_f_extra,
            'sweep_f_divisions':   self.profile.cal_sdr_sweep_f_divisions,
            'sweep_g_min':         self.profile.cal_sdr_sweep_g_min,
            'sweep_g_max':         self.profile.cal_sdr_sweep_g_max,
            'sweep_g_num_steps':   self.profile.cal_sdr_sweep_g_num_steps,
            'sweep_g_lin_spacing': self.profile.cal_sdr_sweep_g_lin_spacing,
            'sweep_g_log_steps':   self.profile.cal_sdr_sweep_g_log_steps,
            'sweep_g_extra':       self.profile.cal_sdr_sweep_g_extra,
            
            'scale_factor_power_level':        self.profile.cal_sdr_scale_factor_power_level,
            'scale_factor_measurement_method': self.profile.cal_sdr_scale_factor_measurement_method,

            'enbw_frequency':                self.profile.cal_sdr_enbw_frequency,
            'enbw_gain':                     self.profile.cal_sdr_enbw_gain,
            'enbw_power_level':              self.profile.cal_sdr_enbw_power_level,
            'enbw_measurement_band_stretch': self.profile.cal_sdr_enbw_measurement_band_stretch,
            'enbw_transfer_function_points': self.profile.cal_sdr_enbw_transfer_function_points,

            'noise_figure_enbws':       self.profile.cal_sdr_noise_figure_enbws,
            'noise_figure_terminating': self.profile.cal_sdr_noise_figure_terminating,
            'noise_figure_input_power': self.profile.cal_sdr_noise_figure_input_power,
            
            'compression_skip_sample_rate_cycling': self.profile.cal_sdr_compression_skip_sample_rate_cycling,
            'compression_decimate_frequencies':     self.profile.cal_sdr_compression_decimate_frequencies,
            'compression_min_power':                self.profile.cal_sdr_compression_min_power,
            'compression_max_power':                self.profile.cal_sdr_compression_max_power,
            'compression_power_step':               self.profile.cal_sdr_compression_power_step,
            'compression_measurement_method':       self.profile.cal_sdr_compression_measurement_method,
            'compression_threshold':                self.profile.cal_sdr_compression_threshold,
            'compression_linearity_steps':          self.profile.cal_sdr_compression_linearity_steps,
            'compression_linearity_threshold':      self.profile.cal_sdr_compression_linearity_threshold,

            'spur_free_measurement_remove_ranges': self.profile.cal_sdr_spur_free_measurement_remove_ranges,
            'spur_free_danl_num':                  self.profile.cal_sdr_spur_free_danl_num,
            'spur_free_threshold':                 self.profile.cal_sdr_spur_free_threshold
        }
        subtest_save_directory = "{}/sdr_calibration".format(self.save_directory)
        self.run_dependency_test(
            self.calibrate,
            self.dependency_test_profile_adjustments
        )
        self.logger.stepout()
        self.logger.logln("Finished calibrating SCOS SDR!")

        # Recover the data from the test
        self.logger.log("Recovering calibration data... ")
        r = self.calibrate
        self.test_calibration_data['sdr']['fs'] = r.sweep_list_1
        self.test_calibration_data['sdr']['gs'] = r.sweep_list_2
        if self.profile.cal_sdr_measure_scale_factor:
            self.test_calibration_data['sdr']['scale_factors'] = r.scale_factors
            self.test_calibration_data['sdr']['empirical_gains'] = deepcopy(r.empirical_gains)
        if self.profile.cal_sdr_measure_enbws:
            self.test_calibration_data['sdr']['enbws'] = r.measured_enbws
        if self.profile.cal_sdr_measure_noise_figure:
            self.test_calibration_data['sdr']['noise_figures'] = r.noise_figures
            self.test_calibration_data['sdr']['noise_powers'] = r.noise_powers
        if self.profile.cal_sdr_measure_compression:
            self.test_calibration_data['sdr']['compression_levels'] = r.compression_levels
        self.logger.logln("Done!")

        # Scale the compression data from the SDR to SCOS
        if self.profile.cal_sdr_measure_compression:
            self.logger.log("Extending compression levels from SDR to SCOS... ")
            self.test_calibration_data['scos']['compression_levels'] = deepcopy(self.test_calibration_data['scos']['scale_factors'])
            for k in range(len(self.profile.test_sample_rates)):
                for j in range(len(self.test_calibration_data['scos']['gs'])):
                    # Find the sdr gain immediately below the scos gain
                    j_sdr = len(self.test_calibration_data['sdr']['gs'])-2
                    for l in range(len(self.test_calibration_data['sdr']['gs'])-1):
                        if self.test_calibration_data['sdr']['gs'][l+1] > self.test_calibration_data['scos']['gs'][j]:
                            j_sdr = l
                            break
                    for i in range(len(self.test_calibration_data['scos']['fs'])):
                        # Find the sdr freq immediately below the scos freq
                        i_sdr = len(self.test_calibration_data['sdr']['fs'])-2
                        for l in range(len(self.test_calibration_data['sdr']['fs'])-1):
                            if self.test_calibration_data['sdr']['fs'][l+1] > self.test_calibration_data['scos']['fs'][i]:
                                i_sdr = l
                                break
                        # Interpolate to find the scale factor and compression point
                        sdr_scale_factor = utils.interpolate_2d(
                            self.test_calibration_data['scos']['fs'][i],
                            self.test_calibration_data['scos']['gs'][j],
                            self.test_calibration_data['sdr']['fs'][i_sdr],
                            self.test_calibration_data['sdr']['fs'][i_sdr+1],
                            self.test_calibration_data['sdr']['gs'][j_sdr],
                            self.test_calibration_data['sdr']['gs'][j_sdr+1],
                            self.test_calibration_data['sdr']['scale_factors'][k][i_sdr][j_sdr],
                            self.test_calibration_data['sdr']['scale_factors'][k][i_sdr+1][j_sdr],
                            self.test_calibration_data['sdr']['scale_factors'][k][i_sdr][j_sdr+1],
                            self.test_calibration_data['sdr']['scale_factors'][k][i_sdr+1][j_sdr+1]
                        )
                        sdr_compression = utils.interpolate_2d(
                            self.test_calibration_data['scos']['fs'][i],
                            self.test_calibration_data['scos']['gs'][j],
                            self.test_calibration_data['sdr']['fs'][i_sdr],
                            self.test_calibration_data['sdr']['fs'][i_sdr+1],
                            self.test_calibration_data['sdr']['gs'][j_sdr],
                            self.test_calibration_data['sdr']['gs'][j_sdr+1],
                            self.test_calibration_data['sdr']['compression_levels'][k][i_sdr][j_sdr],
                            self.test_calibration_data['sdr']['compression_levels'][k][i_sdr+1][j_sdr],
                            self.test_calibration_data['sdr']['compression_levels'][k][i_sdr][j_sdr+1],
                            self.test_calibration_data['sdr']['compression_levels'][k][i_sdr+1][j_sdr+1]
                        )
                        scos_compression = sdr_compression-sdr_scale_factor + self.test_calibration_data['scos']['scale_factors'][k][i][j]
                        self.test_calibration_data['scos']['compression_levels'][k][i][j] = scos_compression
                        print("  Calculated for SCOS:")
                        print("    SDR scale factor:  {}".format(sdr_scale_factor))
                        print("    SCOS scale factor: {}".format(self.test_calibration_data['scos']['scale_factors'][k][i][j]))
                        print("    SDR compression:   {}".format(sdr_compression))
                        print("    SCOS compression:  {}".format(scos_compression))
                if self.profile.cal_sdr_compression_skip_sample_rate_cycling:
                    self.profile.cal_scos_compression_skip_sample_rate_cycling = True
                    break
            r.compression_levels = self.test_calibration_data['scos']['compression_levels']
            self.profile.cal_scos_measure_compression = True
            self.logger.logln("Done!")
        
        # Calculate the front-end calibration values
        self.logger.logln("Calculating front end calibration values...")
        self.logger.stepin()
        self.test_calibration_data['fe'] = deepcopy(self.test_calibration_data['scos'])
        for param_num in range(3):
            # Get the parameter to be calculated
            if param_num == 0:
                # Check if can be calculated
                if self.profile.cal_sdr_measure_scale_factor and self.profile.cal_scos_measure_scale_factor:
                    self.logger.log("Calculating front-end gain... ")
                    scos_cal = self.test_calibration_data['scos']['empirical_gains']
                    sdr_cal  = self.test_calibration_data['sdr']['empirical_gains']
                    fe_cal   = self.test_calibration_data['fe']['empirical_gains']
                else:
                    continue
            if param_num == 1:
                # Check if can be calculated
                if self.profile.cal_sdr_measure_noise_figure and self.profile.cal_scos_measure_noise_figure:
                    self.logger.log("Calculating front-end noise figure... ")
                    scos_cal = self.test_calibration_data['scos']['noise_figures']
                    sdr_cal  = self.test_calibration_data['sdr']['noise_figures']
                    fe_cal   = self.test_calibration_data['fe']['noise_figures']
                else:
                    continue
            if param_num == 2:
                # Check if can be calculated
                if self.profile.cal_sdr_measure_compression and self.profile.cal_scos_measure_compression:
                    self.logger.log("Calculating front-end compression... ")
                    scos_cal = self.test_calibration_data['scos']['compression_levels']
                    sdr_cal  = self.test_calibration_data['sdr']['compression_levels']
                    fe_cal   = self.test_calibration_data['fe']['compression_levels']
                else:
                    continue
            
            # Cycle through all the SCOS values
            for k in range(len(self.profile.test_sample_rates)):
                for j in range(len(self.test_calibration_data['scos']['gs'])):
                    # Find the sdr gain immediately below the scos gain
                    j_sdr = len(self.test_calibration_data['sdr']['gs'])-2
                    for l in range(len(self.test_calibration_data['sdr']['gs'])-1):
                        if self.test_calibration_data['sdr']['gs'][l+1] > self.test_calibration_data['scos']['gs'][j]:
                            j_sdr = l
                            break
                    for i in range(len(self.test_calibration_data['scos']['fs'])):
                        # Find the sdr freq immediately below the scos freq
                        i_sdr = len(self.test_calibration_data['sdr']['fs'])-2
                        for l in range(len(self.test_calibration_data['sdr']['fs'])-1):
                            if self.test_calibration_data['sdr']['fs'][l+1] > self.test_calibration_data['scos']['fs'][i]:
                                i_sdr = l
                                break
                        # Interpolate to find the sdr parameter at the f and g
                        print("{} - {} - {} - {}".format(param_num, k, i_sdr, j_sdr))
                        sdr_cal_val = utils.interpolate_2d(
                            self.test_calibration_data['scos']['fs'][i],
                            self.test_calibration_data['scos']['gs'][j],
                            self.test_calibration_data['sdr']['fs'][i_sdr],
                            self.test_calibration_data['sdr']['fs'][i_sdr+1],
                            self.test_calibration_data['sdr']['gs'][j_sdr],
                            self.test_calibration_data['sdr']['gs'][j_sdr+1],
                            sdr_cal[k][i_sdr][j_sdr],
                            sdr_cal[k][i_sdr+1][j_sdr],
                            sdr_cal[k][i_sdr][j_sdr+1],
                            sdr_cal[k][i_sdr+1][j_sdr+1]
                        )
                        # Calculate the front-end value based on the param
                        if param_num == 0:
                            fe_cal[k][i][j] = scos_cal[k][i][j] - sdr_cal_val
                        if param_num == 1:
                            scos_nf = 10**((scos_cal[k][i][j])/10)
                            sdr_nf  = 10**(sdr_cal[k][i][j]/10)
                            fe_g    = 10**(self.test_calibration_data['fe']['empirical_gains'][k][i][j]/10)
                            fe_cal[k][i][j] = scos_nf-(sdr_nf-1)/fe_g
                            # Ensure measurement error doesn't result with an unphysical result
                            if fe_cal[k][i][j] < 1:
                                fe_cal[k][i][j] = 1
                            print("NF SCOS: {}".format(scos_cal[k][i][j]))
                            print("NF SDR:  {}".format(sdr_cal[k][i][j]))
                            print("nf SCOS: {}".format(scos_nf))
                            print("nf SDR:  {}".format(sdr_nf))
                            print("G  FE:   {}".format(self.test_calibration_data['fe']['empirical_gains'][k][i][j]))
                            print("g  FE:  {}".format(fe_g))
                            print("    nf FE:  {}".format(fe_cal[k][i][j]))
                            fe_cal[k][i][j] = 10*np.log10(fe_cal[k][i][j])
                            print("    NF FE:  {}".format(fe_cal[k][i][j]))
                        if param_num == 2:
                            scos_c = 10**(scos_cal[k][i][j]/10)
                            sdr_c  = 10**(sdr_cal[k][i][j]/10)
                            fe_g   = 10**(self.test_calibration_data['fe']['empirical_gains'][k][i][j]/10)
                            sdr_c *= fe_g
                            # Ensure measurement error does not give an unphysical result
                            if scos_c >= sdr_c:
                                fe_cal[k][i][j] = 100
                            else:
                                fe_cal[k][i][j] = (scos_c**-1 - sdr_c**-1)**-1
                                fe_cal[k][i][j] = 10*np.log10(fe_cal[k][i][j])
                                # Cap the compression at 100dBm
                                if fe_cal[k][i][j] > 100:
                                    fe_cal[k][i][j] = 100
                # If this is compression, copy the data over
                if param_num == 2 and (self.profile.cal_sdr_compression_skip_sample_rate_cycling or self.profile.cal_scos_compression_skip_sample_rate_cycling):
                    break
            self.logger.logln("Done!")
        self.logger.stepout()
        
        # Save the data into a sub folder
        #self.logger.log("Saving SCOS SDR calibration data... ")
        #self.root_save_directory = self.save_directory
        #self.save_directory = "{}/sdr_calibration".format(self.save_directory)
        #if not os.path.exists(self.save_directory):
        #    os.makedirs(self.save_directory)
        #r.sdr_serial_number = self.sdr_serial_number
        #r.save_data()
        #self.save_directory = self.root_save_directory
        #self.logger.logln("Done!")


    # Save data or construct plot if required
    def save_data(self):
        # Save the test summary if requested
        if self.profile.logging_save_test_summary:
            self.logger.log("Writing test data to file... ")
            base_save_directory = self.save_directory
            cal_time = datetime.datetime.utcnow().isoformat()

            # Create the sdr directory and write the data
            self.save_directory = "{}/sdr".format(base_save_directory)
            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory)
            if self.profile.cal_sdr_measure_enbws:
                fname = "enbw_summary.csv"
                with open(self.save_file(fname), 'w+') as file:
                    file.write("sample_rate,clock_freq,ENBW\r\n")
                    for k in range(len(self.profile.test_sample_rates)):
                        file.write("{},{},{}\r\n".format(
                            self.logger.to_MHz(self.profile.test_sample_rates[k]),
                            self.logger.to_MHz(self.profile.test_clock_frequencies[k]),
                            self.logger.to_MHz(self.test_calibration_data['sdr']['enbws'][k]),
                        ))
            for k in range(len(self.profile.test_sample_rates)):
                sr = self.profile.test_sample_rates[k]
                cf = self.profile.test_clock_frequencies[k]
                if self.profile.cal_sdr_measure_compression:
                    fname = "compression_summary_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['sdr']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['sdr']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['sdr']['fs'])):
                            file.write("{}".format(self.test_calibration_data['sdr']['fs'][i]))
                            for j in range(len(self.test_calibration_data['sdr']['gs'])):
                                if self.profile.cal_sdr_compression_skip_sample_rate_cycling:
                                    file.write(",{}".format(self.test_calibration_data['sdr']['compression_levels'][0][i][j]))
                                else:
                                    file.write(",{}".format(self.test_calibration_data['sdr']['compression_levels'][k][i][j]))
                            file.write("\r\n")
                        file.close()
                if self.profile.cal_sdr_measure_scale_factor:
                    fname = "scale_factors_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['sdr']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['sdr']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['sdr']['fs'])):
                            file.write("{}".format(self.test_calibration_data['sdr']['fs'][i]))
                            for j in range(len(self.test_calibration_data['sdr']['gs'])):
                                file.write(",{}".format(self.test_calibration_data['sdr']['scale_factors'][k][i][j]))
                            file.write("\r\n")
                        file.close()
                if self.profile.cal_sdr_measure_noise_figure:
                    fname = "noise_powers_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['sdr']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['sdr']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['sdr']['fs'])):
                            file.write("{}".format(self.test_calibration_data['sdr']['fs'][i]))
                            for j in range(len(self.test_calibration_data['sdr']['gs'])):
                                file.write(",{}".format(self.test_calibration_data['sdr']['noise_powers'][k][i][j][0]))
                            file.write("\r\n")
                        file.close()
                    fname = "noise_figures_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['sdr']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['sdr']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['sdr']['fs'])):
                            file.write("{}".format(self.test_calibration_data['sdr']['fs'][i]))
                            for j in range(len(self.test_calibration_data['sdr']['gs'])):
                                file.write(",{}".format(self.test_calibration_data['sdr']['noise_figures'][k][i][j]))
                            file.write("\r\n")
                        file.close()
            cal_data_json = {}
            for k,v in self.profile.cal_sdr_additional_calibration_fields.items():
                cal_data_json[k] = v
            cal_data_json['sigan_uid'] = self.sdr_serial_number
            cal_data_json['calibration_datetime'] = "{}Z".format(cal_time)
            cal_data_json['calibration_frequency_divisions'] = []
            for i in range(len(self.profile.cal_sdr_sweep_f_divisions)):
                cal_data_json['calibration_frequency_divisions'].append({
                    'lower_bound': self.profile.cal_sdr_sweep_f_divisions[i][0],
                    'upper_bound': self.profile.cal_sdr_sweep_f_divisions[i][1]
                })
            cal_data_json['clock_rate_lookup_by_sample_rate'] = []
            for i in range(len(self.profile.test_sample_rates)):
                cal_data_json['clock_rate_lookup_by_sample_rate'].append({
                    "sample_rate": self.profile.test_sample_rates[i],
                    "clock_frequency": self.profile.test_clock_frequencies[i]
                })
            """
            cal_data_json['calibration_points'] = []
            for k in range(len(self.profile.test_sample_rates)):
                for i in range(len(self.test_calibration_data['sdr']['fs'])):
                    for j in range(len(self.test_calibration_data['sdr']['gs'])):
                        cal_data_point = {
                            'freq_sigan': self.test_calibration_data['sdr']['fs'][i],
                            'gain_sigan': self.test_calibration_data['sdr']['gs'][j],
                            'sample_rate_sigan': self.profile.test_sample_rates[k]
                        }
                        if self.profile.cal_sdr_measure_compression:
                            if self.profile.cal_sdr_compression_skip_sample_rate_cycling:
                                cal_data_point['1dB_compression'] = self.test_calibration_data['sdr']['compression_levels'][0][i][j]
                            else:
                                cal_data_point['1dB_compression'] = self.test_calibration_data['sdr']['compression_levels'][k][i][j]
                        if self.profile.cal_sdr_measure_scale_factor:
                            cal_data_point['scale_factor'] = self.test_calibration_data['sdr']['scale_factors'][k][i][j]
                            cal_data_point['gain_sigan_2'] = self.test_calibration_data['sdr']['empirical_gains'][k][i][j]
                        if self.profile.cal_sdr_measure_noise_figure:
                            cal_data_point['noise_figure'] = self.test_calibration_data['sdr']['noise_figures'][k][i][j]
                        if self.profile.cal_sdr_measure_enbws:
                            cal_data_point['equivalent_noise_bw'] = self.test_calibration_data['sdr']['enbws'][k]
                        cal_data_json['calibration_points'].append(cal_data_point)"""
            cal_data_json['calibration_data'] = {}
            cal_data_json['calibration_data']['sample_rates'] = []
            for k in range(len(self.profile.test_sample_rates)):
                cal_data_json_sr = {}
                cal_data_json_sr['sample_rate'] = self.profile.test_sample_rates[k]
                cal_data_json_sr['calibration_data'] = {}
                cal_data_json_sr['calibration_data']['frequencies'] = []
                for i in range(len(self.test_calibration_data['sdr']['fs'])):
                    cal_data_json_f = {}
                    cal_data_json_f['frequency'] = self.test_calibration_data['sdr']['fs'][i]
                    cal_data_json_f['calibration_data'] = {}
                    cal_data_json_f['calibration_data']['gains'] = []
                    for j in range(len(self.test_calibration_data['sdr']['gs'])):
                        cal_data_json_g = {}
                        cal_data_json_g['gain'] = self.test_calibration_data['sdr']['gs'][j]
                        
                        # Add the calibration data
                        cal_data_point = {}
                        if self.profile.cal_sdr_measure_compression:
                            if self.profile.cal_sdr_compression_skip_sample_rate_cycling:
                                cal_data_point['1dB_compression_sigan'] = self.test_calibration_data['sdr']['compression_levels'][0][i][j]
                            else:
                                cal_data_point['1dB_compression_sigan'] = self.test_calibration_data['sdr']['compression_levels'][k][i][j]
                        if self.profile.cal_sdr_measure_scale_factor:
                            cal_data_point['gain_sigan'] = self.test_calibration_data['sdr']['empirical_gains'][k][i][j]
                        if self.profile.cal_sdr_measure_noise_figure:
                            cal_data_point['noise_figure_sigan'] = self.test_calibration_data['sdr']['noise_figures'][k][i][j]
                        if self.profile.cal_sdr_measure_enbws:
                            cal_data_point['enbw_sigan'] = self.test_calibration_data['sdr']['enbws'][k]

                        # Add the generated dicts to the parent lists
                        cal_data_json_g['calibration_data'] = deepcopy(cal_data_point)
                        cal_data_json_f['calibration_data']['gains'].append(deepcopy(cal_data_json_g))
                    cal_data_json_sr['calibration_data']['frequencies'].append(deepcopy(cal_data_json_f))
                cal_data_json['calibration_data']['sample_rates'].append(deepcopy(cal_data_json_sr))
            self.write_calibration_file("calibration_file.json", src_file=None, json_dict=cal_data_json)
        
        # Create the scos directory and write the data
            self.save_directory = "{}/scos".format(base_save_directory)
            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory)
            if self.profile.cal_scos_measure_enbws:
                fname = "enbw_summary.csv"
                with open(self.save_file(fname), 'w+') as file:
                    file.write("sample_rate,clock_freq,ENBW\r\n")
                    for k in range(len(self.profile.test_sample_rates)):
                        file.write("{},{},{}\r\n".format(
                            self.logger.to_MHz(self.profile.test_sample_rates[k]),
                            self.logger.to_MHz(self.profile.test_clock_frequencies[k]),
                            self.logger.to_MHz(self.test_calibration_data['scos']['enbws'][k]),
                        ))
            for k in range(len(self.profile.test_sample_rates)):
                sr = self.profile.test_sample_rates[k]
                cf = self.profile.test_clock_frequencies[k]
                if self.profile.cal_scos_measure_compression:
                    fname = "compression_summary_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['scos']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['scos']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['scos']['fs'])):
                            file.write("{}".format(self.test_calibration_data['scos']['fs'][i]))
                            for j in range(len(self.test_calibration_data['scos']['gs'])):
                                if self.profile.cal_scos_compression_skip_sample_rate_cycling:
                                    file.write(",{}".format(self.test_calibration_data['scos']['compression_levels'][0][i][j]))
                                else:
                                    file.write(",{}".format(self.test_calibration_data['scos']['compression_levels'][k][i][j]))
                            file.write("\r\n")
                        file.close()
                if self.profile.cal_scos_measure_scale_factor:
                    fname = "scale_factors_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['scos']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['scos']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['scos']['fs'])):
                            file.write("{}".format(self.test_calibration_data['scos']['fs'][i]))
                            for j in range(len(self.test_calibration_data['scos']['gs'])):
                                file.write(",{}".format(self.test_calibration_data['scos']['scale_factors'][k][i][j]))
                            file.write("\r\n")
                        file.close()
                if self.profile.cal_scos_measure_noise_figure:
                    fname = "noise_powers_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['scos']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['scos']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['scos']['fs'])):
                            file.write("{}".format(self.test_calibration_data['scos']['fs'][i]))
                            for j in range(len(self.test_calibration_data['scos']['gs'])):
                                file.write(",{}".format(self.test_calibration_data['scos']['noise_powers'][k][i][j][0]))
                            file.write("\r\n")
                        file.close()
                    fname = "noise_figures_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['scos']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['scos']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['scos']['fs'])):
                            file.write("{}".format(self.test_calibration_data['scos']['fs'][i]))
                            for j in range(len(self.test_calibration_data['scos']['gs'])):
                                file.write(",{}".format(self.test_calibration_data['scos']['noise_figures'][k][i][j]))
                            file.write("\r\n")
                        file.close()
                if self.profile.cal_scos_measure_compression and self.profile.cal_sdr_measure_compression:
                    fname = "compression_summary_frontend_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['scos']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['scos']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['scos']['fs'])):
                            file.write("{}".format(self.test_calibration_data['scos']['fs'][i]))
                            for j in range(len(self.test_calibration_data['scos']['gs'])):
                                if self.profile.cal_scos_compression_skip_sample_rate_cycling or self.profile.cal_sdr_compression_skip_sample_rate_cycling:
                                    file.write(",{}".format(self.test_calibration_data['fe']['compression_levels'][0][i][j]))
                                else:
                                    file.write(",{}".format(self.test_calibration_data['fe']['compression_levels'][k][i][j]))
                            file.write("\r\n")
                        file.close()
                if self.profile.cal_scos_measure_scale_factor and self.profile.cal_sdr_measure_scale_factor:
                    fname = "empirical_gains_frontend_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['scos']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['scos']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['scos']['fs'])):
                            file.write("{}".format(self.test_calibration_data['scos']['fs'][i]))
                            for j in range(len(self.test_calibration_data['scos']['gs'])):
                                file.write(",{}".format(self.test_calibration_data['fe']['empirical_gains'][k][i][j]))
                            file.write("\r\n")
                        file.close()
                if self.profile.cal_scos_measure_noise_figure and self.profile.cal_sdr_measure_noise_figure:
                    fname = "noise_figures_frontend_({},{}).csv".format(
                        self.logger.to_MHz(sr),
                        self.logger.to_MHz(cf)
                    )
                    with open(self.save_file(fname), 'w+') as file:
                        for j in range(len(self.test_calibration_data['scos']['gs'])):
                            file.write(",{}".format(self.test_calibration_data['scos']['gs'][j]))
                        file.write("\r\n")
                        for i in range(len(self.test_calibration_data['scos']['fs'])):
                            file.write("{}".format(self.test_calibration_data['scos']['fs'][i]))
                            for j in range(len(self.test_calibration_data['scos']['gs'])):
                                file.write(",{}".format(self.test_calibration_data['fe']['noise_figures'][k][i][j]))
                            file.write("\r\n")
                        file.close()
            cal_data_json = {}
            for k,v in self.profile.cal_scos_additional_calibration_fields.items():
                cal_data_json[k] = v
            cal_data_json['sigan_uid'] = self.sdr_serial_number
            cal_data_json['calibration_datetime'] = "{}Z".format(cal_time)
            cal_data_json['calibration_frequency_divisions'] = []
            for i in range(len(self.profile.cal_scos_sweep_f_divisions)):
                cal_data_json['calibration_frequency_divisions'].append({
                    'lower_bound': self.profile.cal_scos_sweep_f_divisions[i][0],
                    'upper_bound': self.profile.cal_scos_sweep_f_divisions[i][1]
                })
            cal_data_json['clock_rate_lookup_by_sample_rate'] = []
            for i in range(len(self.profile.test_sample_rates)):
                cal_data_json['clock_rate_lookup_by_sample_rate'].append({
                    "sample_rate": self.profile.test_sample_rates[i],
                    "clock_frequency": self.profile.test_clock_frequencies[i]
                })
            """cal_data_json['calibration_points'] = []
            for k in range(len(self.profile.test_sample_rates)):
                for i in range(len(self.test_calibration_data['scos']['fs'])):
                    for j in range(len(self.test_calibration_data['scos']['gs'])):
                        cal_data_point = {
                            'freq_sigan': self.test_calibration_data['scos']['fs'][i],
                            'gain_sigan': self.test_calibration_data['scos']['gs'][j],
                            'sample_rate_sigan': self.profile.test_sample_rates[k]
                        }
                        if self.profile.cal_scos_measure_compression:
                            if self.profile.cal_scos_compression_skip_sample_rate_cycling:
                                cal_data_point['1dB_compression_sensor'] = self.test_calibration_data['scos']['compression_levels'][0][i][j]
                            else:
                                cal_data_point['1dB_compression_sensor'] = self.test_calibration_data['scos']['compression_levels'][k][i][j]
                            if self.profile.cal_sdr_measure_compression:
                                if self.profile.cal_scos_compression_skip_sample_rate_cycling:
                                    cal_data_point['1dB_compression_preselector'] = self.test_calibration_data['fe']['compression_levels'][0][i][j]
                                else:
                                    cal_data_point['1dB_compression_preselector'] = self.test_calibration_data['fe']['compression_levels'][k][i][j]
                        if self.profile.cal_scos_measure_scale_factor:
                            cal_data_point['scale_factor_sensor'] = self.test_calibration_data['scos']['scale_factors'][k][i][j]
                            cal_data_point['gain_sensor'] = self.test_calibration_data['scos']['empirical_gains'][k][i][j]
                            if self.profile.cal_sdr_measure_scale_factor:
                                cal_data_point['gain_preselector'] = self.test_calibration_data['fe']['empirical_gains'][k][i][j]
                        if self.profile.cal_scos_measure_noise_figure:
                            cal_data_point['noise_figure'] = self.test_calibration_data['scos']['noise_figures'][k][i][j]
                            if self.profile.cal_sdr_measure_noise_figure:
                                cal_data_point['noise_figure_preselector'] = self.test_calibration_data['fe']['noise_figures'][k][i][j]
                        if self.profile.cal_scos_measure_enbws:
                            cal_data_point['equivalent_noise_bw'] = self.test_calibration_data['scos']['enbws'][k]
                        cal_data_json['calibration_points'].append(cal_data_point)"""
            cal_data_json['calibration_data'] = {}
            cal_data_json['calibration_data']['sample_rates'] = []
            for k in range(len(self.profile.test_sample_rates)):
                cal_data_json_sr = {}
                cal_data_json_sr['sample_rate'] = self.profile.test_sample_rates[k]
                cal_data_json_sr['calibration_data'] = {}
                cal_data_json_sr['calibration_data']['frequencies'] = []
                for i in range(len(self.test_calibration_data['scos']['fs'])):
                    cal_data_json_f = {}
                    cal_data_json_f['frequency'] = self.test_calibration_data['scos']['fs'][i]
                    cal_data_json_f['calibration_data'] = {}
                    cal_data_json_f['calibration_data']['gains'] = []
                    for j in range(len(self.test_calibration_data['scos']['gs'])):
                        cal_data_json_g = {}
                        cal_data_json_g['gain'] = self.test_calibration_data['scos']['gs'][j]
                        
                        # Add the calibration data
                        cal_data_point = {}
                        if self.profile.cal_scos_measure_compression:
                            if self.profile.cal_scos_compression_skip_sample_rate_cycling:
                                cal_data_point['1dB_compression_sensor'] = self.test_calibration_data['scos']['compression_levels'][0][i][j]
                            else:
                                cal_data_point['1dB_compression_sensor'] = self.test_calibration_data['scos']['compression_levels'][k][i][j]
                            if self.profile.cal_sdr_measure_compression:
                                if self.profile.cal_scos_compression_skip_sample_rate_cycling:
                                    cal_data_point['1dB_compression_preselector'] = self.test_calibration_data['fe']['compression_levels'][0][i][j]
                                else:
                                    cal_data_point['1dB_compression_preselector'] = self.test_calibration_data['fe']['compression_levels'][k][i][j]
                        if self.profile.cal_scos_measure_scale_factor:
                            cal_data_point['gain_sensor'] = self.test_calibration_data['scos']['empirical_gains'][k][i][j]
                            if self.profile.cal_sdr_measure_scale_factor:
                                cal_data_point['gain_preselector'] = self.test_calibration_data['fe']['empirical_gains'][k][i][j]
                        if self.profile.cal_scos_measure_noise_figure:
                            cal_data_point['noise_figure_sensor'] = self.test_calibration_data['scos']['noise_figures'][k][i][j]
                            if self.profile.cal_sdr_measure_noise_figure:
                                cal_data_point['noise_figure_preselector'] = self.test_calibration_data['fe']['noise_figures'][k][i][j]
                        if self.profile.cal_scos_measure_enbws:
                            cal_data_point['enbw_sensor'] = self.test_calibration_data['scos']['enbws'][k]

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
