import time
import os
import math
import csv

import numpy as np
from scipy import signal, integrate

from matplotlib import pyplot as plt

from operator import itemgetter

import sdrcalibrator.lib.utils.common as utils
import sdrcalibrator.lib.utils.error as Error
from sdrcalibrator.lib.utils.logging import Logger
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error

import json
from shutil import copyfile

from signal import signal, SIGPIPE, SIG_DFL
# signal(SIGPIPE, SIG_DFL)


""" Base test class for the different tests """
class SDR_Test_Class(object):

    TEST_PROFILE_DEFINITIONS = {
        'required_tests': [],
        'required_profile_parameters': [],
        'required_equipment': [],
        'possible_functionality': [],
        'profile_parameter_defaults': {},
        'forced_profile_parameters': {}, 
        'setup_correction_factors' : {},
        'pwr_correction_factors_set':False
    }

    """ Equipment parameter definition dict """
    EQUIPMENT_PARAMETER_DEFINITIONS = {
        'sdr': {
            'required_profile_parameters': [
                'sdr_module',
                'sdr_connect_params'
            ],
            'defaultable_profile_parameters': [
                'sdr_clock_frequency',
                'sdr_sampling_frequency',
                'sdr_auto_dc_offset',
                'sdr_auto_iq_imbalance',
                'sdr_gain',
                'sdr_f0_tuning_error_threshold',
                'sdr_use_dsp_lo_shift',
                'sdr_dsp_lo_shift',
                'sdr_conditioning_samples',
                'sdr_power_limit',
                'sdr_power_scale_factor',
                'sdr_power_scale_factor_file'
            ]
        },
        'siggen': {
            'required_profile_parameters': [
                'siggen_module',
                'siggen_connect_params'
            ],
            'defaultable_profile_parameters': [
                'siggen_rf_on_settling_time',
                'siggen_rf_off_settling_time'
            ]
        },
        'pwrmtr': {
            'required_profile_parameters': [
                'pwrmtr_module',
                'pwrmtr_connect_params'
            ],
            'defaultable_profile_parameters': []
        },
        'switch': {
            'required_profile_parameters': [
                # 'switch_module',
                # 'switch_connect_params'
            ],
            'defaultable_profile_parameters': [
                'switch_swap_inputs',
                'switch_correction_factor_file'
            ]
        },
        'atten': {
            'required_profile_parameters': [
                'atten_module',
                'atten_connect_params',
                'atten_setup_params'
            ],
            'defaultable_profile_parameters': [
                'atten_settling_time'
            ]
        }
    }

    """ Store the profile and initialize the logger """
    def __init__(self, profile, logger):
        self.profile = profile
        if logger is None:
            self.logger = Logger()
        else:
            self.logger = logger
        self.equipment_in_use = {}
        self.equipment_errors = {}

        """ Define the initial profile definitions """
        self.PROFILE_DEFINITIONS = {
            'required_tests': [],
            'required_profile_parameters': [
                'test_type',
                'freq_f0',
                'fft_number_of_bins'
            ],
            'required_equipment': [],
            'possible_functionality': [],
            'profile_parameter_defaults': {
                'sweep_f_num_steps': False,
                'sweep_f_lin_spacing': False,
                'sweep_f_log_steps': False,
                'sweep_f_extra': [],
                'sweep_f_order': 'asc',
                'sweep_p_num_steps': False,
                'sweep_p_lin_spacing': False,
                'sweep_p_log_steps': False,
                'sweep_p_extra': [],
                'sweep_p_order': 'asc',
                'sweep_g_num_steps': False,
                'sweep_g_lin_spacing': False,
                'sweep_g_log_steps': False,
                'sweep_g_extra': [],
                'sweep_g_order': 'asc',

                'freq_use_offset': False,
                'freq_offset_f0_and_cw': 'DEFAULT',
                'freq_offset_using_sdr': False,

                'power_stimulus': None,
                'power_level_mode': 'normal',
                'power_base_power': 0,
                'power_verification': None,
                'power_inline_attenuator': 0,
                'power_limit_output_power': True,
                'power_scale_cw_power_with_sdr_gain': False,

                'fft_minimum_frequency_resolution': False,
                'fft_averaging_number': 1,
                'fft_window': None,

                'logging_quiet_mode': False,
                'logging_save_log_file': False
            },
            'forced_profile_parameters': {}
        }

        self.merge_profile_definitions()

        # print("AFTER MERGE PROFILE IN INIT\n")
    
        # print(self.PROFILE_DEFINITIONS['required_equipment'])

    """
        >>>
            CHAPTER 1: GENERAL TEST FUNCTIONS
        >>>
    """

    """ Main function to run test with all initializations """
    def run(self):
        # Initialize the test
        self.initialize_test()
        print("\nCHECKING EQUIPMENT IN USE (1):")
        print(self.equipment_in_use)
        # Configure necessary profile values for this specific test
        self.logger.log("Checking profile... ")
        try:
            self.check_profile() # equipment gets added to equipment in use
        except SDR_Test_Error as e:
            Error.error_out(self.logger, e)
        self.logger.logln("Done!")

        print("\nCHECKING EQUIPMENT IN USE (2):")
        print(self.equipment_in_use)

        # Initialize the desired equipment
        self.logger.logln("Initializing equipment...")
        self.logger.stepin()
        self.init_calibration_factors()
        print("\nCHECKING EQUIPMENT IN USE:")
        print(self.equipment_in_use)
        self.initialize_equipment()
        self.logger.stepout()

        # Ensure the dependency tests get the equipment
        self.logger.log("Extending equipment to dependency tests... ")
        self.extend_equipment_to_dependency_tests()
        self.logger.logln("Done!")

        # Flush the log right before the test starts
        self.logger.flush()

        # Run the actual test
        self.run_test()

        # Handle the cleanup
        self.cleanup()

        # Handle the saving of data
        self.save_data()

        # Delete the logger
        del self.logger

    """ Initialize the test and display welcome message """
    def initialize_test(self):
        self.start_time = time.time()
        self.logger.logln("~*~*~* {} *~*~*~".format(self.TEST_NAME))
        self.logger.logln()

    # Ensure that all dependency tests get the equipment and associated errors
    def extend_equipment_to_dependency_tests(self):
        for test_dependence in self.PROFILE_DEFINITIONS['required_tests']:
            getattr(self, test_dependence).equipment_in_use = self.equipment_in_use
            getattr(self, test_dependence).equipment_errors = self.equipment_errors
            getattr(self, test_dependence).beakout_equipment()
            getattr(self, test_dependence).extend_equipment_to_dependency_tests()

    # Makes the temporary additions to the profile, runs the dependency
    # test, then removes the profile additions
    def run_dependency_test(self, test, profile_adjustments, run_save_function=False, save_directory=False, revert_adjustments_after_completion=True):
        save_profile_params = {}
        for k, v in profile_adjustments.items():
            if self.profile_parameter_exists(k):
                save_profile_params[k] = self.profile_get_parameter(k)
            self.profile_set_parameter(k, v)
        test.run_test()
        if run_save_function:
            if not save_directory:
                save_directory = self.save_directory
            if not os.path.exists(save_directory):
                os.makedirs(save_directory)
            test.save_directory = save_directory
            test.sdr_serial_number = self.sdr_serial_number # Find better place to ripple this down
            test.save_data()
        if revert_adjustments_after_completion:
            for k in profile_adjustments:
                delattr(self.profile, k)
            for k, v in save_profile_params.items():
                self.profile_set_parameter(k, v)

    # Perform the general cleanup
    def cleanup(self):
        # Make sure to run power down procedures for all equipment
        for equip in self.equipment_in_use:
            self.logger.log("Powering down {}... ".format(equip))
            delattr(self, equip)
            self.logger.logln("Done!")

        # Calculate runtime
        self.logger.disable_quiet_mode()
        self.end_time = time.time()
        self.run_time = self.end_time - self.start_time
        self.logger.logln("Test completed in {}s!".format(self.run_time))

    """
        >>>
            CHAPTER 2: TEST PROFILE FUNCTIONS
        >>>
    """

    """ Merge the test specific profile definitions with the master version """
    def merge_profile_definitions(self):
        # Merge the required tests
        for rt in self.TEST_PROFILE_DEFINITIONS['required_tests']:
            if rt not in self.PROFILE_DEFINITIONS['required_tests']:
                self.PROFILE_DEFINITIONS['required_tests'].append(rt)
        
        # Merge the required profile parameters
        for rp in self.TEST_PROFILE_DEFINITIONS['required_profile_parameters']:
            if rp not in self.PROFILE_DEFINITIONS['required_profile_parameters']:
                self.PROFILE_DEFINITIONS['required_profile_parameters'].append(rp)
        
        # Merge the required equipment
        for re in self.TEST_PROFILE_DEFINITIONS['required_equipment']:
            if re not in self.PROFILE_DEFINITIONS['required_equipment']:
                self.PROFILE_DEFINITIONS['required_equipment'].append(re)
        
        # Merge the possible functionality
        for pf in self.TEST_PROFILE_DEFINITIONS['possible_functionality']:
            if pf not in self.PROFILE_DEFINITIONS['possible_functionality']:
                self.PROFILE_DEFINITIONS['possible_functionality'].append(pf)
        
        # Update the default dict
        for dk, dv in self.TEST_PROFILE_DEFINITIONS['profile_parameter_defaults'].items():
            self.PROFILE_DEFINITIONS['profile_parameter_defaults'][dk] = dv
        
        # Update the forced dict
        for fk, fv in self.TEST_PROFILE_DEFINITIONS['forced_profile_parameters'].items():
            self.PROFILE_DEFINITIONS['forced_profile_parameters'][fk] = fv

    """ Check the profile for errors 
    
    - adds the user-defined parameters from the measurement profile
    - overwrites user-defined parameters with forced profile parameters (defined in the test class) where applicable
    - fills in default parameter values for any parameters that have not already been set
    - adds required parameters for tests based on their functionality 
        - checks stimilus parameters for tests with 'apply_stimulus' in possible functionality 
        - checks power measurement parameters for tests with 'verify_power' in possible functionality

    """
    def check_profile(self):
        # Handle the special case of num_bins is overridden
        # by min_freq_resolution
        if (self.profile_parameter_exists('fft_minimum_frequency_resolution')
                and self.profile.fft_minimum_frequency_resolution > 0):
            self.profile.fft_number_of_bins = None

        # Add forced profile values
        f = self.PROFILE_DEFINITIONS['forced_profile_parameters']
        for k, v in f.items():
            self.profile_set_parameter(k, v)

        # Add in default values
        d = self.PROFILE_DEFINITIONS['profile_parameter_defaults']
        for k, v in d.items():
            if not self.profile_parameter_exists(k):
                self.profile_set_parameter(k, v)
        
        # Check test functionality and add parameters to definitions
        self.using_stimulus = False
        if 'apply_stimulus' in self.PROFILE_DEFINITIONS['possible_functionality']:
            self.check_stimulus_parameters()
        self.verifying_power = False
        if 'verify_power' in self.PROFILE_DEFINITIONS['possible_functionality']:
            self.check_power_verification_parameters()

        # Add forced profile values again to catch equipment parameters
        #f = self.PROFILE_DEFINITIONS['forced_profile_parameters']
        #for k, v in f.items():
        #    self.profile_set_parameter(k, v)

        # Add in default values again to catch equipment parameters
        #d = self.PROFILE_DEFINITIONS['profile_parameter_defaults']
        #for k, v in d.items():
        #    if not self.profile_parameter_exists(k):
        #        self.profile_set_parameter(k, v)

        # Add required parameters for each piece of equipment (defaults done
        # after loading equipment) and add to in_use dict
        # for passing to depency tests
        # print("EQUIPMENT IN USE IS", self.PROFILE_DEFINITIONS['required_equipment'])
        for equip in self.PROFILE_DEFINITIONS['required_equipment']:
            # print("SETTING UP EQUIPMENT IN SDR TEST CLASS,", equip)
            # If it already made it in, don't do it again
            if equip in self.equipment_in_use:
                continue
            # Merge the parameters
            equip_params = self.EQUIPMENT_PARAMETER_DEFINITIONS[equip]
            self.PROFILE_DEFINITIONS['required_profile_parameters'].extend(
                    equip_params['required_profile_parameters']
                )
            self.equipment_in_use[equip] = None

        # Ensure that all required parameters are set
        for p in self.PROFILE_DEFINITIONS['required_profile_parameters']:
            if not self.profile_parameter_exists(p):
                raise SDR_Test_Error(
                        10,
                        "Required profile parameter not set",
                        "This test requires a set profile parameter of " +
                        "'{}' in the profile file".format(p)
                    )

        # Load other tests as necessary
        for subtest in self.PROFILE_DEFINITIONS['required_tests']:
            try:
                subtest_script = "sdrcalibrator.lib.scripts.{}".format(subtest)
                subtest_class = utils.import_object(subtest_script, "SDR_Test")
                setattr(self, subtest, subtest_class(self.profile, logger=self.logger))
            except ImportError:
                ehead = "Could not find dependent test '{}'".format(subtest)
                ebody = "Please check that all built-in tests exist\r\n"
                ebody += "and download any missing one."
                err = SDR_Test_Error(11, ehead, ebody)
                Error.error_out_pre_logger(err)
            # Check the profile for the test dependancy
            getattr(self, subtest).check_profile()
    
    """ Check the multiple configurations for applying stimulus """
    # this function checks to make sure that test files have been configured with the appropriate parameters to run the specified tests
    def check_stimulus_parameters(self):
        self.using_stimulus = False
        if self.profile_parameter_exists('power_stimulus') and self.profile.power_stimulus is not None and self.profile.power_stimulus is not False:
            self.using_stimulus = True
            # Setup with a single CW input
            if self.profile.power_stimulus == 'single_cw':
                # Add the siggen to required equipment
                pd = self.PROFILE_DEFINITIONS
                if 'siggen' not in pd['required_equipment']:
                    pd['required_equipment'].append('siggen')
                    print("Added siggen to list of required equipment in check_stimulus parameters due to single_cw power stimulus")
                # Add power level to the required parameters
                if 'power_level' not in pd['required_profile_parameters']:
                    pd['required_profile_parameters'].append('power_level')
                    print("Added power_level to list of required profile parameters in check_stimulus parameters due to single_cw power stimulus")
                # Check how the power level will be conditioned
                if self.profile_parameter_exists('power_level_mode'):
                    # Check if a programmable attenuator will be used
                    if self.profile.power_level_mode == 'attenuator':
                        if 'atten' not in pd['required_equipment']:
                            pd['required_equipment'].append('atten')
                            print("Added attenuator to list of required equipment due to attenuated single c requirements")
                    else:
                        self.profile.power_level_mode = 'normal'
    
    """ Check the multiple configurations for verifying a power level """
    def check_power_verification_parameters(self):
        if self.profile_parameter_exists('power_verification') and self.profile.power_verification is not None and self.profile.power_verification is not False:
            self.verifying_power = True
            # Setup with a single CW input
            if self.profile.power_verification == 'power_meter':
                # Add the power meter and RF switch to the required equipment
                pd = self.PROFILE_DEFINITIONS
                if 'pwrmtr' not in pd['required_equipment']:
                    pd['required_equipment'].append('pwrmtr')
                if 'switch' not in pd['required_equipment']:
                    pd['required_equipment'].append('switch')
            if self.profile.power_verification == 'C20':
                pd = self.PROFILE_DEFINITIONS
                # Need the switch just for the calibration factors
                if 'switch' not in pd['required_equipment']:
                    pd['required_equipment'].append('switch')

    """ Check if a profile parameter exists based on a string key """
    def profile_parameter_exists(self, param):
        return hasattr(self.profile, param)

    """ Set a profile parameter based on a string key """
    def profile_set_parameter(self, param, val):
        setattr(self.profile, param, val)
    
    """ Get a profile parameter based on a string key """
    def profile_get_parameter(self, param):
        return getattr(self.profile, param)

    """ Add equipment defaults to the profile """
    def profile_add_equipment_defaults(self, equip):
        equip_params = self.EQUIPMENT_PARAMETER_DEFINITIONS[equip]
        for k in equip_params['defaultable_profile_parameters']:
            if not self.profile_parameter_exists(k):
                v = self.get_equipment_default_parameter(equip, k)
                self.profile_set_parameter(k, v)

    """ Get an equipment default profile parameter """
    def get_equipment_default_parameter(self, equip_str, param):
        equip = getattr(self, equip_str)
        key = param[:len(equip_str)] + '_DEFAULT' + param[len(equip_str):]
        key = key.upper()
        print("GETTING DEFAULT PARAMETERS FOR KEY", key)
        return getattr(equip, key)

    """ Check for defaulted profile parameters which rely on equipment settings """
    def check_dependent_defaulted_profile_parameters(self):
        # Set the f0 and CW offset to sampling_freq/4 by default
        if self.profile_parameter_exists('freq_offset_f0_and_cw'):
            if self.profile.freq_offset_f0_and_cw == 'DEFAULT':
                offset = -1*(self.profile.sdr_sampling_frequency/4)
                self.profile.freq_offset_f0_and_cw = offset

    """
        >>>
            CHAPTER 3: EQUIPMENT INITIALIZATION FUNCTIONS
        >>>
    """

    """ Break equipment out of the dict to reference as instance variables """
    def beakout_equipment(self):
        for k,v in self.equipment_in_use.items():
            setattr(self, k, v)
        for k,v in self.equipment_errors.items():
            setattr(self, k, v)

    """ Initialize all equipment defined in the profile """
    def initialize_equipment(self):

        # Check if data will be saved and create save directory if needed
        self.saving_data = False
        for k in self.profile.__dict__:
            if k.startswith('logging_save_') and getattr(self.profile, k):
                self.saving_data = True
                self.create_save_directory()
                self.logger.logln("Created save directory: '{}'".format(
                    self.save_directory))
                self.logger.log("Writing profile to file... ")
                self.write_profile_to_file()
                self.logger.logln("Done!")
                break

        # Configure the logger
        self.logger.logln("Configuring logger...")
        self.configure_logger()

        # Check for an SDR to initialize
        if 'sdr' in self.equipment_in_use:
            self.logger.logln("Initializing SDR...")
            try:
                sdr_module = "sdrcalibrator.lib.equipment.sdr.{}".format(self.profile.sdr_module)
                self.sdr = utils.import_object(sdr_module, "SDR")()
                sdr_err_module = "sdrcalibrator.lib.equipment.sdr.sdr_error"
                self.SDR_Error_Class = utils.import_object(sdr_err_module, "SDR_Error")
            except ImportError as e:
                raise e
                ehead = "Could not import equipment module"
                ebody = "Module for sdr '{}'".format(self.profile.sdr_module)
                ebody += " could not be found.\r\nDid you remember to run '"
                ebody += "source ~/uhd_gnu_radio/setup_env.sh'"
                err = SDR_Test_Error(12, ehead, ebody)
                Error.error_out(self.logger, err)
            self.profile_add_equipment_defaults('sdr')
            try:
                self.initialize_sdr()
            except self.SDR_Error_Class as e:
                Error.error_out(self.logger, e)
            self.equipment_in_use['sdr'] = self.sdr
            self.equipment_errors['SDR_Error_Class'] = self.SDR_Error_Class

            

        # Check for a signal generator to initialize
        if 'siggen' in self.equipment_in_use:
            self.logger.logln("Initializing signal generator...")
            try:
                siggen_module = "sdrcalibrator.lib.equipment.siggen.{}".format(self.profile.siggen_module)
                self.siggen = utils.import_object(siggen_module, "Signal_Generator")()
                siggen_err_module = "sdrcalibrator.lib.equipment.siggen.siggen_error"
                self.Signal_Generator_Error_Class = utils.import_object(siggen_err_module, "Signal_Generator_Error")
            except ImportError as e:
                raise e
                ehead = "Could not import equipment module"
                ebody = "Module for siggen '{}'".format(self.profile.siggen_module)
                ebody += " could not be found."
                err = SDR_Test_Error(12, ehead, ebody)
                Error.error_out(self.logger, err)
            self.profile_add_equipment_defaults('siggen')
            try:
                self.initialize_siggen()
            except self.Signal_Generator_Error_Class as e:
                Error.error_out(self.logger, e)
            self.equipment_in_use['siggen'] = self.siggen
            self.equipment_errors['Signal_Generator_Error_Class'] = self.Signal_Generator_Error_Class

        # Check for a power meter to initialize
        if 'pwrmtr' in self.equipment_in_use:
            self.logger.logln("Initializing power meter...")
            try:
                pwrmtr_module = "sdrcalibrator.lib.equipment.pwrmtr.{}".format(self.profile.pwrmtr_module)
                self.pwrmtr = utils.import_object(pwrmtr_module, "Power_Meter")()
                pwrmtr_err_module = "sdrcalibrator.lib.equipment.pwrmtr.pwrmtr_error"
                self.Power_Meter_Error_Class = utils.import_object(pwrmtr_err_module, "Power_Meter_Error")
            except ImportError as e:
                print(e)
                ehead = "Could not import equipment module"
                ebody = "Module for pwrmtr '{}'".format(self.profile.pwrmtr_module)
                ebody += " could not be found."
                err = SDR_Test_Error(12, ehead, ebody)
                Error.error_out(self.logger, err)
            self.profile_add_equipment_defaults('pwrmtr')
            try:
                self.initialize_pwrmtr()
            except self.Power_Meter_Error_Class as e:
                Error.error_out(self.logger, e)
            self.equipment_in_use['pwrmtr'] = self.pwrmtr
            self.equipment_errors['Power_Meter_Error_Class'] = self.Power_Meter_Error_Class

        # Check for an RF switch to initialize
        if 'switch' in self.equipment_in_use:
            self.logger.logln("Initializing RF switch...")
            try:
                switch_module = "sdrcalibrator.lib.equipment.switch.{}".format(self.profile.switch_module)
                self.switch = utils.import_object(switch_module, "RF_Switch")()
                switch_err_module = "sdrcalibrator.lib.equipment.switch.switch_error"
                self.RF_Switch_Error_Class = utils.import_object(switch_err_module, "RF_Switch_Error")
            except ImportError as e:
                ehead = "Could not import equipment module"
                ebody = "Module for switch '{}'".format(self.profile.switch_module)
                ebody += " could not be found.\r\n"
                ebody += str(e)
                err = SDR_Test_Error(12, ehead, ebody)
                Error.error_out(self.logger, err)
            self.profile_add_equipment_defaults('switch')
            try:
                self.initialize_switch()
            except self.RF_Switch_Error_Class as e:
                Error.error_out(self.logger, e)
            self.equipment_in_use['switch'] = self.switch
            self.equipment_errors['RF_Switch_Error_Class'] = self.RF_Switch_Error_Class
        
        # Check for programmable attenuator to initialize
        if 'atten' in self.equipment_in_use:
            self.logger.logln("Initializing programmable attenuator...")
            try:
                atten_module = "sdrcalibrator.lib.equipment.atten.{}".format(self.profile.atten_module)
                self.atten = utils.import_object(atten_module, "Programmable_Attenuator")()
                atten_err_module = "sdrcalibrator.lib.equipment.atten.atten_error"
                self.Programmable_Attenuator_Error_Class = utils.import_object(atten_err_module, "Programmable_Attenuator_Error")
            except ImportError:
                ehead = "Could not import equipment module"
                ebody = "Module for attenuator '{}'".format(self.profile.atten_module)
                ebody += " could not be found."
                err = SDR_Test_Error(12, ehead, ebody)
                Error.error_out(self.logger, err)
            self.profile_add_equipment_defaults('atten')
            try:
                self.initialize_atten()
            except self.Programmable_Attenuator_Error_Class as e:
                Error.error_out(self.logger, e)
            self.equipment_in_use['atten'] = self.atten
            self.equipment_errors['Programmable_Attenuator_Error_Class'] = self.Programmable_Attenuator_Error_Class

        # Check for defaulted parameters which relied on equipment settings
        self.logger.log(
                "Checking defaulted parameters which rely on " +
                "equipment settings... "
            )
        self.check_dependent_defaulted_profile_parameters()
        self.logger.logln("Done!")

    """ Configure the logger """
    def configure_logger(self):
        self.logger.stepin()
        if self.profile.logging_quiet_mode:
            self.logger.log("Proceeding in quiet mode...")
            self.logger.enable_quiet_mode()
            self.logger.logln("Done!")
        if self.profile.logging_save_log_file:
            self.logger.log("Generating log file...")
            self.logger.define_log_file(self.save_file("log.txt"))
            self.logger.logln("Done!")
        else:
            self.logger.log("Disabling logging to file...")
            self.logger.disable_log_to_file()
            self.logger.logln("Done!")
        self.logger.stepout()

    # Verbosely initialize the SDR
    def initialize_sdr(self):
        self.logger.stepin()

        # Connect to the SDR
        self.logger.logln("SDR should be of type '{}'...".format(
            self.sdr.SDR_NAME))
        self.logger.log("Connecting to SDR... ")
        self.sdr.connect(self.profile.sdr_connect_params)
        self.logger.logln("Done!")
        self.logger.stepin()
        self.sdr_serial_number = self.sdr.get_serial_number()
        self.logger.logln("SDR serial number: \"{}\"".format(self.sdr_serial_number))
        self.logger.stepout()

        # Set the clock frequency
        self.logger.log("SDR clock frequency will be set to {}... ".format(
            self.logger.to_MHz(self.profile.sdr_clock_frequency)))
        self.sdr.set_clock_frequency(self.profile.sdr_clock_frequency)
        self.logger.logln("Done!")

        # Set the sampling frequency
        self.logger.log("SDR sampling frequency will be set to {}... ".format(
            self.logger.to_MHz(self.profile.sdr_sampling_frequency)))
        self.sdr.set_sampling_frequency(self.profile.sdr_sampling_frequency)
        self.logger.logln("Done!")

        # Check for DC offset correction
        self.logger.log("Setting auto DC offset correction to {}... ".format(
            self.profile.sdr_auto_dc_offset))
        self.sdr.set_auto_dc_offset(self.profile.sdr_auto_dc_offset)
        self.logger.logln("Done!")

        # Check for IQ imbalance correction
        self.logger.log("Setting auto IQ balance correction to {}... ".format(
            self.profile.sdr_auto_iq_imbalance))
        self.sdr.set_auto_iq_imbalance(self.profile.sdr_auto_iq_imbalance)
        self.logger.logln("Done!")

        # Check for SDR gain
        self.logger.log("Setting SDR gain to {}... ".format(
            self.logger.to_dBm(self.profile.sdr_gain)))
        self.sdr.set_gain(self.profile.sdr_gain)
        self.logger.logln("Done!")

        # Check for LO tuning error threshold
        self.sdr.configure_f0_tuning_threshold(
            self.profile.sdr_f0_tuning_error_threshold)
        t = self.logger.to_MHz(self.profile.sdr_f0_tuning_error_threshold)
        self.logger.logln(
            "Center frequency tuning error threshold: {}...".format(t))

        # Set the DSP local oscillator shift if needed
        if self.profile.sdr_use_dsp_lo_shift:
            self.logger.log("Setting DSP LO shift to {}... ".format(
                self.logger.to_MHz(self.profile.sdr_dsp_lo_shift)))
            self.sdr.set_dsp_lo_shift(self.profile.sdr_dsp_lo_shift)
            self.logger.logln("Done!")
        else:
            self.logger.log("Disabling DSP LO shifting...")
            self.sdr.set_dsp_lo_shift(0)
            self.logger.logln("Done!")
        
        # Determine scale factor configuration
        self.sdr.scale_factors = None
        if self.profile.sdr_power_scale_factor is not None:
            self.logger.logln("SDR scale factor set to {} for all frequencies...".format(
                self.logger.to_dBm(self.profile.sdr_power_scale_factor)))
        elif self.profile.sdr_power_scale_factor_file:
            self.logger.log("Loading SDR scale factors from file... ")
            self.load_scaling_factor_file(self.profile.sdr_power_scale_factor_file)
            self.logger.logln("Done!")
        else:
            self.logger.logln("Defaulting to scale factor of 0dBm for all frequencies...")
            self.profile.sdr_power_scale_factor = 0
        
        # Copy over the calibration file
        if self.sdr.scale_factors is not None and self.saving_data:
            self.logger.log("Copying calibration data to output directory... ")
            #self.write_scale_factor_file('scale.factors.csv')
            self.write_calibration_file('calibration_file.json', src_file=self.profile.sdr_power_scale_factor_file)
            self.logger.logln("Done!")

        self.logger.stepout()
        return

    """ Verbosely initialize the signal generator """
    def initialize_siggen(self):
        self.logger.stepin()

        # Connect to the signal generator
        self.logger.logln("Signal generator should be of type '{}'...".format(
            self.siggen.SIGGEN_NAME))
        self.logger.log("Connecting to signal generator... ")
        self.siggen.connect(self.profile.siggen_connect_params)
        self.logger.logln("Done!")

        # Check for a settling time for the signal generator
        self.siggen.configure_rf_on_settling_time(
            self.profile.siggen_rf_on_settling_time)
        self.siggen.configure_rf_off_settling_time(
            self.profile.siggen_rf_off_settling_time)
        self.logger.logln(
                "Signal generator on/off settling times set to " +
                "{}s/{}s".format(
                    self.profile.siggen_rf_on_settling_time,
                    self.profile.siggen_rf_off_settling_time
                )
            )

        self.logger.stepout()
        return

    # Verbosely initialize the power meter
    def initialize_pwrmtr(self):
        self.logger.stepin()

        # Determine the type of power meter
        self.logger.logln("Power meter should be of type '{}'...".format(
                self.pwrmtr.PWRMTR_NAME)
            )

        # Check if we need to ask which equipment to connect to
        remove_equipment_ID = False
        if ('ask_which_instrument' in self.profile.pwrmtr_connect_params and
                self.profile.pwrmtr_connect_params['ask_which_instrument']):
            # Query the power meter for a list of connected equipment
            self.logger.log("Asking for equipment options... ")
            equipment_options = self.pwrmtr.query_equipment_options()
            self.logger.logln("Done!")

            # Display the options for the user to choose
            self.logger.logln(
                    "Please choose which equipment is the correct power meter:"
                )
            self.logger.stepin()
            for i in range(len(equipment_options)):
                self.logger.logln("{}: {}".format(i, equipment_options[i]))
            self.logger.stepin()
            equipment_id = int(self.logger.query("Enter equipment ID: "))
            self.logger.stepout(step_out_num=2)

            # Add the equipment ID to the connect parameters and trigger it
            # to be removed after connection
            self.profile.pwrmtr_connect_params['equipment_id'] = equipment_id
            remove_equipment_ID = True

        # Connect to the power meter
        self.logger.log("Connecting to power meter... ")
        self.pwrmtr.connect(self.profile.pwrmtr_connect_params)
        self.logger.logln("Done!")

        # Remove the equipment id if the user chose it
        # (preserves the user select when the profile is written)
        if remove_equipment_ID:
            del self.profile.pwrmtr_connect_params['equipment_id']

        self.logger.stepout()

        return

    # Verbosely initialize the RF switch
    def initialize_switch(self):
        self.logger.stepin()

        # Determine the type of RF switch
        self.logger.logln("RF switch should be of type '{}'...".format(
                self.switch.SWITCH_NAME
            ))

        # Connect to the switch
        self.logger.log("Connecting to RF switch... ")
        self.switch.connect(
                self.profile.switch_connect_params,
                self.profile.switch_swap_inputs
            )
        self.logger.logln("Done!")

        # Set the switch to its default state
        self.logger.log("Setting RF switch to its default state... ")
        self.switch.set_to_default()
        self.logger.logln("Done!")

        # # Load the correction factors if needed
        #     # TODO: change this to load a power_correction_factor_file
        #     # move it to initialize power not initialize switch
        #     # make default case for if there's no correction factor file
        # self.switch.calibrated = False
        # if self.profile.switch_correction_factor_file is not None:
        #     self.logger.log("Loading switch correction factors... ")
        #     self.load_setup_correction_factor_file(self.profile.switch_correction_factor_file)
        #     self.logger.logln("Done!")
        #     self.switch.calibrated = True
        # else:
        #     self.logger.logln("No calibration data for switch provided...")

        self.logger.stepout()
        return
    
    # Verbosely initialize the programmable attenuator
    def initialize_atten(self):
        self.logger.stepin()

        # Connect to the programmable attenuator
        self.logger.logln("Programmable attenuator should be of type '{}'...".format(
            self.atten.ATTEN_NAME))
        self.logger.log("Connecting to programmable attenuator... ")
        self.atten.connect(self.profile.atten_connect_params)
        self.logger.logln("Done!")

        # Set the settling time for the attenuator
        self.logger.log("Setting attenuator settling time to {}s...".format(self.profile.atten_settling_time))
        self.atten.set_settling_time(self.profile.atten_settling_time)
        self.logger.logln("Done!")

        # Setup the attenuator according to the params
        self.logger.log("Setting up attenuator... ")
        self.atten.setup(self.profile.atten_setup_params)
        self.logger.logln("Done!")

        self.logger.stepout()
        return
    
    """
        >>>
            CHAPTER 3.5: NON-SDR EQUIPMENT SPECIFIC FUNCTIONS
        >>>
    """

    """ Generate a rf switch correction factor matrix from a file """
    def load_setup_correction_factor_file(self, fname):
        self.setup_correction_factors = {}

        # If the scale factor file is a generated JSON file
        if fname.lower().endswith(".json"):
            cal_data = {}
            with open(fname, 'r+') as f:
                cal_data = json.load(f)
                f.close()
            # Load all the calibration points
            for pt in cal_data['rf_test_setup_calibration_points']:
                f = pt['frequency']
                self.setup_correction_factors[f] = pt
        else:
            ehead = 'Calibration files must be JSON'
            ebody = (
                "The calibration file/s, including correction factor files can no longer\r\n" +
                "be in CSV format. Instead they must be in JSON format. Please rerun\r\n" +
                "the rf_switch_cal test to generate a JSON calibration file."
            )
            err = SDR_Test_Error(10, ehead, ebody)
            Error.error_out(self.logger, err)

    """ Calculate the correction factor from current setup """
    def calculate_setup_correction_factor(self, f, setup_factor_type='C23'):
        self.logger.logln("Calculating setup correction factor...")
        self.logger.stepin()

        # Get the CW frequency and its index
        f_i = -1
        bypass_freq_interpolation = True
        fs = sorted(self.setup_correction_factors.keys())
        if f < fs[0]:
            self.logger.logln("CW frequency is below calibration range.")
            self.logger.logln("Assuming correction factor of lowest frequency.")
            self.logger.stepin()
            self.logger.logln("Actual f:  {}".format(self.logger.to_MHz(f)))
            self.logger.logln("Assumed f: {}".format(self.logger.to_MHz(fs[0])))
            self.logger.stepout()
            f_i = 0
        elif f > fs[-1]:
            self.logger.logln("CW frequency is above calibration range.")
            self.logger.logln("Assuming correction factor of highest frequency.")
            self.logger.stepin()
            self.logger.logln("Actual f:  {}".format(self.logger.to_MHz(f)))
            self.logger.logln("Assumed f: {}".format(self.logger.to_MHz(fs[-1])))
            self.logger.stepout()
            f_i = len(fs)-1
        else:
            # Ensure we do interpolation for frequency
            bypass_freq_interpolation = False
            # Determine the index associated with the closest frequency less than or equal to f_lo
            for i in range(len(fs)-1):
                f_i = i
                # If the next frequency is larger, we're done
                if fs[i+1] > f:
                    break

        # Interpolate as needed
        if bypass_freq_interpolation:
            self.setup_correction_factor = self.setup_correction_factors[fs[f_i]][setup_factor_type]
        else:
            self.setup_correction_factor = utils.interpolate_1d(
                f,
                fs[f_i],
                fs[f_i+1],
                self.setup_correction_factors[fs[f_i]][setup_factor_type],
                self.setup_correction_factors[fs[f_i+1]][setup_factor_type]
            )
        
        # Check if the inputs are swapped
        # if self.profile.switch_swap_inputs:
        #     self.setup_correction_factor *= -1

        # Log the calculated correction factor and return the result
        self.logger.logln("Correction factor: {}".format(self.logger.to_dBm(self.setup_correction_factor)))
        self.logger.stepout()
        return self.setup_correction_factor
    
    """
        >>>
            CHAPTER 4: SDR SPECIFIC FUNCTIONS
        >>>
    """

    """ Generate a scaling factor matrix from a file """
    def load_scaling_factor_file(self, fname):
        self.sdr.scale_factors = {}

        # If the scale factor file is a generated JSON file
        if fname.lower().endswith(".json"):
            cal_data = {}
            with open(fname, 'r+') as f:
                cal_data = json.load(f)
                f.close()
            # Load the frequency divisions
            self.sdr.scale_factor_frequency_divisions = cal_data['calibration_frequency_divisions']
            # Load the calibrated SR/CR pairs
            self.sdr.calibrated_sample_clock_rates = {}
            for srcr_pair in cal_data['clock_rate_lookup_by_sample_rate']:
                self.sdr.calibrated_sample_clock_rates[srcr_pair['sample_rate']] = srcr_pair['clock_frequency']
            # Load all the calibration data
            for sample_rate_row in cal_data['calibration_data']['sample_rates']:
                sr = sample_rate_row['sample_rate']
                for frequency_row in sample_rate_row['calibration_data']['frequencies']:
                    f = frequency_row['frequency']
                    for gain_row in frequency_row['calibration_data']['gains']:
                        g = gain_row['gain']
                        cal_point = gain_row['calibration_data']

                        # Make sure the dicts are feshed out
                        if sr not in self.sdr.scale_factors.keys():
                            self.sdr.scale_factors[sr] = {}
                        if f not in self.sdr.scale_factors[sr].keys():
                            self.sdr.scale_factors[sr][f] = {}
                        self.sdr.scale_factors[sr][f][g] = -1*cal_point['gain_sigan']
            """
            for pt in cal_data['calibration_points']:
                sr = pt['sample_rate_sigan']
                f = pt['freq_sigan']
                g = pt['gain_sigan']
                # Make sure the dicts are fleshed out
                if sr not in self.sdr.scale_factors.keys():
                    self.sdr.scale_factors[sr] = {}
                if f not in self.sdr.scale_factors[sr].keys():
                    self.sdr.scale_factors[sr][f] = {}
                self.sdr.scale_factors[sr][f][g] = pt['scale_factor']
            """
        else:
            ehead = 'Calibration files must be JSON'
            ebody = (
                "The calibration file/s, including scale factor files can no longer\r\n" +
                "be in CSV format. Instead they must be in JSON format. Please rerun\r\n" +
                "the calibration test to generate a JSON calibration file."
            )
            err = SDR_Test_Error(10, ehead, ebody)
            Error.error_out(self.logger, err)
            # Cannot get here, saving to ensure the calculation is still correct
            """ PRESERVED FOR REFERENCE
            with open(fname, 'rb') as f:
                reader = csv.reader(f, delimiter=',')
                for row in reader:
                    # Check for a division row
                    if row[0] == 'div':
                        self.sdr.scale_factor_divisions.append([float(row[1]),float(row[2])])
                        continue
                    # Check for list of gains
                    if row[0] == '':
                        for i in range(len(row)-1):
                            self.sdr.scale_factor_gains.append(float(row[i+1]))
                        continue
                    # Row must be a frequency row
                    self.sdr.scale_factor_frequencies.append(float(row[0]))
                    self.sdr.scale_factors.append([])
                    for i in range(len(row)-1):
                        self.sdr.scale_factors[-1].append(float(row[i+1]))
                f.close()
            #Sort frequencies in order
            self.sdr.scale_factors,self.sdr.scale_factor_gains,self.sdr.scale_factor_frequencies = utils.sort_matrix_by_lists(self.sdr.scale_factors,self.sdr.scale_factor_gains,self.sdr.scale_factor_frequencies)
            """

    """ Tune the SDR and load the scaling factor """
    def tune_sdr_to_frequency(self,f0):
        # Tune the SDR and get back the LO
        self.logger.logln("Tuning SDR to {}... ".format(
            self.logger.to_MHz(f0)))
        try:
            actual_f0 = self.sdr.tune_to_frequency(f0)
        except self.SDR_Error_Class as e:
            Error.error_out(self.logger, e)
        f_lo = self.sdr.current_lo_frequency()
        f_dsp = self.sdr.current_dsp_frequency()

        # Log tuning result for record keeping and return the actual freq
        self.logger.stepin()
        self.logger.logln("Requested f0:  {}".format(self.logger.to_MHz(f0)))
        self.logger.logln("Actual f0:     {}".format(self.logger.to_MHz(actual_f0)))
        self.logger.logln("LO frequency:  {}".format(self.logger.to_MHz(f_lo)))
        self.logger.logln("DSP frequency: {}".format(self.logger.to_MHz(f_dsp)))
        self.logger.stepout()
        return actual_f0

    """ Calculate the power scale factor from current setup """
    def calculate_scale_factor(self):
        self.logger.logln("Calculating scale factor...")
        self.logger.stepin()
        # Catch a forced scale factor in the profile
        if self.profile.sdr_power_scale_factor is not None:
            self.sdr.scale_factor = self.profile.sdr_power_scale_factor
        else:
            # Get the sampling rate index for the scale factor
            srs = self.sdr.scale_factors.keys()
            sr = int(self.sdr.get_sampling_frequency())
            cr = int(self.sdr.get_clock_frequency())
            if sr not in srs:
                self.logger.logln("Actual sampling rate was not a calibration point.")
                self.logger.logln("Assuming calibration for first sample rate.")
                self.logger.stepin()
                self.logger.logln("Actual SR:  {}".format(self.logger.to_MHz(sr)))
                self.logger.logln("Assumed SR: {}".format(self.logger.to_MHz(srs[0])))
                self.logger.stepout()
                sr = srs[0]
            else:
                # Check if the sample and clock rate match
                if not self.sdr.calibrated_sample_clock_rates[sr] == cr:
                    self.logger.logln("Current clock frequency does not match calibrated clock frequency.")
                    self.logger.logln("Assuming calibration for calibrated clock frequency.")
                    self.logger.stepin()
                    self.logger.logln("Actual CR:  {}".format(self.logger.to_MHz(cr)))
                    self.logger.logln("Assumed CR: {}".format(self.logger.to_MHz(self.sdr.calibrated_sample_clock_rates[sr])))
                    self.logger.stepout()

            # Get the SDR frequency  and its index
            f_lo = self.sdr.current_lo_frequency()
            f_i = -1
            bypass_freq_interpolation = True
            fs = sorted(self.sdr.scale_factors[sr].keys())
            if f_lo < fs[0]:
                self.logger.logln("Tuned frequency is below calibration range.")
                self.logger.logln("Assuming scale factor of lowest frequency.")
                self.logger.stepin()
                self.logger.logln("Actual LO:  {}".format(self.logger.to_MHz(f_lo)))
                self.logger.logln("Assumed LO: {}".format(self.logger.to_MHz(fs[0])))
                self.logger.stepout()
                f_i = 0
            elif f_lo > fs[-1]:
                self.logger.logln("Tuned frequency is above calibration range.")
                self.logger.logln("Assuming scale factor of highest frequency.")
                self.logger.stepin()
                self.logger.logln("Actual LO:  {}".format(self.logger.to_MHz(f_lo)))
                self.logger.logln("Assumed LO: {}".format(self.logger.to_MHz(fs[-1])))
                self.logger.stepout()
                f_i = len(fs)-1
            else:
                # Ensure we do interpolation for frequency
                bypass_freq_interpolation = False
                # Check if we are in a division
                for div in self.sdr.scale_factor_frequency_divisions:
                    if f_lo > div['lower_bound'] and f_lo < div['upper_bound']:
                        self.logger.logln("Tuned frequency is within a frequency division.")
                        self.logger.logln("Assuming scale factor of lower bound.")
                        self.logger.stepin()
                        self.logger.logln("Division: [ {} , {} ]".format(self.logger.to_MHz(div['lower_bound']),self.logger.to_MHz(div['upper_bound'])))
                        self.logger.logln("Actual LO:  {}".format(self.logger.to_MHz(f_lo)))
                        self.logger.logln("Assumed LO: {}".format(self.logger.to_MHz(div['lower_bound'])))
                        self.logger.stepout()
                        f_lo = div['lower_bound'] # Interpolation will force this point; no interpolation error
                # Determine the index associated with the closest frequency less than or equal to f_lo
                for i in range(len(fs)-1):
                    f_i = i
                    # If the next frequency is larger, we're done
                    if fs[i+1] > f_lo:
                        break
            
            # Get the SDR gain and its index in the matrix
            g = self.sdr.get_gain()
            gs = sorted(self.sdr.scale_factors[sr][fs[f_i]].keys())
            g_i = 0
            g_fudge = 0
            bypass_gain_interpolation = True
            if g < gs[0]:
                self.logger.logln("Tuned gain is below calibration range.")
                self.logger.logln("Assuming scale factor of lowest gain with fudge factor.")
                self.logger.stepin()
                self.logger.logln("Actual gain:       {}".format(self.logger.to_dBm(g)))
                self.logger.logln("Assumed gain:      {}".format(self.logger.to_dBm(gs[0])))
                self.logger.logln("Gain fudge factor: {}".format(self.logger.to_dBm(gs[0]-g)))
                self.logger.stepout()
                g_i = 0
                g_fudge = gs[0]-g
            elif g > gs[-1]:
                self.logger.logln("Tuned gain is above calibration range.")
                self.logger.logln("Assuming scale factor of highest gain with fudge factor.")
                self.logger.stepin()
                self.logger.logln("Actual gain:       {}".format(self.logger.to_dBm(g)))
                self.logger.logln("Assumed gain:      {}".format(self.logger.to_dBm(gs[-1])))
                self.logger.logln("Gain fudge factor: {}".format(self.logger.to_dBm(gs[-1]-g)))
                self.logger.stepout()
                g_i = len(gs)-1
                g_fudge = gs[-1]-g
            else:
                # Ensure we do interpolation for gain
                bypass_gain_interpolation = False
                # Determine the index associated with the closest frequency less than or equal to f_lo
                for i in range(len(gs)-1):
                    g_i = i
                    # If the next gain is larger, we're done
                    if gs[i+1] > g:
                        break

            # Interpolate as needed
            if bypass_gain_interpolation and bypass_freq_interpolation:
                self.sdr.scale_factor = self.sdr.scale_factors[sr][fs[f_i]][gs[g_i]]
            elif bypass_freq_interpolation:
                self.sdr.scale_factor = utils.interpolate_1d(
                    g,
                    gs[g_i],
                    gs[g_i+1],
                    self.sdr.scale_factors[sr][fs[f_i]][gs[g_i]],
                    self.sdr.scale_factors[sr][fs[f_i]][gs[g_i+1]]
                )
            elif bypass_gain_interpolation:
                self.sdr.scale_factor = utils.interpolate_1d(
                    f_lo,
                    fs[f_i],
                    fs[f_i+1],
                    self.sdr.scale_factors[sr][fs[f_i]][gs[g_i]],
                    self.sdr.scale_factors[sr][fs[f_i+1]][gs[g_i]]
                )
            else:
                self.sdr.scale_factor = utils.interpolate_2d(
                    f_lo,
                    g,
                    fs[f_i],
                    fs[f_i+1],
                    gs[g_i],
                    gs[g_i+1],
                    self.sdr.scale_factors[sr][fs[f_i]][gs[g_i]],
                    self.sdr.scale_factors[sr][fs[f_i+1]][gs[g_i]],
                    self.sdr.scale_factors[sr][fs[f_i]][gs[g_i+1]],
                    self.sdr.scale_factors[sr][fs[f_i+1]][gs[g_i+1]]
                )
            # Apply the gain fudge factor if needed
            self.sdr.scale_factor += g_fudge

        # Log the calculated scale factor and return the result
        self.logger.logln("Scale factor: {}".format(self.logger.to_dBm(self.sdr.scale_factor)))
        self.logger.stepout()
        return self.sdr.scale_factor
    
    """ Acquire samples from the SDR and scale them """
    def acquire_samples(self, num):
        # Get the samples
        self.logger.log(
            "Reading {} samples after {} conditioning samples...".format(
                    num, self.profile.sdr_conditioning_samples))
        # print("CALLING TAKE IQ SAMPLES FOR SDR =", self.sdr) # TODO: remove this
        data = self.sdr.take_iq_samples(
                num, self.profile.sdr_conditioning_samples)
        self.logger.logln("Done!")

        # Scale the samples with the loaded scale factor
        if not (self.sdr.scale_factor == 0):
            self.logger.log("Scaling IQ data with defined scale factor... ")
            data = self.scale_iq_data_with_power_factor(data, self.sdr.scale_factor)
            self.logger.logln("Done!")

        return data
    
    """ Set the gain of the SDR """
    def set_sdr_gain(self, g):
        try:
            self.sdr.set_gain(g)
        except self.SDR_Error_Class as e:
            Error.error_out(self.logger, e)
    
    """
        >>>
            CHAPTER 5: STIMULUS SPECIFIC FUNCTIONS
        >>>
    """

    """ Load necessary parameters for the stimulus """
    def setup_stimulus(self, f0, p_in):
        if not self.using_stimulus:
            return
        # Setup the siggen for a single CW for calibrating other equipment
        if self.profile.power_stimulus == 'single_cw_for_calibration':
            self.logger.logln("Setting up CW from signal generator...")
            self.logger.stepin()

            # Tune the signal generator to the correct frequency
            self.logger.log("Tuning signal generator to {}... ".format(
                    self.logger.to_MHz(f0)
                ))
            self.siggen.tune_to_frequency(f0)
            self.logger.logln("Done!")

            # Set the output power for the signal generator
            self.logger.log(
                "Setting signal generator output power to {}... ".format(
                    self.logger.to_dBm(p_in)
                ))
            self.siggen.set_power(p_in)
            self.logger.logln("Done!")
            self.logger.stepout()
            return
        # Compute and setup the siggen for a single CW
        if self.profile.power_stimulus == 'single_cw':
            self.logger.logln("Setting up CW from signal generator...")
            self.logger.stepin()

            # Compute the frequencies with offsets
            self.logger.log("Computing f0 and CW frequencies...")
            f0, cw = self.compute_freqs_with_offset(f0)
            self.logger.logln("Done")
            self.logger.logln("SDR center frequency will be set to: {}".format(
                self.logger.to_MHz(f0)))
            self.logger.logln("Signal generator CW will be set to: {}".format(
                self.logger.to_MHz(cw)))
            self.f_cw = cw

            # Compute the output power for the siggen
            self.logger.log("Computing output power for the CW signal...")
            try:
                gain = self.sdr.get_gain()
                self.p_in = self.profile.power_level
                if self.profile.power_scale_cw_power_with_sdr_gain:
                    self.p_in -= gain
                if (self.profile.power_limit_output_power and
                        self.p_in+gain > self.profile.sdr_power_limit):
                    ehead = "Requested power exceeds the set power limit"
                    ebody = "Requested power {}\r\n".format(self.logger.to_dBm(self.p_in))
                    ebody += "Power with SDR gain: {}\r\n".format(self.logger.to_dBm(self.p_in+gain))
                    ebody += "Power limit {}".format(self.logger.to_dBm(self.profile.sdr_power_limit))
                    raise SDR_Test_Error(30, ehead, ebody)
                self.p_out = self.p_in + self.profile.power_inline_attenuator
            except SDR_Test_Error as e:
                Error.error_out(self.logger, e)
            self.logger.logln("Done!")
            
            # If using the attenuator to control power, set that up
            if self.profile.power_level_mode == 'attenuator':
                desired_atten = self.profile.power_base_power - self.p_out
                left_over_atten = self.atten.set_attenuation(desired_atten,self.f_cw)
                self.attenuation = desired_atten-left_over_atten
                self.p_out = self.profile.power_base_power - left_over_atten
                self.logger.logln(
                    "Programmable attenuator level set to: {}".format(
                            self.logger.to_dBm(self.attenuation)
                        )
                    )
            # Log the approximate power levels
            self.logger.logln(
                "Signal generator CW output power will be set to: {}".format(
                        self.logger.to_dBm(self.p_out)
                    )
                )
            self.logger.logln(
                "Approximate power at SDR input will be: {}".format(
                        self.logger.to_dBm(self.p_in)
                    )
                )
            
            # Configure the signal generator with calculated parameters
            self.logger.logln("Configuring signal generator...")
            self.logger.stepin()

            # Tune the signal generator to the correct frequency
            self.logger.log("Tuning signal generator to {}... ".format(
                    self.logger.to_MHz(self.f_cw)
                ))
            self.siggen.tune_to_frequency(self.f_cw)
            self.logger.logln("Done!")

            # Set the output power for the signal generator
            self.logger.log(
                "Setting signal generator output power to {}... ".format(
                    self.logger.to_dBm(self.p_out)
                ))
            self.siggen.set_power(self.p_out)
            self.logger.logln("Done!")

            # Perform power verification if required
            if self.verifying_power:
                self.logger.logln("Verifying power output...")
                self.logger.stepin()

                # Perform power verification with power meter
                if self.profile.power_verification == 'power_meter':

                    # Tune the power meter to the CW frequency
                    self.logger.log("Tuning power meter to {}... ".format(self.logger.to_MHz(self.f_cw)))
                    self.pwrmtr.tune_to_frequency(self.f_cw)
                    self.logger.logln("Done!")

                    # Turn the switch to the power meter
                    self.logger.log("Turning switch to the power meter... ")
                    self.switch.select_meter()
                    self.logger.logln("Done!")

                    # Turn on the power
                    self.stimulus_on()

                    # Measure the power with the power meter
                    self.logger.log("Measuring power with the power meter... ")
                    self.measured_power = self.pwrmtr.take_measurement(self.p_out)
                    self.logger.logln("Done!")
                    self.logger.stepin()
                    self.logger.logln("Measured power: {}".format(self.logger.to_dBm(self.measured_power)))
                    self.logger.stepout()

                    # If using correction factors for the switch, apply them
                    if self.switch.calibrated:
                        self.calculate_setup_correction_factor(self.f_cw)
                        self.logger.stepin()
                        self.measured_power += self.setup_correction_factor
                        self.logger.logln("Setup correction factor: {}".format(self.logger.to_dBm(self.setup_correction_factor)))
                        self.logger.logln("Corrected measured power: {}".format(self.logger.to_dBm(self.measured_power)))
                        self.logger.stepout()

                    # Turn on the power
                    self.stimulus_off()

                    # Turn the switch to the power meter
                    self.logger.log("Turning switch to the SDR... ")
                    self.switch.select_sdr()
                    self.logger.logln("Done!")

                    # Calculate the measured power
                    if self.profile.power_level_mode == 'attenuator':
                        self.measured_power -= self.attenuation
                        self.logger.logln("Power after the attenuator taken to be: {}".format(self.logger.to_dBm(self.measured_power)))
                # Calculate the power based on C20
                if self.profile.power_verification == 'C20':
                    if self.switch.calibrated:
                        self.calculate_setup_correction_factor(self.f_cw, setup_factor_type='C20')
                        self.logger.stepin()
                        self.measured_power = self.p_out + self.setup_correction_factor
                        self.logger.logln("Setup correction factor: {}".format(self.logger.to_dBm(self.setup_correction_factor)))
                        self.logger.logln("Corrected measured power: {}".format(self.logger.to_dBm(self.measured_power)))
                        self.logger.stepout()
                    else:
                        self.logger.stepin()
                        self.measured_power = self.p_out
                        self.logger.logln("No setup correction factor")
                        self.logger.logln("Corrected measured power: {}".format(self.logger.to_dBm(self.measured_power)))
                        self.logger.stepout()
                self.logger.stepout()
            else:
                self.measured_power = self.p_in
                self.logger.logln("Assuming the true power to be {}...".format(self.logger.to_dBm(self.measured_power)))

            self.logger.stepout(step_out_num=2)
            return f0
    
    """ Function to recover stimulus parameters from a dependency test """
    def recover_stimulus_parameters_from_dependency_test(self, t):
        if not self.using_stimulus:
            self.p_in = None
            return
        if self.profile.power_stimulus == 'single_cw':
            self.f_cw = t.f_cw
            self.p_in = t.p_in
            self.p_out = t.p_out
            self.measured_power = t.measured_power
    
    """ Turn on the stimulus """
    def stimulus_on(self):
        if not self.using_stimulus:
            return
        if self.profile.power_stimulus == 'single_cw_for_calibration':
            # Turn on the RF output from the signal generator
            self.logger.log("Turning on the signal generator RF output... ")
            self.siggen.rf_on()
            self.logger.logln("Done!")
        if self.profile.power_stimulus == 'single_cw':
            # Turn on the RF output from the signal generator
            self.logger.log("Turning on the signal generator RF output... ")
            self.siggen.rf_on()
            self.logger.logln("Done!")
    
    """ Turn off the stimulus """
    def stimulus_off(self):
        if not self.using_stimulus:
            return
        if self.profile.power_stimulus == 'single_cw_for_calibration':
            # Turn on the RF output from the signal generator
            self.logger.log("Turning off the signal generator RF output... ")
            self.siggen.rf_off()
            self.logger.logln("Done!")
        if self.profile.power_stimulus == 'single_cw':
            # Turn on the RF output from the signal generator
            self.logger.log("Turning off the signal generator RF output... ")
            self.siggen.rf_off()
            self.logger.logln("Done!")
    
    """
        >>>
            CHAPTER 6: POWER VERIFICATION SPECIFIC FUNCTIONS
        >>>
    """

    """
        >>>
            CHAPTER 7: GENERAL PARAMETER CALCULATION FUNCTIONS
        >>>
    """

    """ Compute fft_num_bins from fft_min_resoution if required """
    def calculate_fft_num_bins(self):
        if not self.profile.fft_number_of_bins:
            self.logger.log(
                    "Computing number of bins for {}Hz resolution... ".format(
                        self.profile.fft_minimum_frequency_resolution
                    )
                )
            bins = 1
            while self.profile.sdr_sampling_frequency/bins > self.profile.fft_minimum_frequency_resolution:
                bins = bins * 2
            self.profile.fft_number_of_bins = bins
            self.logger.logln("Done!")
        self.logger.logln("Using {} bins per FFT...".format(
                self.profile.fft_number_of_bins
            ))

    # Compute the sweep arrays for the swept power measurement test
    def compute_swept_power_sweep_parameters(self):
        self.logger.log("Computing sweep frequencies and scale factors... ")
        self.f_list = self.create_swept_parameter(
            self.profile.sweep_f_min,
            self.profile.sweep_f_max ,
            self.profile.sweep_f_num_steps,
            self.profile.sweep_f_lin_spacing,
            self.profile.sweep_f_log_steps,
            self.profile.sweep_f_extra,
            self.profile.sweep_f_order
        )
        self.p_list = self.create_swept_parameter(
            self.profile.sweep_p_min,
            self.profile.sweep_p_max ,
            self.profile.sweep_p_num_steps,
            self.profile.sweep_p_lin_spacing,
            self.profile.sweep_p_log_steps,
            self.profile.sweep_p_extra,
            self.profile.sweep_p_order
        )
        self.g_list = self.create_swept_parameter(
            self.profile.sweep_g_min,
            self.profile.sweep_g_max ,
            self.profile.sweep_g_num_steps,
            self.profile.sweep_g_lin_spacing,
            self.profile.sweep_g_log_steps,
            self.profile.sweep_g_extra,
            self.profile.sweep_g_order
        )

        # Get the lists in order
        if self.profile.sweep_order_1st == 'frequency':
            self.sweep_list_1 = self.f_list
        if self.profile.sweep_order_1st == 'power':
            self.sweep_list_1 = self.p_list
        if self.profile.sweep_order_1st == 'gain':
            self.sweep_list_1 = self.g_list
        if self.profile.sweep_order_2nd == 'frequency':
            self.sweep_list_2 = self.f_list
        if self.profile.sweep_order_2nd == 'power':
            self.sweep_list_2 = self.p_list
        if self.profile.sweep_order_2nd == 'gain':
            self.sweep_list_2 = self.g_list
        if self.profile.sweep_order_3rd == 'frequency':
            self.sweep_list_3 = self.f_list
        if self.profile.sweep_order_3rd == 'power':
            self.sweep_list_3 = self.p_list
        if self.profile.sweep_order_3rd == 'gain':
            self.sweep_list_3 = self.g_list
        self.logger.logln("Done!")

    # Compute an array for a swept parameter
    def create_swept_parameter(self,min,max,lin_steps=0,lin_space=0,log_steps=0,extras=[],sort='asc'):
        # Create the base sweep
        if lin_steps > 0:
            arr = np.linspace(min,max,num=lin_steps)
        elif lin_space > 0:
            arr = np.arange(min,max,lin_space)
            if arr[-1] < max:
                arr = np.append(arr, [max])
        elif log_steps > 0:
            arr = np.geomspace(min, max, num=log_steps)
        else:
            arr = np.asarray([])
        
        # Add the extras
        for i in range(len(extras)):
            arr = np.append(arr, [extras[i]])
        
        # Sort if required and return
        arr = np.unique(arr)
        if sort == 'desc':
            arr = arr[::-1]
        return arr.tolist()

    # Compute the LO and CW frequencies based on the profile parameters
    def compute_freqs_with_offset(self, f0):
        f_lo = f0
        f_cw = f0
        if self.profile.freq_use_offset:
            if self.profile.freq_offset_using_sdr:
                f_lo = f_lo + self.profile.freq_offset_f0_and_cw
            else:
                f_cw = f_cw + self.profile.freq_offset_f0_and_cw
        return f_lo, f_cw
    
    # Compute the f0s for a spectrum sweep
    def compute_spectrum_f0s(self,simple_stitch):
        #Compute what the f0s need to be
        f0s = [self.sdr.frequency_round(self.sdr.frequency_round(self.profile.test_freq_min+self.profile.sdr_sampling_frequency/2-self.profile.test_fft_window_narrowing))]
        if simple_stitch:
            while self.profile.test_freq_max > f0s[-1] + self.profile.sdr_sampling_frequency/2-self.profile.test_fft_window_narrowing:
                f0s.append(self.sdr.frequency_round(f0s[-1] + self.profile.sdr_sampling_frequency - 2*self.profile.test_fft_window_narrowing))
        else:
            while True:
                # Calculate the next upper frequency
                f0s.append(self.sdr.frequency_round(f0s[-1] + self.profile.sdr_sampling_frequency/3 - 2*self.profile.test_fft_window_narrowing/3))
                # Check if we have completed the needed range
                if self.profile.test_freq_max < (f0s[-1] + self.profile.sdr_sampling_frequency/2 - self.profile.test_fft_window_narrowing):
                    break
                # Calculate the next lower frequency
                f0s.append(self.sdr.frequency_round(f0s[-1] + self.profile.sdr_sampling_frequency - 2*self.profile.test_fft_window_narrowing))
        return f0s
        
    # Compute a series of f0s and scale factors based on the profile parameters
    def compute_f0s_and_scale_factors(self):
        # Check if a list was passed in the profile
        # (mainly for when these were calculated for the test)
        if self.profile.freq_f0_list is not False:
            return np.asarray(self.profile.freq_f0_list)

        # Finally, create a simple list of frequencies
        if self.profile.freq_num_steps > 0:
            if not self.profile.freq_f0_log_spacing:
                f0s = np.linspace(
                        self.profile.freq_f0_min,
                        self.profile.freq_f0_max,
                        num=self.profile.freq_num_steps
                    )
            else:
                f0s = np.logspace(
                        np.log10(self.profile.freq_f0_min),
                        np.log10(self.profile.freq_f0_max),
                        num=self.profile.freq_num_steps
                    )
        else:
            f0s = np.asarray([])
        return np.sort(np.append(f0s, self.profile.freq_extra_f0s))
    
    # Calculate the indeces for the spectrum sweep
    def compute_spectrum_sweep_indeces(self,simple_stitching):
        # Calculate the window_delta index
        self.narrowing_index = self.profile.fft_number_of_bins * (self.profile.test_fft_window_narrowing/self.profile.sdr_sampling_frequency)
        if simple_stitching:
            self.lwli = int(self.narrowing_index)
            self.lwui = int(self.profile.fft_number_of_bins-self.narrowing_index)
            return
        
        # Calculate the window bounds
        self.lwli = int(self.narrowing_index)
        self.lwui = int(math.ceil((self.profile.fft_number_of_bins+self.narrowing_index)/3))
        self.uwli = int(math.floor((2*self.profile.fft_number_of_bins-self.narrowing_index)/3))
        self.uwui = int(self.profile.fft_number_of_bins-self.narrowing_index)
        while not self.lwui-self.lwli == self.uwui-self.uwli:
            if self.lwui-self.lwli > self.uwui-self.uwli:
                self.uwli = self.uwli - 1
            else:
                self.lwui = self.lwui + 1

    #
    # GENERAL FFT FUNCTIONS
    #

    # Calculate the dBm power of the current window
    def calculate_fft_window_power(self):
        window_power = np.mean(self.fft_window) #sum(self.fft_window ** 2)/len(self.fft_window)
        window_power_dbm = 20*np.log10(window_power)
        #window_power_dbm = -7.3166024515
        return window_power_dbm

    # Create the window for the FFT
    def construct_fft_window(self, window, length):
        self.logger.log("Creating the {} FFT window... ".format(window))
        if window is None:
            self.fft_window = np.ones(length) # signal.flattop(length) # TODO: CHANGE THIS BACK FROM BOXCAR
            #self.fft_window = np.ones(length)
            self.logger.logln("Done!")
            return
        if window == "flattop":
            self.fft_window = signal.flattop(length) # todo: look into why flattop window doesn't work
            self.logger.logln("Done!")
            return
        
        # If we reach here, the window type is not implemented
        ehead = "Unknown window type '{}'".format(window)
        ebody = "See documentation for which windows are currently included."
        Error.error_out(self.logger, SDR_Test_Error(20, ehead, ebody))
    
    # Normalize an FFT
    def normalize_dBm_fft(self, fft):
        return (fft - 20*np.log10(len(fft)))

    # Compute a normalized dBm FFT
    def compute_dBm_fft(self, data, f0):
        fft, fft_freqs = self.compute_fft(data, f0)
        return (fft - 20*np.log10(len(data)/2)), fft_freqs

    # Compute a default FFT
    def compute_fft(self, data, f0):
        print("LENGTH OF WINDOW:", len(self.fft_window))
        print("LENGTH OF DATA:", len(data))
        fft = 20*np.log10(
                np.absolute(
                    np.fft.fftshift(
                        np.fft.fft(self.fft_window*data)
                    )
                )
            ) + self.compute_lin_v_to_dbm_p_factor() - self.calculate_fft_window_power()
        fft_freqs = np.fft.fftshift(
                np.fft.fftfreq(
                    len(data), d=(1/self.sdr.get_sampling_frequency()) #d=(1/self.profile.sdr_sampling_frequency)
                )
            ) + f0
        return fft, fft_freqs

    # Compute an averaged normalized dBm FFT
    def compute_avg_dBm_fft(self, data, f0, avg_num=1):
        bins = int(len(data)/avg_num)
        fft = np.zeros(bins)
        fft_freqs = np.zeros(bins)
        for i in range(avg_num):
            sub_data = data[i*bins:(i+1)*bins]
            sub_fft, sub_fft_freqs = self.compute_dBm_fft(
                    sub_data, f0
                )
            fft = fft + sub_fft
            fft_freqs = sub_fft_freqs
        fft = fft / avg_num
        return fft, fft_freqs

    # Compute an averaged default FFT
    def compute_avg_fft(self, data, lo_freq, avg_num=1):
        print("LENGTH OF DATA IN AVG FFT:", len(data))
        bins = int(len(data)/avg_num)
        fft = np.zeros(bins)#-1000
        fft_freqs = np.zeros(bins)
        for i in range(avg_num):
            sub_data = data[i*bins:(i+1)*bins]
            sub_fft, sub_fft_freqs = self.compute_fft(
                    sub_data, lo_freq
                )
            #fft = np.max(np.array([fft, sub_fft]), axis=0) (Max trace)
            fft = fft + 10**(sub_fft/10)  # converts back to linear to be converted to dB again later
            fft_freqs = sub_fft_freqs
        fft = fft / avg_num
        fft = 10*np.log10(fft)
        return fft, fft_freqs

    #
    # POWER MEASUREMENT FUNCTIONS
    #

    # Compute IQ(V) to P(dBm) factor
    def compute_lin_v_to_dbm_p_factor(self):
        impedance = 50
        factor = 1.0/(2*impedance)
        factor = 10*np.log10(factor) + 30
        return factor

    # Compute power by averaging the time-domain signal
    def compute_time_domain_averaged_power(self, data):
        return 10*np.log10(
                np.mean(
                    np.abs(data)**2
                )
            ) + self.compute_lin_v_to_dbm_p_factor()

    # Compute power by integrating the frequency domain signal
    def compute_freq_domain_integrated_power(self, data):
        f_psd,psd = signal.welch(data, nperseg=self.profile.fft_number_of_bins, fs=self.profile.sdr_sampling_frequency, window=self.fft_window)
        acc = integrate.trapz(psd, f_psd)
        acc = 10*np.log10(acc) + self.compute_lin_v_to_dbm_p_factor()
        return acc

    # Compute the power by looking at the max value in a normalized FFT
    def compute_normalized_fft_maximum_power(
                self, data, f0, avg_num=1
            ):
        fft, fft_freq = self.compute_avg_dBm_fft(
                data, f0, avg_num
            )
        return self.compute_normalized_fft_maximum_power_from_fft(
                fft, fft_freq
            )

    def compute_normalized_fft_maximum_power_from_fft(self, fft, fft_freq, remove_dc_spike=False):
        #remove_dc_spike = 5
        if remove_dc_spike:
            for i in range(remove_dc_spike):
                fft[len(fft)/2 + i] = -150
                fft[len(fft)/2 - i] = -150
        fft_max_index = np.argmax(fft)
        return fft[fft_max_index], fft_freq[fft_max_index]

    # Scale the time domain IQ data with a power scale factor
    def scale_iq_data_with_power_factor(self, iq_data, power_scaling_factor):
        voltage_scaling_factor = (10**(power_scaling_factor/20.0))
        return iq_data*voltage_scaling_factor

    #
    # LINEARITY CHECK FUNCTIONS
    #

    # Check linearity versus threshold
    def check_linearity(
                self, x, y, threshold,
                pin_slope=None, pin_intercept=None
            ):
        # Convert data to np arrays if they are not
        if type(x) is not np.ndarray:
            x = np.asarray(x)
        if type(y) is not np.ndarray:
            y = np.asarray(y)
        
        # Calculate the linear fit based on pinning
        if pin_slope is None and pin_intercept is None:
            lin_coeffs = np.polyfit(x, y, 1)
        elif pin_slope is None:
            lin_coeffs = [None, pin_intercept]
        elif pin_intercept is None:
            lin_coeffs = [pin_slope, None]
        else:
            lin_coeffs = [pin_slope, pin_intercept]
        if lin_coeffs[0] is None:
            lin_coeffs[0] = np.dot(x, y-lin_coeffs[1])/np.dot(x,x)
        if lin_coeffs[1] is None:
            lin_coeffs[1] = np.mean(y - lin_coeffs[0]*x)

        # Create the equation and calculate R-squared
        lin_eq = np.poly1d(lin_coeffs)
        r_squared = self.calc_r_squared(
                x, y, lin_eq
            )
        self.logger.logln("Coefficient: {} * x + {}".format(
                lin_coeffs[0], lin_coeffs[1]
            ))
        self.logger.logln("R-squared: {}".format(
                r_squared
            ))
        ret_dict = {
                'lin_coeffs': lin_coeffs,
                'lin_eq': lin_eq,
                'r_squared': r_squared
            }

        # Check for linear fit within threshold
        if np.abs(1-r_squared) > threshold:
            self.logger.logln("R-squared not within range [{},{}]...".format(
                    1-threshold,
                    1+threshold
                ))
            return False, ret_dict

        # Return a linearity match
        self.logger.logln("Linearity achieved with threshold {}!".format(
                threshold
            ))
        return True, ret_dict

    # Calculate the r-squared on a linear fit
    def calc_r_squared(self, x, y, f):
        y_fit = f(x)
        y_bar = np.sum(y)/len(y)
        SS_tot = np.sum((y-y_bar)**2)
        SS_reg = np.sum((y-y_fit)**2)
        return (1-(SS_reg/SS_tot))
    
    # Determine divisions in a list of discrete points
    def determine_divisions(self,x,y,d,t_d,show_plots):
        self.div_data_num += 1  #DEBUG
        # Calculate the slope
        m = np.zeros(len(x)-1)
        for i in range(len(m)):
            m[i] = np.absolute(y[i+1]-y[i])/(x[i+1]-x[i])
        
        # Compute averages/differences/ratios
        m_p = np.zeros(len(m)-2*d)
        m_pp = np.zeros(len(m)-2*d)
        m_d = np.zeros(len(m)-2*d)
        for i in range(len(m_p)):
            #Compute the average with/without point of interest
            for j in range(2*d+1):
                m_p[i] = m_p[i] + m[i+j]
            m_pp[i] = m_p[i] - m[i+d]
            m_p[i] = m_p[i]/(2*d+1)
            m_pp[i] = m_pp[i]/(2*d)

            #Compute differences and ratios
            m_d[i] = np.absolute((m_p[i]/m_pp[i])-1)
        
        # Normalize the differences with their averages
        # m_d_avg = np.average(m_d)
        # for i in range(len(m_d)):
        #     m_d[i] = m_d[i]/m_d_avg

        # Check the thresholds
        div_is = []
        for i in range(len(m_d)):
            if (m_d[i] > t_d):
                # Ensure this is the peak
                if i==0:
                    if m_d[i]>m_d[i+1]:
                        div_is = np.append(div_is,[i])
                    else:
                        continue
                elif i==len(m_d)-1 :
                    if m_d[i] > m_d[i-1]:
                        div_is = np.append(div_is,[i])
                    else:
                        continue
                elif m_d[i]>m_d[i+1] and m_d[i] > m_d[i-1]:
                    div_is = np.append(div_is,[i])
        print(div_is)
        
        # Show plots if requested
        if show_plots:
            m_x = np.zeros(len(x)-1)
            for i in range(len(x)-1):
                m_x[i] = (x[i]+x[i+1])/2
            m_x = m_x[d:-d]
            threshold_x = [m_x[0],m_x[-1]]
            m_d_threshold = [t_d,t_d]
            plt.plot(m_x,m_d,'b')
            plt.plot(threshold_x,m_d_threshold,'b--')
            legend = ['Slope average ratio', 'Slope average ratio threshold']
            div_plot_y_max = 10*t_d
            for i in range(len(div_is)):
                div_x = [m_x[int(div_is[i])],m_x[int(div_is[i])]]
                div_y = [0,div_plot_y_max]
                plt.plot(div_x,div_y,'g--')
                legend.append("Possible discontinuity {}".format(i+1))
            plt.legend(legend)
            plt.xlim(m_x[0],m_x[-1])
            plt.ylim(0,div_plot_y_max)
            plt.show()
            # with open(self.save_file("div_testing{}.csv".format(self.div_data_num)), 'w+') as file:
            #     for i in range(len(m_x)):
            #         file.write("{},{}\r\n".format(m_x[i],m_d[i]))
            #     file.close()
        
        # Add the offset to return to point of interest and return
        if len(div_is)>0:
            div_is = div_is + d
        return div_is


    #
    # BANDWIDTH AND TRANSFER FUNCTION CALCULATION FUNCTIONS
    #

    # Compute the bandwidth with a defined shoulder cutoff
    def compute_dB_bandwidth(self, h_dB, freqs, cutoff_dB=3):
        # If there is an odd number of elements in the arrays, remove the
        # middle element (should be DC error point)
        if len(h_dB) % 2 == 1:
            h_dB = np.delete(h_dB, math.floor(len(h_dB)/2)+1)
            freqs = np.delete(freqs, math.floor(len(freqs)/2)+1)

        # Split the arrays to calculate both sides independently
        h_dB = np.split(h_dB, 2)
        freqs = np.split(freqs, 2)

        # Get the indices of the max of each side
        max_indeces = [
            np.argmax(h_dB[0]),
            np.argmax(h_dB[1])
        ]

        # Find the dB cutoff frequency for the lower half
        cutoff_freqs = [0, 0]
        for j in range(len(max_indeces)):
            # Scale by the max value for the half
            h_dB[j] = h_dB[j] - h_dB[j][max_indeces[j]]

            # Get the start index since we'll be sweeping up for lower
            # and down for upper
            if j == 0:
                start_index = 1
            else:
                start_index = max_indeces[j]

            # Check for the cutoff crossing
            last_i = (h_dB[j][start_index-1] > -1*cutoff_dB)
            for i in range(start_index, len(h_dB[j])):
                # Start looking for a crossing
                this_i = (h_dB[j][i] > -1*cutoff_dB)
                if last_i is not this_i:
                    # Get the weighted average factor
                    a_i = np.absolute(
                            (h_dB[j][i]+cutoff_dB)/(h_dB[j][i]-h_dB[j][i-1])
                        )

                    # Get the weighted average estimate of the cutoff freq
                    cutoff_freqs[j] = (1-a_i)*freqs[j][i] + a_i*freqs[j][i-1]
                    break
                last_i = this_i

        # Return the 3dB bandwidth
        return (cutoff_freqs[1] - cutoff_freqs[0])

    # Integrate to compute the equivalent noise bandwidth
    def compute_equivalent_noise_bandwidth(self, h_dB, freqs):
        # Integrate the transfer function and divide by the max
        return np.sum(
                10**(h_dB/10)
            ) * (freqs[1]-freqs[0]) / np.amax(10**(h_dB/10))

    # Compute the transfer function from measured and input power
    def compute_dB_transfer_function(self, measured_power, input_power):
        return (np.asarray(measured_power) - np.asarray(input_power))

    #
    # PROGRAM FLOW FUNCTIONS
    #

    def cycling_complete(self, cycle_num):
        if self.profile.test_cycle_use_time:
            t = time.time()
            return (t-self.start_time > self.profile.test_cycle_sweeping_time)
        else:
            return (cycle_num >= self.profile.test_cycle_number_of_sweeps)

    #
    # FILE SAVING FUNCTIONS
    #

    # Create the save directory
    def create_save_directory(self):
        self.save_directory = "./test_results/{}___{}".format(
                time.strftime('%Y-%m-%d_%H_%M_%S'), self.profile.test_type
            )
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)

    # Create the save file name based on the requested file name
    # and the save directory
    def save_file(self, fname):
        return "{}/{}".format(self.save_directory, fname)

    # Write a profile file which will run the exact same test
    def write_profile_to_file(self):
        # Sort the profile values by category so they print in order
        profile_to_write = {}
        cat_list = []

        # print("----------PRINTING PROFILE--------")
        # print("NOW: ",vars(self.profile).items())
        # for k,v in vars(self.profile).items():
        #     print("NEW:",k,v)
        #     try:
        #         print(k[:k.index('_')])
        #     except ValueError:
        #         print("COULDN'T FIND",k,v)

        for k, v in vars(self.profile).items():
            # Get the category for the parameter
            try:
                cat = k[:k.index('_')] # TODO: figure out why it doesn't know what to do with logging params
                # Add this category if it doesn't exist
                if cat not in profile_to_write:
                    profile_to_write[cat] = {}
                    cat_list.append(cat)

                # Add this profile parater to be written
                profile_to_write[cat][k] = v
            except ValueError as e:
                print(e)
                print("COULDN'T FIND",k,v)            

        # Write the profile to file
        with open(
                    self.save_file("{}_profile.profile").format(
                        self.profile.test_type
                    ), 'w+'
                ) as file:
            # Write the profile headers
            file.write("#\r\n")
            file.write("# {}\r\n".format(self.TEST_NAME))
            file.write("#     run on {}\r\n".format(
                    format(time.strftime('%Y-%m-%d_%H_%M_%S'))
                ))
            file.write("#")

            # Write the profile parameters
            for cat in cat_list:
                file.write("\r\n\r\n# {} parameters".format(cat))
                for k, v in profile_to_write[cat].items():
                    f = self.PROFILE_DEFINITIONS['forced_profile_parameters']
                    if k in f:
                        continue
                    file.write("\r\n{} = ".format(k))
                    #if isinstance(v, basestring):
                    if isinstance(v, str):
                        file.write("\"{}\"".format(v))
                    else:
                        file.write("{}".format(v))
            file.close()

    # Write out the used calibration data
    def write_calibration_file(self, fname=None, src_file=None, json_dict=None):
        # Get the full path of the written file
        if fname is None:
            fname = 'calibration_file.json'
        fname = self.save_file(fname)

        # If a file was used, simply copy the file
        if src_file is not None:
            copyfile(src_file, fname)
            return
        
        # If json data is given, write it out
        if json_dict is not None:
            with open(fname, 'w+') as file:
                json.dump(json_dict, file, indent=4)
                file.close()
            return
        
        # If we get here, error because no data was given
        assert 0
        
    # # Write out the scale factor file  OLD METHOD - SAVED FOR REFERENCE UNTIL SURE IT'S NOT USED ANY MORE
    # def write_scale_factor_file(self, fname=None, division_freqs=None, gains=None, freqs=None, scale_factors=None):
    #     if fname is None:
    #         fname = 'scale_factors.csv'
    #     if division_freqs is None:
    #         division_freqs = self.sdr.scale_factor_divisions
    #     if gains is None:
    #         gains = self.sdr.scale_factor_gains
    #     if freqs is None:
    #         freqs = self.sdr.scale_factor_frequencies
    #     if scale_factors is None:
    #         scale_factors = self.sdr.scale_factors
    #     with open(
    #                 self.save_file(fname), 'w+'
    #             ) as file:
    #         for i in range(len(division_freqs)):
    #             file.write("div,{},{}\r\n".format(division_freqs[i][0],division_freqs[i][1]))
    #         for i in range(len(gains)):
    #             file.write(",{}".format(gains[i]))
    #         file.write("\r\n")
    #         for i in range(len(scale_factors)):
    #             file.write("{}".format(freqs[i]))
    #             for j in range(len(scale_factors[i])):
    #                 file.write(",{}".format(scale_factors[i][j]))
    #             file.write("\r\n")
    #         file.close()
    """
        >>>
            CHAPTER 8: CALIBRATION FUNCTIONS
        >>>
    """
    def init_calibration_factors(self):
        # set up calibration file 
        # Load the correction factors if needed
        # TODO: change this to load a power_correction_factor_file
        # move it to initialize power not initialize switch
        # make default case for if there's no correction factor file
        
        self.pwr_correction_factors_set = False
        print("\n LOOKING FOR SWITCH CORRECTION FACTORS\n")
        print("file:", self.profile.switch_correction_factor_file)
        if self.profile.switch_correction_factor_file is not None:
            print("\n LOADING SWITCH CORRECTION FACTORS\n")
            self.logger.log("Loading switch correction factors... ")
            self.load_setup_correction_factor_file(self.profile.switch_correction_factor_file)
            self.logger.logln("Done!")
            self.pwr_correction_factors_set = True
        else:
            self.logger.logln("No calibration data for switch provided...")