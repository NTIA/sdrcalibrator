''' 

Author: AJ Cuddeback, acuddeback@ntia.gov

ADALM Pluto Driver Installation Notes 


'''



import numpy as np
from sdrcalibrator.lib.equipment.sdr.sdr_error import SDR_Error

import iio
import time
import numpy as np 
from matplotlib import pyplot as plt 
import libm2k
import adi

class SDR(object):

    """ SDR Constants """
        # USER MODIFY based on SDR hardware datasheet values
    SDR_NAME = "ADALM PLUTO"
    SDR_DEFAULT_CLOCK_FREQUENCY = 40e6 # adalm pluto clock frequency
    SDR_DEFAULT_SAMPLING_FREQUENCY = 12e6
    SDR_DEFAULT_AUTO_DC_OFFSET = True
    SDR_DEFAULT_AUTO_IQ_IMBALANCE = True
    SDR_DEFAULT_GAIN = 0 # adalm pluto has options of [-3 1 71]
    SDR_DEFAULT_F0_TUNING_ERROR_THRESHOLD = 1e6
    SDR_DEFAULT_USE_DSP_LO_SHIFT = False
    SDR_DEFAULT_DSP_LO_SHIFT = -6e6
    SDR_DEFAULT_CONDITIONING_SAMPLES = 1000000 # 1Msample is what radioware uses
    SDR_DEFAULT_POWER_LIMIT = -15
    SDR_DEFAULT_POWER_SCALE_FACTOR = None
    SDR_DEFAULT_POWER_SCALE_FACTOR_FILE = False
    SDR_FREQUENCY_RANGE = [325e6, 3.8e9]
    SDR_ADC_BITS = 12 # bits
    SDR_PLUTO_VDDA1P3_BB = 1.3 # volts
    SDR_VIN_RANGE = [0.05, SDR_PLUTO_VDDA1P3_BB-0.05] # volts


    # USER MODIFY any additional sdr constants that are specific to an individual SDR (rather than the whole class)
        # these variables should be structured as SDRNAME_CONSTANT_NAME

    """ Initialize the SDR """
    def __init__(self):
        # Load defaults in case these are referenced before setting
        self.clk_freq = self.SDR_DEFAULT_CLOCK_FREQUENCY
        self.samp_freq = self.SDR_DEFAULT_SAMPLING_FREQUENCY
        self.auto_dc_offset = self.SDR_DEFAULT_AUTO_DC_OFFSET
        self.auto_iq_balance = self.SDR_DEFAULT_AUTO_IQ_IMBALANCE
        self.gain = self.SDR_DEFAULT_GAIN

        # USER MODIFY with any routines SDR needs to run at startup
        print("CALLED INITIALIZE PLUTO")
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
        found_devices = ["MOCK SDR"]

        # search for SDR connections
            # USER MODIFY search for SDR based on SDR interface
            # found_devices is list of SDR connections
        
        found_devices = iio.scan_contexts()

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
        
        # check for other failed to connect errors here
            # USER MODIFY error detection based on SDR parameters
        
        pluto_addr = ''
        pluto_serial = ''
        for key in found_devices.keys():
            if "ADALM-PLUTO" in found_devices[key]:
                print("Adalm Pluto Detected with location", key)
                pluto_addr = key
                pluto_serial = found_devices[key].split('serial=')[1]
            else:
                connection_error = 2
        
        if connection_error == 2:
            ehead = "Failed to connect to SDR"
            ebody = "Non-Pluto SDR found"
            raise SDR_Error(2,ehead, ebody)
        
        if connection_error == 3:
            ehead = "Failed to connect to SDR"
            ebody = "Initialization of SDR failed"
            raise SDR_Error(2,ehead, ebody)
        
        # Set a dummy serial number
        self.serial_number = pluto_serial # replae with serial number of found device 
            # TODO: Get serial number by splitting string into substrings at "serial="
        
        # Set any SDR variables or context that need to be used in other methods
        self.sdr = adi.Pluto(pluto_addr) # won't get here if no pluto 

        # TODO: calculate I/Q autoimbalance here

        # If no error was requested, return success
        return True
    
    # Return the serial number for this SDR
    def get_serial_number(self):
        return self.serial_number

    """ Return the current clock frequency """
    def get_clock_frequency(self):
        return self.clk_freq

    """ Set the sampling frequency """
    def set_sampling_frequency(self, samp_freq, err=False):
        # self.samp_freq = samp_freq

        # set the sample frequency in the sdr

        # TODO: TEST WHAT HAPPENS IF YOU PUT OTHER TYPES IN
        print("SETTING SAMPLING FREQUENCY TO", samp_freq,"IN ADALM PLUTO METHOD")
        self.sdr.sample_rate = int(samp_freq) # sample frequency must be an integer

        # Throw error if requested (and set to bad value)
            # USER MODIFY error detection based on SDR parameters
        # TODO: Check for an appropriate sample frequency
        if err:
            self.sdr.sample_rate = 2*samp_freq+1e6
            ehead = "Sampling frequency not set correctly"
            ebody = "Requested freq: {}MHz\r\n".format(samp_freq/1e6)
            ebody += "Actual freq: {}MHz\r\n".format(self.samp_freq/1e6)
            raise SDR_Error(11,ehead,ebody)
        
        # Return the actual sampling frequency
        return self.sdr.sample_rate

    """ Return the current ACTUAL sampling frequency """
    def get_sampling_frequency(self):
        return self.sdr.sample_rate # USER MODIFY to use actual SDR settings

    """ Enable/disable the auto DC offset correction """
    def set_auto_dc_offset(self, set_val, err=False):
        self.auto_dc_offset = set_val

        # not all SDRs will have the ability to correct DC offset in software
        # default return value for this funciton should be True

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
        # if set_auto_dc_offset is implemented, should get the value from the SDR
        # otherwise, should just return the default value 
        return self.auto_dc_offset

    """ Enable/disable the auto IQ balance (returns bool)"""
    def set_auto_iq_imbalance(self, set_val, err=False):
        self.auto_iq_balance = set_val

        # should be implemented if the SDR has the ability to correct for IQ imbalance
        # otherwise should return True

        # Throw error if requested (and set to bad value)
        if err:
            self.auto_iq_balance = not set_val
            ehead = "Unable to set auto IQ imbalance correction"
            raise SDR_Error(13,ehead)
        
        # Return the actual IQ balance
        return self.auto_iq_balance

    """ Return the current state of auto IQ balance (returns bool) """
    def get_auto_iq_imbalance(self):
        # should be implemented to get auto IQ imbalance setting from SDR if 
        # set_auto_iq_imbalance is implemented. Otherwise, return default.
        return self.auto_iq_balance

    """ Set the gain value for the SDR """
    def set_gain(self, gain, err=False):
        self.sdr.gain_control_mode_chan0 = "manual"
        self.sdr.rx_hardwaregain_chan0 = gain
        self.sdr_setgain = gain

        # TODO: have a check for where the gain value decreases

        # for SDRs that don't have gain settings, there should be a map function that 
        # maps between gain and however the SDR sets dynamic range (range, attenuation, etc)
        
        # Throw error if requested (and set to bad value)
        if err:
            self.gain = gain+5
            ehead = "Unable to set SDR gain"
            ebody = "Requested gain {}dBm\r\n".format(gain)
            ebody += "Actual gain {}dBm".format(self.gain)
            raise SDR_Error(14,ehead,ebody)
        
        # Return the actual gain
        return self.sdr.rx_hardwaregain_chan0

    """ Return the current gain setting """
    def get_gain(self):
        # for SDRs that don't have gain settings, there should be a map function that 
        # maps between gain and however the SDR sets dynamic range (range, attenuation, etc)
        return self.sdr.rx_hardwaregain_chan0

    """ Configure the f0 tuning threshold before error is raised"""
    def configure_f0_tuning_threshold(self, tuning_threshold):
        # set's how close the tuned frequency has to be to the requested frequency
        self.f0_tuning_threshold = tuning_threshold

    """ Tune the SDR to a frequency """
    def tune_to_frequency(self, f, err=None):
        err = err # TODO: Add this line everywhere else if we want to actually have error handling
        # Round the f0 to avoid errors when sweeping frequencies
            # USER MODIFY based on how SDR tunes frequency
        
        freq = int(f) # prevent floating point error 
        # TODO: See if need a frequency round for pluto 
        self.f0 = self.frequency_round(freq)
        print("SELECTED FREQUENCY IS:", self.f0)
        

        if(self.f0 < self.SDR_FREQUENCY_RANGE[0]):
            print("REQUESTED A FREQUENCY THAT IS TOO LOW")
            err = 2

        if(self.f0 > self.SDR_FREQUENCY_RANGE[1]):
            print("REQUESTED A FREQUENCY THAT IS TOO HIGH")
            err = 2   

        # TODO: handling if using frequency outside range
        # Fail to "parse the result" if requested
        if err == 1:
            ehead = "Could not parse tune result"
            ebody = "Tune result was not as expected"
            raise SDR_Error(21,ehead,ebody)

        # TODO: redo this error checking for adalm pluto
        # Error with f0 tuning threshold if requested
        if err == 0:
            self.f0 = f + 2*self.f0_tuning_threshold
            ehead = "f0 improperly tuned"
            ebody = "Requested f0 frequency: {}MHz\r\n".format(f/1e6)
            ebody += "Actual f0 frequency: {}MHz".format(self.f0/1e6)

        if err == 2: # requested a frequency that was too low
            print("ERROR FOUND ERR 2")
            self.f0 = int(self.SDR_FREQUENCY_RANGE[0])
            ehead = "f0 improperly tuned"
            ebody = "Requested f0 frequency: {}MHz\r\n".format(f/1e6)
            ebody += "Actual f0 frequency: {}MHz".format(self.f0/1e6)

        self.sdr.rx_lo = self.frequency_round(self.f0)
        print("TUNING SDR IN TUNE_TO_FREQUENCY")


        print("DSP LO SHIFT - MIGHT BE WRONG FOR PLUTO")
        # Mock the tune and LO/DSP freq extraction
        self.sdr.rx_lo = self.f0-self.dsp_lo_shift # correct for adalm pluto 
        self.dsp_freq = self.dsp_lo_shift # TODO: check if this is correct for adalm pluto

        # Return the center frequency
        return self.sdr.rx_lo

    """ Return the currently tuned frequency """
    def current_tuned_frequency(self):
        # LO freuquency + DSP frequency for B210 and similar devices only 
        # otherwise, just get the tuned frequency for the SDR
        return self.sdr.rx_lo # TODO: should this be diferent than this? otherwise it's listed as f0
    
    """ Return the current LO frequency """
    def current_lo_frequency(self):
        # likely don't need to implement unless you're working with something like the B210
        return self.sdr.rx_lo # TODO: See if the same as the tuned frequency
    
    """ Return the current DSP frequency """
    def current_dsp_frequency(self):
        # likely don't need to implement unless you're working with something like the B210
        return self.dsp_freq

    """ Set the DSP LO shift"""
    def set_dsp_lo_shift(self, dsp_lo_shift):
        # likely don't need to implement unless you're working with something like the B210
        self.dsp_lo_shift = dsp_lo_shift

    """ Take IQ samples 
    
    Returns a vector of complex samples

    """
    # USER MODIFY - Should return 2D time-domain array of I data and Q data
    def take_iq_samples(self, n, n_skip, retries = 5, err=False):
        print("TAKING IQ AMPLES IN ADALM PLUTO")
        # Raise error if requested
        if err:
            ehead = "Failed to acquire IQ samples"
            ebody = "Data acquisition failed {} times in a row...".format(retries+1)
            ebody += "Latest acquisition:\r\n"
            ebody += "Expected IQ data length: {}\r\n".format(n)
            ebody += "Actual IQ data length: 0"
            raise SDR_Error(30, ehead, ebody)
        
        # TODO: get data 

        # get the skip samples - skips at least this many samples
        print("GETTING CONDITIONING SAMPLES OF LENGTH:", n_skip)
        self.sdr.rx_buffer_size = n_skip+n
        self.sdr.rx() # take samples off pluto and fill buffer 

        # # get the actual samples 
        # print("GETTING ACTUAL SAMPLES OF LENGTH:", n)
        # self.sdr.rx_buffer_size = n
        td_all = self.sdr.rx() 

        td = td_all[n_skip:n+n_skip]
        print("ACTUAL SAMPLES R OF LENGTH:", len(td))
        print("SDR GAIN IS SET TO", self.sdr.rx_hardwaregain_chan0)
        print("WANTED SETTING OF", self.sdr.gain_control_mode_chan0)
        
        # convert the data to volts
        n_bits_ADC = 12
        max_voltage = 0.62 #0.625 # go back to the datasheet and check this voltage swing
        voltage_swing = 2*max_voltage
        n_voltage_steps = 2**(n_bits_ADC)
        volts_per_bit = voltage_swing/(n_voltage_steps-1)
        data_volts = td*volts_per_bit/np.sqrt(10**(self.sdr.rx_hardwaregain_chan0/10))

        # TODO: make wrapper to retry filling the buffer
        
        # Return a dummy array
        return data_volts

    """ Round the frequency according to SDR resolution 
    used in error checking for setting frequency
    """
    def frequency_round(self, f):
        return int(1e-1 * round(f/1e-1))

    """ Power down the SDR """
    # USER MODIFY
    def power_down(self):
        return

    """ Ensure the SDR is powered down when deleted """
    def __del__(self):
        self.power_down()

##### METHODS FOR UNSUPPORTED FUNCTIONALITY BELOW THIS LINE #####
        
    """ Set the clock frequency """
    def set_clock_frequency(self, clk_freq, err=False):
        self.clk_freq = clk_freq

        # Throw error if requested (and set to bad value)
            # USER MODIFY error detection based on SDR parameters
            # in the event that clock frequency and sample rate can't be set 
            # independently (common), this function should return a placeholder
            # return value and not affect SDR settings
        if err:
            self.clk_freq = 2*clk_freq+1e6
            ehead = "Clock frequency not set correctly"
            ebody = "Requested freq: {}MHz\r\n".format(clk_freq/1e6)
            ebody += "Actual freq: {}MHz\r\n".format(self.clk_freq/1e6)
            raise SDR_Error(10,ehead,ebody)
        
        # Return the actual clock frequency
        return self.clk_freq