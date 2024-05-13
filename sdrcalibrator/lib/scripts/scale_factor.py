import numpy as np
from matplotlib import pyplot as plt
from copy import copy, deepcopy

from sdrcalibrator.lib.utils.sdr_test_class import SDR_Test_Class
from sdrcalibrator.lib.utils.sdr_test_error import SDR_Test_Error
import sdrcalibrator.lib.utils.common as utils
import sdrcalibrator.lib.utils.error as Error


class SDR_Test(SDR_Test_Class):

    # Test specific constants
    TEST_NAME = "Scale Factor Calibration"

    # Test constructor
    def __init__(self, profile, logger=None):
        self.TEST_PROFILE_DEFINITIONS = {
            'required_tests': [
                'swept_power_measurement'
            ],
            'required_profile_parameters': [
                'power_level'
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
                'test_find_divisions': False,
                'test_division_slope_averaging_factor': 3,
                'test_division_slope_ratio_threshold': 0.5,
                'test_division_resolution': 1e3,
                'test_division_narrowing_num': 20,
                'test_division_narrowing_buffer': 0.25,
                'test_division_narrowing_slope_ratio_threshold': 2,
                'test_division_observe': False,
                'test_known_divisions': [],
                'logging_save_scale_factors': False,
                'logging_plot_scale_factors': True
            },
            'forced_profile_parameters': {
                'test_check_for_compression': False,
                'test_measure_spur_power': False,
                'sweep_p_min': None,
                'sweep_p_max': None,
                'sweep_p_num_steps': False,
                'sweep_p_lin_spacing': False,
                'sweep_p_log_steps': False,
                'sweep_order_1st': 'power',
                'sweep_order_2nd': 'gain',
                'sweep_order_3rd': 'frequency',
                'freq_f0': False,
                'power_stimulus': 'single_cw',
                'sdr_gain': 0,
                'sdr_power_scale_factor': 0,
                'sdr_power_scale_factor_file': False
            }
        }
        super(SDR_Test, self).__init__(profile, logger)

    # Check the profile
    def check_profile(self):
        # Add the power level as the only option for power
        if self.profile_parameter_exists('power_level'):
            self.profile.sweep_p_extra = [self.profile.power_level]
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
                    ehead += "    {}\r\n".format(check_list[i])
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
    
    # Run a scale factor sweep
    def run_scale_factor_sweep(self, profile_adjustments):
        # Run the Swept Power Measurement Test
        self.run_dependency_test(
            self.swept_power_measurement,
            profile_adjustments
        )

        # Compute the scale factors
        self.logger.log("Computing scale factors... ")
        r = self.swept_power_measurement
        f_los = np.zeros(len(r.f_list)).tolist()
        gains = deepcopy(r.g_list)
        sfs = np.zeros((
            len(gains),
            len(f_los)
        )).tolist()
        sdr_powers = getattr(r, self.profile.test_power_measurement_method)
        measured_powers = r.measured_powers
        for i in range(len(f_los)):
            f_los[i] = r.f_los[0][0][i]
            for j in range(len(gains)):
                sfs[j][i] = measured_powers[0][j][i]-sdr_powers[0][j][i]
        self.logger.logln("Done!")
        self.logger.flush()

        return deepcopy(f_los), deepcopy(gains), deepcopy(sfs)

    # Run the equipment for the test
    def run_test(self):

        # Run the base scale factor sweep
        self.logger.logln("Running the base scale factor sweep...")
        self.logger.stepin()
        f_los, gains, sfs = self.run_scale_factor_sweep({})
        self.logger.stepout()

        # Do the automatic testing for divisions
        found_divisions = {}
        self.div_data_num = 0  #DEBUG
        if self.profile.test_find_divisions:
            # Check for divisions
            self.logger.logln("Checking for divisions...")
            sfs = utils.transpose_matrix(sfs)
            f_los,sfs = utils.remove_duplicates(f_los,sfs)
            sfs = utils.transpose_matrix(sfs)
            for i in range(len(gains)):
                divs = self.determine_divisions(
                    f_los,
                    sfs[i],
                    self.profile.test_division_slope_averaging_factor,
                    self.profile.test_division_slope_ratio_threshold,
                    self.profile.test_division_observe
                )

                # Compile list of divisions and the first gain they appear at, that also are not already known divisions
                for f_i in divs:
                    f_i = int(f_i)
                    # Check if this is a known division
                    div_known = False
                    for known_division in self.profile.test_known_divisions:
                        if known_division[0] <= f_los[f_i+2] and known_division[1] >= f_los[f_i-1]:
                            div_known = True
                            break
                    # Check that this wasn't already found
                    if not div_known and f_i not in found_divisions:
                        # Add the division index pointing to the gain it was found at
                        found_divisions[f_i] = [gains[i], f_los[f_i-1], f_los[f_i+2]]
            # Check that new divisions were found
            if len(found_divisions) > 0:
                self.logger.logln("New division found:")
                self.logger.stepin()
                for k,v in found_divisions.iteritems():
                    self.logger.logln("[{},{}] at gain {}dB".format(self.logger.to_MHz(v[1]),self.logger.to_MHz(v[2]),v[0]))
                self.logger.stepout()
                # Narrow each division
                for k,v in found_divisions.iteritems():
                    self.logger.logln("Narrowing division between [{},{}]...".format(self.logger.to_MHz(v[1]),self.logger.to_MHz(v[2])))
                    self.logger.stepin()
                    division_narrowed = False
                    while not division_narrowed:
                        # Run sweep across the division at the first gain it was found at
                        self.logger.logln("Division currently between [{},{}]...".format(self.logger.to_MHz(v[1]),self.logger.to_MHz(v[2])))
                        self.logger.stepin()
                        buffer = (v[2]-v[1])*self.profile.test_division_narrowing_buffer
                        profile_adjustments = {
                            'sweep_f_min': v[1]-buffer,
                            'sweep_f_max': v[2]+buffer,
                            'sweep_f_num_steps': self.profile.test_division_narrowing_num,
                            'sweep_f_extra': [],
                            'sweep_g_num_steps': False,
                            'sweep_g_lin_spacing': False,
                            'sweep_g_log_steps': False,
                            'sweep_g_extra': [v[0]]
                        }
                        division_f_los, division_gains, division_sfs = self.run_scale_factor_sweep(profile_adjustments)

                        # Remove duplicates in case its up against the LO resolution of the SDR
                        before_length = len(division_f_los)
                        division_sfs = utils.transpose_matrix(division_sfs)
                        division_f_los,division_sfs = utils.remove_duplicates(division_f_los,division_sfs)
                        division_sfs = utils.transpose_matrix(division_sfs)

                        if len(division_f_los)-2*self.profile.test_division_slope_averaging_factor-1 < 7:
                            v[1] -= buffer
                            v[2] += buffer
                            self.logger.logln("Narrowed division too far, slightly increasing before running algorithm...")
                            self.logger.stepout()
                            continue
                        
                        # Find the division within the division
                        narrowed_divs = self.determine_divisions(
                            division_f_los,
                            division_sfs[0],
                            self.profile.test_division_slope_averaging_factor,
                            self.profile.test_division_narrowing_slope_ratio_threshold,
                            self.profile.test_division_observe
                        )
                        if len(narrowed_divs) < 1:
                            self.logger.stepin(step_in_num=2)
                            self.logger.logln("!!! NARROWED DIVISION RETURNED NO RESULTS !!!")
                            self.logger.logln("Assuming it was a false positive...")
                            self.logger.stepout(step_out_num=2)
                            found_divisions[k] = None
                            break
                        if len(narrowed_divs) > 1:
                            self.logger.stepin(step_in_num=2)
                            self.logger.logln("!!! NARROWED DIVISION RETURNED MULTIPLE RESULTS !!!")
                            self.logger.logln("Assuming the first...")
                            self.logger.stepout(step_out_num=2)
                        f_i = int(narrowed_divs[0])
                        self.logger.logln("Narrowed division to [{},{}]".format(self.logger.to_MHz(division_f_los[f_i]),self.logger.to_MHz(division_f_los[f_i+1])))
                        v[1] = division_f_los[f_i]
                        v[2] = division_f_los[f_i+1]

                        # Check if the division has been sufficiently narrowed
                        if v[2]-v[1] < self.profile.test_division_resolution:
                            self.logger.logln("Division successfully narrowed...")
                            division_narrowed = True
                        
                        # Check if the resolution of the SDR has been reached (i.e. there are duplicates)
                        if not len(division_f_los) == before_length:
                            self.logger.logln("LO resolution of the SDR has been reached...")
                            self.logger.logln("Division successfully narrowed...")
                            division_narrowed = True
                        self.logger.flush()
                        self.logger.stepout()
                    if division_narrowed:
                        found_divisions[k][1] = v[1]
                        found_divisions[k][2] = v[2]
                    self.logger.stepout()
            else:
                self.logger.logln("No new divisions found...")
        
        # Consolidate division boundary frequencies
        self.logger.log("Consolidating boundary frequencies... ")
        division_freqs = []
        for k,v in found_divisions.items():
            if v is None:
                continue
            division_freqs.append(v[1])
            division_freqs.append(v[2])
        for kd in self.profile.test_known_divisions:
            division_freqs.append(kd[0])
            division_freqs.append(kd[1])
        division_freqs.sort()
        self.logger.logln("Done!")

        # Get the scale factors at the boundaries
        self.logger.logln("Getting the scale factors at the boundaries...")
        self.logger.stepin()
        profile_adjustments = {
            'sweep_f_num_steps': False,
            'sweep_f_lin_spacing': False,
            'sweep_f_log_steps': False,
            'sweep_f_extra': division_freqs
        }
        division_boundary_f_los, division_boundary_gains, division_boundary_sfs = self.run_scale_factor_sweep(profile_adjustments)
        self.logger.stepout()

        # Consolidate the lists and sort
        self.logger.log("Consolidating data... ")
        self.f_los = f_los
        self.gains = gains
        self.sfs = sfs
        for i in range(len(division_boundary_f_los)):
            self.f_los.append(division_boundary_f_los[i])
        self.sfs = utils.transpose_matrix(self.sfs)
        division_boundary_sfs = utils.transpose_matrix(division_boundary_sfs)
        self.sfs = utils.stack_matrices(self.sfs,division_boundary_sfs)
        self.f_los,self.sfs = utils.remove_duplicates(self.f_los,self.sfs)
        self.sfs = utils.transpose_matrix(self.sfs)
        self.sfs = utils.transpose_matrix(self.sfs)
        self.sfs,self.gains,self.f_los = utils.sort_matrix_by_lists(self.sfs,self.gains,self.f_los)
        division_boundary_f_los.sort()
        self.division_freq_pairs = []
        for i in range(0,len(division_boundary_f_los),2):
            self.division_freq_pairs.append([
                division_boundary_f_los[i],
                division_boundary_f_los[i+1]
            ])
        self.logger.logln("Done!")

    # Save data or construct plot if required
    def save_data(self):
        # Save the scale factors if requested
        if self.profile.logging_save_scale_factors:
            self.logger.log("Writing scale factor data to file... ")
            fname = "scale_factors.csv"
            with open(self.save_file(fname), 'w+') as file:
                for i in range(len(self.division_freq_pairs)):
                    file.write("div,{},{}\r\n".format(
                        self.division_freq_pairs[i][0],
                        self.division_freq_pairs[i][1]
                    ))
                for j in range(len(self.gains)):
                    file.write(",{}".format(self.gains[j]))
                file.write("\r\n")
                for i in range(len(self.f_los)):
                    file.write("{}".format(self.f_los[i]))
                    for j in range(len(self.gains)):
                        file.write(",{}".format(self.sfs[i][j]))
                    file.write("\r\n")
                file.close()
            # self.write_scale_factor_file(
            #     fname = 'scale_factors.csv',
            #     division_freqs = self.division_freq_pairs,
            #     gains = self.gains,
            #     freqs = self.f_los,
            #     scale_factors = self.sfs
            # )
            # with open(self.save_file("scale_factors.json"), 'w+') as file:
            #     file.write("[\r\n")
            #     for i in range(len(self.gains)):
            #         for j in range(len(self.f_los)):
            #             file.write("    {\r\n")
            #             file.write("        \"gain\": {},\r\n".format(self.gains[i]))
            #             file.write("        \"frequency\": {},\r\n".format(self.f_los[j]))
            #             file.write("        \"scale_factor\": {}\r\n".format(self.sfs[j][i]))
            #             file.write("    },\r\n")
            #     file.write("]")
            #     file.close()
            self.logger.logln("Done!")

        # Create the plot if desired
        if self.profile.logging_plot_scale_factors:
            plot_max = 0
            plot_min = 0
            self.sfs = utils.transpose_matrix(self.sfs)
            self.f_los = np.asarray(self.f_los)
            for i in range(len(self.gains)):
                plt.plot(self.f_los/1e6, self.sfs[i])
                if np.amax(self.sfs[i]) > plot_max:
                    plot_max = np.amax(self.sfs[i])
                if np.amin(self.sfs[i]) < plot_min:
                    plot_min = np.amin(self.sfs[i])
            yrange_buffer = 0.25*(
                    plot_max - plot_min
                )
            plt.gca().set_ylim([
                    plot_min-yrange_buffer,
                    plot_max+yrange_buffer
                ])
            plt.gca().set_xlim([
                    self.f_los[0]/1e6,
                    self.f_los[-1]/1e6
                ])
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Scale Factors (dBm)")
            plt.show()

    # Cleanup as necessary
    def cleanup(self):
        super(SDR_Test, self).cleanup()
