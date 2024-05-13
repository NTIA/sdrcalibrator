'''
ADALM2000 Driver Installation Notes
    Author: AJ Cuddeback, acuddeback@ntia.gov

https://wiki.analog.com/university/tools/pluto/drivers/linux

These notes are meant to accompay the instructions at the link above. They are not rigorously validated, 
but they are notes on the process the author used to install the ADALM drivers. If there are addenda to
these install notes that you believe would be helpful, please submit them as an issue or pull request.

    - To check if modules are installed, run modinfo [MODULENAME] in the terminal
    - When writing this code, I used the plutosdr-m2k-udev.dev package to install the ADALM udev rules
    - I used PyADI-IIO to install the IIO-Scope using `pip install pylibiio`
        This is instead of using the instructions linked in the Quick Start (https://wiki.analog.com/university/tools/pluto/users/quick_start)
    - I tested the functionality of my ADALM using a separate jupyter notebook
    - I also installed sudo apt install libiio-utils
    - install Libm2k to use pluto with these instructions: https://wiki.analog.com/university/tools/m2k/libm2k/libm2k
        - install the udev rules for m2k
        - install the libiio and libm2k packages
        - build libm2k on linux using the instruactions starting here: https://wiki.analog.com/university/tools/m2k/libm2k/libm2k#building_on_linux 
        - this should install the bindings 

ADALM Datasheets: https://wiki.analog.com/university/tools/m2k/users/reference_manual 
'''

""" Mock SDR object for unit tests """

import numpy as np
from matplotlib import pyplot as plt
import libm2k
import time

from sdrcalibrator.lib.equipment.sdr.sdr_error import SDR_Error


