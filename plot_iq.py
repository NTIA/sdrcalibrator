from __future__ import print_function
import argparse
import sys

import numpy as np 
from matplotlib import pyplot as plt

import sdrcalibrator.lib.utils.common as utils

def main(args):
    print("in main")
    print(args)
    test_foldername = args.foldername
    print(test_foldername)
    iq_filename = test_foldername + "iq_dump.csv"
    profile_name = test_foldername + "iq_dump_profile.profile"
    # change to get profile name from the folder
    #profile_name = test_foldername + "single_fft_profile.profile"
    profile = utils.load_profile(profile_name)
    print(profile_name)

    print(iq_filename)

    data = np.loadtxt(iq_filename, delimiter=",", dtype="str")
    n_samples = np.shape(data)[0]-1

    fs = profile.sdr_sampling_frequency
    ts = 1/fs
    print("ts is:",ts)
    if(args.n_plot_samples == "all"):
        n_plot_samples = n_samples
    else:
        n_plot_samples = int(args.n_plot_samples)

    tstart = 0; tend = tstart +(n_plot_samples-1)*ts
    print("tend:",tend)
    t = np.linspace(tstart,tend,n_plot_samples) # t is in miliseconds
    data = np.loadtxt(iq_filename, delimiter=",", dtype="str")
    IQ = data[1:np.shape(data)[0],:].astype(np.float64)
    I = IQ[:,0]; Q = IQ[:,1]
    plt.figure()
    
    fs = 1e6; # change to read from profile

    plt.plot(t,I[0:n_plot_samples],label="I"); plt.plot(t,Q[0:n_plot_samples],label="Q")
    plt.legend(); plt.xlabel("Time, t (s)"); plt.ylabel("Voltage")
    plt.title("IQ Dump")
    plt.show()

    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('foldername',
                        help="Name of folder for data",)
    parser.add_argument('n_plot_samples',
                        help="number of samples to plot",default="all")
    args = parser.parse_args()

    try:
        main(args)
    except KeyboardInterrupt:
        print("Caught Ctrl-C, exiting...", file=sys.stderr)
        sys.exit(130)