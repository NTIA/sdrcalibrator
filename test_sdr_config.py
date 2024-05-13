#!/usr/bin/env python

from __future__ import print_function
import argparse
import sys

import sdrcalibrator.lib.utils.common as utils
from measurement_profile_gen import merge_measurement_config as gen_measurement_file

""" Load profile and run test """
def main(args):
    # TODO: add timestamp generation here for making filename, always generate new measurement profile
    # gen_measurement_file(args)
    # profile = utils.load_profile(args.filename)
    profile = utils.load_profile('./profiles/measurement_profiles/measurement.profile')

    # run individual tests
    print(profile)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    main(args)