class SDR(object):

    """ SDR Constants """
        # USER MODIFY based on SDR hardware datasheet values
    SDR_NAME = "ADALM2000"
    SDR_DEFAULT_CLOCK_FREQUENCY = 48e6
    SDR_DEFAULT_SAMPLING_FREQUENCY = 12e6
    SDR_DEFAULT_AUTO_DC_OFFSET = True
    SDR_DEFAULT_AUTO_IQ_IMBALANCE = True
    SDR_DEFAULT_GAIN = 0
    SDR_DEFAULT_F0_TUNING_ERROR_THRESHOLD = 1e6
    SDR_DEFAULT_USE_DSP_LO_SHIFT = False
    SDR_DEFAULT_DSP_LO_SHIFT = -6e6
    SDR_DEFAULT_CONDITIONING_SAMPLES = 1024
    SDR_DEFAULT_POWER_LIMIT = -15
    SDR_DEFAULT_POWER_SCALE_FACTOR = None
    SDR_DEFAULT_POWER_SCALE_FACTOR_FILE = False

    # USER MODIFY additional SDR constants that may be specific to an individual SDR
    # these parameters are to select analog input and output channels for adalm
    ADALM_AIN_VMAX = 2 # used to set voltage range for analog in 
    ADALM_AIN_VMIN = -2 # used to set voltage range for analog in 
    ADALM_KERNEL_BUFFERS_COUNT = 48
    # ADALM_TRIGGER_LEVEL = 0.5
    # ADALM_TRIGGER_DELAY = 0
    # ADALM_AOUT_CHANNEL = 0 # TODO: if wanting to use mroe than one channel for the adam will have to change this


    """ Initialize the SDR """
    def __init__(self):
        # Load defaults in case these are referenced before setting
        self.clk_freq = self.SDR_DEFAULT_CLOCK_FREQUENCY
        self.samp_freq = self.SDR_DEFAULT_SAMPLING_FREQUENCY
        self.auto_dc_offset = self.SDR_DEFAULT_AUTO_DC_OFFSET
        self.auto_iq_balance = self.SDR_DEFAULT_AUTO_IQ_IMBALANCE
        self.gain = self.SDR_DEFAULT_GAIN

        # USER MODIFY with any routines SDR needs to run at startup
        print("CALLED INITIALIZE ADALM")
        return

    """ Connect to the SDR 
    
    inputs: 

    outputs: 

    usage: 
    - used to set serial number for SDR to faciliate connection for testing
    - used to store any other SDR variables needed to function
    """
    # TODO: explain what this is supposed to do (what are the connect params)
    def connect(self, connect_params, connection_error=None):
        found_devices = []

        print("CALLED CONNECT TO ADALM")
        # search for SDR connections
            # USER MODIFY search for SDR based on SDR interface
            # found_devices is list of SDR connections
        found_devices = libm2k.getAllContexts()

        if len(found_devices) < 1:
            connection_error = 0
        elif len(found_devices) > 1:
            connection_error = 1

        # Throw connection errors if requested
        if connection_error == 0:
            ehead = "Could not find a matching SDR"
            ebody = "Try being less restrictive in the search criteria"
            raise SDR_Error(0,ehead, ebody)
        
        if connection_error == 1:
            ehead = "Found multiple SDRs, need exactly 1."
            ebody = "[List of actual devices]"
            raise SDR_Error(1,ehead, ebody)
        
        # try calibrating SDR 
        print("SELF CTX BEING SET AS")
        self.ctx= libm2k.m2kOpen()
        print(self.ctx)
        max_calibration_attemps = 3
        times_attempted_calibration = 0

        retry = True
        max_calibration_attemps = 3
        times_attempted_calibration = 0
        while retry:
            try:
                self.ctx.calibrateADC()
                retry = False
            except ValueError:
                print("Failed to calibrate ADC, retrying after waiting 1s")
                time.sleep(1)
                times_attempted_calibration += 1
                if times_attempted_calibration>max_calibration_attemps:
                    retry = False
                    connection_error = 2

        if connection_error == 2:
            ehead = "Failed to connect to SDR"
            ebody = "Initialization of SDR failed"
            raise SDR_Error(2,ehead, ebody)
        
        # Set a dummy serial number
        self.serial_number = self.ctx.getSerialNumber() # replae with serial number of found device 

        # Set any SDR variables or context that need to be used in other methods
        # configure SDR changels 
        self.ain = self.ctx.getAnalogIn() # SDR analog input
        self.aout = self.ctx.getAnalogOut() # SDR analog output 
        self.trig = self.ain.getTrigger() # SDR Trigger

        # enable input
        self.ain.enableChannel(0,True)
        self.trig.setAnalogMode(0, libm2k.ALWAYS)
        self.ain.enableChannel(1,True)
        self.trig.setAnalogMode(1, libm2k.ALWAYS)

        self.ain.setRange(0, self.ADALM_AIN_VMIN, self.ADALM_AIN_VMAX) 
        self.ain.setRange(1, self.ADALM_AIN_VMIN, self.ADALM_AIN_VMAX) 

        self.ain.setKernelBuffersCount(self.ADALM_KERNEL_BUFFERS_COUNT)
        # print("Kernel buffers count is", self.ADALM_KERNEL_BUFFERS_COUNT)

        # self.trig.setAnalogDelay(self.ADALM_TRIGGER_DELAY)
        # self.trig.setAnalogLevel(self.ADALM_AIN_CHANNEL,0.5)

        # self.ain.enableChannel(1,True)
        print("TODO: CALCULATE I/Q IMBALANCE HERE")
        print("finished connect routine")
        # If no error was requested, return success
        return True
    
    # Return the serial number for this SDR
    def get_serial_number(self):
        return self.serial_number

    """ Set the clock frequency """
    def set_clock_frequency(self, clk_freq, err=False):
        self.clk_freq = clk_freq

        # Throw error if requested (and set to bad value)
            # USER MODIFY error detection based on SDR parameters
            # TODO: figure out how to set adalm clock frequency
        if err:
            self.clk_freq = 2*clk_freq+1e6
            ehead = "Clock frequency not set correctly"
            ebody = "Requested freq: {}MHz\r\n".format(clk_freq/1e6)
            ebody += "Actual freq: {}MHz\r\n".format(self.clk_freq/1e6)
            raise SDR_Error(10,ehead,ebody)
        
        # Return the actual clock frequency
        return self.clk_freq

    """ Return the current clock frequency """
    def get_clock_frequency(self):
        # TODO: figure out how to get adalm clock frequency
        return self.clk_freq

    """ Set the sampling frequency """
    def set_sampling_frequency(self, samp_freq, err=False):
        self.samp_freq = samp_freq

        # Throw error if requested (and set to bad value)
            # USER MODIFY error detection based on SDR parameters
        self.ain.setSampleRate(samp_freq)
        actual_samp_freq = self.get_sampling_frequency()

        if not self.frequency_round(self.samp_freq) == self.frequency_round(actual_samp_freq):
            raise SDR_Error(
                    11,
                    "Sampling frequency not set correctly",
                    ("Requested freq: {}\r\n" +
                    "Actual freq: {}").format(
                        self.frequency_round(self.samp_freq)/1e6,
                        self.frequency_round(actual_samp_freq)/1e6
                    )
                )
        # return actual sampling frequency
        return actual_samp_freq

    """ Return the current sampling frequency """
    def get_sampling_frequency(self):
        return self.ain.getSampleRate()

    """ Enable/disable the auto DC offset correction """
    def set_auto_dc_offset(self, set_val, err=False):
        self.auto_dc_offset = set_val

        # Throw error if requested (and set to bad value)
            # USER MODIFY error detection based on SDR parameters
        if err:
            self.auto_dc_offset = not set_val
            ehead = "Unable to set auto DC offset correction"
            raise SDR_Error(12,ehead)
        
        # Return the actual DC offset
        return self.auto_dc_offset

    """ Return state of auto DC offset correction """
    def get_auto_dc_offset(self):
        return self.auto_dc_offset

    """ Enable/disable the auto IQ balance """
    def set_auto_iq_imbalance(self, set_val, err=False):
        self.auto_iq_balance = set_val

        # Throw error if requested (and set to bad value)
        if err:
            self.auto_iq_balance = not set_val
            ehead = "Unable to set auto IQ imbalance correction"
            raise SDR_Error(13,ehead)
        
        # Return the actual IQ balance
        return self.auto_iq_balance

    """ Return the current state of auto IQ balance """
    def get_auto_iq_imbalance(self):
        return self.auto_iq_balance

    """ Set the gain value for the SDR """
    # TODO
    def set_gain(self, gain, err=False):
        self.gain = gain
        
        # Throw error if requested (and set to bad value)
        if err:
            self.gain = gain+5
            ehead = "Unable to set SDR gain"
            ebody = "Requested gain {}dBm\r\n".format(gain)
            ebody += "Actual gain {}dBm".format(self.gain)
            raise SDR_Error(14,ehead,ebody)
        
        # Return the actual gain
        return self.gain

    """ Return the current gain setting """
    # TODO
    def get_gain(self):
        return self.gain

    """ Configure the f0 tuning threshold before error is raised"""
    # TODO
    def configure_f0_tuning_threshold(self, tuning_threshold):
        self.f0_tuning_threshold = tuning_threshold

    """ Tune the SDR to a frequency """
    # TODO
    def tune_to_frequency(self, f, err=None):
        # Round the f0 to avoid errors when sweeping frequencies
            # USER MODIFY based on how SDR tunes frequency
        self.f0 = self.frequency_round(f)

        # Fail to "parse the result" if requested
        if err == 1:
            ehead = "Could not parse tune result"
            ebody = "Tune result was not as expected"
            raise SDR_Error(21,ehead,ebody)

        # Mock the tune and LO/DSP freq extraction
        self.lo_freq = self.f0-self.dsp_lo_shift
        self.dsp_freq = self.dsp_lo_shift

        # Error with f0 tuning threshold if requested
        if err == 0:
            self.f0 = f + 2*self.f0_tuning_threshold
            ehead = "f0 improperly tuned"
            ebody = "Requested f0 frequency: {}MHz\r\n".format(f/1e6)
            ebody += "Actual f0 frequency: {}MHz".format(self.f0/1e6)

        # Return the center frequency
        return self.f0

    """ Return the currently tuned frequency """
    # TODO
    def current_tuned_frequency(self):
        return self.f0
    
    """ Return the current LO frequency """
    # TODO
    def current_lo_frequency(self):
        return self.lo_freq
    
    """ Return the current DSP frequency """
    # TODO
    def current_dsp_frequency(self):
        return self.dsp_freq

    """ Set the DSP LO shift"""
    # TODO
    def set_dsp_lo_shift(self, dsp_lo_shift):
        self.dsp_lo_shift = dsp_lo_shift

    """ Take IQ samples """
    # TODO
    # USER MODIFY - should return time domain array of IQ data
    def take_iq_samples(self, n, n_skip, retries = 5, err=False):
        # Raise error if requested
        if err:
            ehead = "Failed to acquire IQ samples"
            ebody = "Data acquisition failed {} times in a row...".format(retries+1)
            ebody += "Latest acquisition:\r\n"
            ebody += "Expected IQ data length: {}\r\n".format(n)
            ebody += "Actual IQ data length: 0"
            raise SDR_Error(30, ehead, ebody)
        
        # # Create noise array in frequency domain
        # fft = np.random.normal(0,1e-1,n)

        # # Add the signal
        # fft[int(len(fft)/4-1)] = 1e4
        # fft[int(len(fft)/4)] = 1e4
        # fft[int(len(fft)/4+1)] = 1e4

        # # IFFT it back to the time domain
        # td = np.fft.ifft(np.fft.ifftshift(fft))
        skipiq = self.ain.getSamples(n_skip) # take conditioning samples
        td = self.ain.getSamples(n)
        print("TOOK DATA")
        plt.figure()
        plt.plot(td[0], label="I") 
        plt.plot(td[1], label="Q")
        plt.show()
        
        # Return a dummy array
        return td

    """ Round the frequency according to SDR resolution """
    # TODO
    def frequency_round(self, f):
        # USER MODIFY to use SDR resulution # TODO: Change based on SDR resolution
            # This is user set to what you want your SDR resolution to be
        return int(1e-1 * round(f/1e-1))

    """ Power down the SDR """
    # USER MODIFY
    def power_down(self):
        # print("CALLING POWER DOWN IN POWER DOWN")
        uri = libm2k.getAllContexts()
        # print("CLOSING INDIVIDUAL CONTEXT")
        # print(uri)
        if(hasattr(self, 'ctx')):
            # print("HAS ATTR, CLOSING")
            libm2k.contextClose(self.ctx)   
        else:
            # print("doesn't have attribute, closing all")
            libm2k.contextCloseAll() 
        return

    """ Ensure the SDR is powered down when deleted """
    def __del__(self):
        self.power_down()

##### METHODS FOR UNSUPPORTED FUNCTIONALITY BELOW THIS LINE #####