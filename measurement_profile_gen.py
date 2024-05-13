# # INPUTS
# #   - experiment profile
# #   - test profile

# # OUTPUTS
# #   - run test profile (for now, profiles/dev_test_gen.profile)

from __future__ import print_function
import argparse
import sys
import sdrcalibrator.lib.utils.common as utils

""" Create Profile File to Run Test """
def merge_measurement_config(args):
    test_profile = experiment_profile = measurement_profile = ""

    # read data from experiment profile
    with open('./profiles/experiment.profile') as fp:
        experiment_profile = fp.read()

    # read data from test profile
    test_filename = args.filename
    with open(test_filename) as fp:
        test_profile = fp.read()

    # merge files 
    measurement_profile += experiment_profile
    measurement_profile += "\n ### PARAMS FROM EXPERIMENT PROFILE ABOVE ###\n \t # Configuring for test from"
    measurement_profile += test_filename
    measurement_profile += "\n ### PARAMS FROM TEST PROFILE BELOW ### \n"
    measurement_profile += test_profile
    measurement_profile += "\n"

    # write to measurement profile file
    with open('./profiles/measurement_profiles/measurement.profile', 'w') as fp:
        fp.write(measurement_profile)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename',help="Filename of test profile",
                        type=utils.filetype)
    args = parser.parse_args()

    try:
        main(args)
    except KeyboardInterrupt:
        print("Caught Ctrl-C, exiting...", file=sys.stderr)
        sys.exit(130)