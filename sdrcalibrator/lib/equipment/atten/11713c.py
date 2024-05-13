import time
from gnuradio import eng_notation
import pyvisa as visa
import csv
import numpy as np
import copy

import sdrcalibrator.lib.utils.common as utils
from sdrcalibrator.lib.equipment.atten.atten_error import Programmable_Attenuator_Error


class Programmable_Attenuator(object):

    # Signal generator constants
    ATTEN_NAME = 'Keysight 11713C'
    ATTEN_DEFAULT_CONNECT_TIMEOUT = 5000
    ATTEN_DEFAULT_SETTLING_TIME = 0.25
    ATTENUATOR_LEVELS = {
        'AG8496g': [10,20,40,40],
        'AG8494g': [1,2,4,4]
    }

    def __init__(self):
        self.atten_levels = []
        self.atten_channels = []
        self.caldata_freqs = []
        self.caldata = []
        self.settling_time = self.ATTEN_DEFAULT_SETTLING_TIME
        self.alive = False

    def connect(self, connect_params):
        # Create the Visa resource manager
        rm = visa.ResourceManager('@py')

        # Save the connection variables
        self.ip_addr = connect_params['ip_addr']
        #self.port = connect_params['port']
        try:
            self.connect_timeout = connect_params['connect_timeout']
        except KeyError:
            self.connect_timeout = self.ATTEN_DEFAULT_CONNECT_TIMEOUT

        # Attempt to connect to the machine
        try:
            #self.atten = rm.open_resource("TCPIP0::{}::{}::INSTR".format(
            self.atten = rm.open_resource("TCPIP0::{}::INSTR".format(
                    self.ip_addr#, self.port
                ), open_timeout=self.connect_timeout)
        except Exception:
            raise Programmable_Attenuator_Error(
                    0,
                    "Unable to connect to the {} programmable attenuator".format(
                        self.ATTEN_NAME
                    ),
                    "Double check the connection settings on the machine"
                )
        self.alive = True
    
    # Setup the attenuator according to the params
    def setup(self, params):
        # Configure the voltage supplies
        if 'bank_1_supply' in params:
            self.atten.write("CONFigure:BANK1 {}".format(params['bank_1_supply']))
        if 'bank_2_supply' in params:
            self.atten.write("CONFigure:BANK2 {}".format(params['bank_2_supply']))

        # Check if a cal file exists
        self.caldata_loaded = False
        if 'cal_data_file' in params and params['cal_data_file'] is not None:
            try:
                self.load_calibrated_data(params['cal_data_file'])
                self.caldata_loaded = True
            except Exception as e:
                raise e
        
        # If cal data did not exist or failed to load, use model specs
        if not self.caldata_loaded:
            if 'bank_1x_atten' in params and params['bank_1x_atten'] is not None:
                self.add_model_attenuator_levels(1,'x',params['bank_1x_atten'])
            if 'bank_1y_atten' in params and params['bank_1y_atten'] is not None:
                self.add_model_attenuator_levels(1,'y',params['bank_1y_atten'])
            if 'bank_2x_atten' in params and params['bank_2x_atten'] is not None:
                self.add_model_attenuator_levels(2,'x',params['bank_2x_atten'])
            if 'bank_2y_atten' in params and params['bank_2y_atten'] is not None:
                self.add_model_attenuator_levels(2,'y',params['bank_2y_atten'])

        self.attenuation_off(None)
    
    """ Load the calibrated attenuation levels vs frequency from file """
    def load_calibrated_data(self, fname):
        with open(fname, 'rb') as f:
            reader = csv.reader(f, delimiter=',')
            for row in reader:
                # Check for list of channels
                if row[0] == '' or row[0] == 'freq\\channel':
                    for i in range(len(row)-1):
                        self.atten_channels.append(int(row[i+1]))
                    continue
                # Row must be a frequency row
                self.caldata_freqs.append(float(row[0]))
                self.caldata.append([])
                for i in range(len(row)-1):
                    self.caldata[-1].append(float(row[i+1]))
        # Sort the frequencies, then transpose so the rows correspons to channels
        self.caldata,self.caldata_freqs = utils.sort_matrix_by_list(self.caldata,self.caldata_freqs)
        self.caldata = utils.transpose_matrix(self.caldata)
        return

    """ Add attenuation levels based on the attenuator connected """
    def add_model_attenuator_levels(self, bank, subbank, model):
        # Determine the channel start num
        channel_start = 100*bank + 1
        if subbank == 'y':
            channel_start += 4
        for i in range(len(self.ATTENUATOR_LEVELS[model])):
            self.atten_levels.append(self.ATTENUATOR_LEVELS[model][i])
            self.atten_channels.append(channel_start+i)
    
    def attenuation_off(self, settling_time=None):
        # Use the set settling time if none was requested
        if settling_time is None:
            settling_time = self.settling_time
        
        self.atten.write(":ROUTe:OPEn:ALL")
        if settling_time is not None:
            time.sleep(settling_time)
    
    def set_attenuation(self, attenuation, freq, settling_time=None):
        # Use the set settling time if none was requested
        if settling_time is None:
            settling_time = self.settling_time
        
        # If cal data was loaded, interpolate to create the atten_levels list
        if self.caldata_loaded:
            self.atten_levels = self.get_atten_levels_for_freq(freq)
        
        # Copy and sort to preserve the original lists
        atten_channels = copy.deepcopy(self.atten_channels)
        atten_levels = copy.deepcopy(self.atten_levels)
        atten_channels, atten_levels = utils.sort_matrix_by_list(atten_channels, atten_levels)
        
        # Determine the best attentuation conditions
        channels_to_use = []
        for i in range(len(atten_levels)+1):
            if i == len(atten_levels):
                break
            index = len(atten_levels)-i-1
            if atten_levels[index] <= attenuation:
                channels_to_use.append(atten_channels[index])
                attenuation -= atten_levels[index]
        
        # Set the attenuator channels as needed
        self.attenuation_off(settling_time)
        if len(channels_to_use):
            visa_cmd = "ROUTe:CLOSe (@{}".format(channels_to_use[0])
            for i in range(1,len(channels_to_use)):
                visa_cmd += ",{}".format(channels_to_use[i])
            visa_cmd += ")"
            self.atten.write(visa_cmd)
            time.sleep(settling_time)
        
        # Return the attenuation that was unaccounted for
        return attenuation
    
    """ Interpolate to get the atten_levels list from cal data """
    def get_atten_levels_for_freq(self, f):
        # Get the nearest index for the given frequency
        f_i = utils.get_nearest_low_index(f,self.caldata_freqs)

        # If we're beyond the range, this will trick the interpolation to extrapolate
        if f_i >= len(self.caldata_freqs)-1:
            f_i -= 1
        if f_i < 0:
            f_i = 0
        
        # Get the boundary frequencies
        f_low = self.caldata_freqs[f_i]
        f_high = self.caldata_freqs[f_i+1]

        # Do the interpolation
        atten_levels = np.zeros(len(self.atten_channels)).tolist()
        for i in range(len(atten_levels)):
            atten_levels[i] = utils.interpolate_1d(f,f_low,f_high,self.caldata[i][f_i],self.caldata[i][f_i+1])
        # Return the result
        return atten_levels
    
    # Set the settling time after attenuator switches
    def set_settling_time(self,t):
        self.settling_time = t

    # Handle deletion of the programmable attenuator:
    #   ensure itall switches are off
    def power_down(self):
        if self.alive:
            self.attenuation_off(0)
            self.alive = False
            return

    # Ensure the device is powered down on deletion
    def __del__(self):
        self.power_down()
