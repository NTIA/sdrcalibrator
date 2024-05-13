from __future__ import print_function
import argparse
import sys

import numpy as np 
from matplotlib import pyplot as plt

import sdrcalibrator.lib.utils.common as utils
#import sdrcalibrator.lib.utils as utils

def main(foldername, n_iq_plot_samples, make_plots):
    print("in main")
    print(args)
    test_foldername = foldername
    print(test_foldername)
    iq_filename = test_foldername + "iq_dump.csv"
    fft_filename = test_foldername + "FFT.csv"
    #profile_name = test_foldername + "iq_dump_profile.profile"
    # change to get profile name from the folder
    profile_name = test_foldername + "single_fft_profile.profile"
    profile = utils.load_profile(profile_name)
    print("FFT FILENAME:",fft_filename)
    fft_data = np.loadtxt(fft_filename, delimiter=",", dtype="str")
    n_fft_samples = np.shape(fft_data)[0]-1
    FFT = fft_data[1:np.shape(fft_data)[0],:].astype(np.float64)
    FFT_freq = FFT[:,0]; FFT_power_dBm = FFT[:,1]
    FFT_power_dBW = FFT_power_dBm-30
    FFT_power_W = np.power(10, FFT_power_dBW/10)
    FFT_Vrms = np.sqrt(FFT_power_W*50) # assumes 50 Ohms

    fft_var = np.var(FFT_Vrms)
    n_bins = profile.fft_number_of_bins

    iq_data = np.loadtxt(iq_filename, delimiter=",", dtype="str")
    n_iq_samples = np.shape(iq_data)[0]-1

    fs = profile.sdr_sampling_frequency
    ts = 1/fs
    print("ts is:",ts)
    if(args.n_iq_plot_samples == "all"):
        n_iq_plot_samples = n_iq_samples
    else:
        n_iq_plot_samples = int(args.n_iq_plot_samples)

    # Plot IQ data 
    print("MAKE PLOTS", make_plots)
    if(make_plots=="True"):
        plt.figure(); plt.plot(FFT_freq*1e6,FFT_power_dBm)
        plt.xlabel("Frequency (MHz)"); plt.ylabel("Power (dBm)")
        plt.grid(which="both")
        plt.title("Single FFT")
        plt.show()


        tstart = 0; tend = tstart +(n_iq_plot_samples-1)*ts
        print("tend:",tend)
        t = np.linspace(tstart,tend,n_iq_plot_samples) # t is in miliseconds
        iq_data = np.loadtxt(iq_filename, delimiter=",", dtype="str")
        IQ = iq_data[1:np.shape(iq_data)[0],:].astype(np.float64)
        I = IQ[:,0]; Q = IQ[:,1]
        plt.figure()

        plt.plot(t,I[0:n_iq_plot_samples],label="I"); plt.plot(t,Q[0:n_iq_plot_samples],label="Q")
        plt.legend(); plt.xlabel("Time, t (s)"); plt.ylabel("Voltage")
        titlestr = str(n_iq_plot_samples) + " Sample IQ Dump"
        plt.title(titlestr)
        plt.show()
    print("NBINS, VAR:",n_bins,fft_var)
    return n_bins, fft_var
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('foldername',
                        help="Name of folder for iq_data",)
    parser.add_argument('n_iq_plot_samples',
                        help="number of samples to plot",default="all")
    parser.add_argument('plot',
                        help="plot boolean",default="False")
    args = parser.parse_args()

    try:
        main(args.foldername,args.n_iq_plot_samples,args.plot)
    except KeyboardInterrupt:
        print("Caught Ctrl-C, exiting...", file=sys.stderr)
        sys.exit(130)