# from __future__ import division, print_function
import time
from gnuradio import eng_notation
import visa

from sdrcalibrator.lib.equipment.siggen.siggen_error import Signal_Generator_Error

# Dummys for now
import numpy as np
from matplotlib import pyplot as plt
from struct import *


class Signal_Generator(object):

    # Signal generator constants
    SIGGEN_NAME = 'Agilent E4438C'
    SIGGEN_DEFAULT_CONNECT_TIMEOUT = 5000
    SIGGEN_DEFAULT_RF_ON_SETTLING_TIME = 1
    SIGGEN_DEFAULT_RF_OFF_SETTLING_TIME = 0
    SIGGEN_DEFAULT_MAX_OUTPUT_POWER = 10
    SIGGEN_ADC_BITS = 14

    def __init__(self):
        self.alive = False
    
    def debug_stop(self):
        raise Signal_Generator_Error(
                99,
                "Debug Stop",
                "Breakpoint to use while debugging"
            )
    
    def create_cw_waveform(self, cw_cycles, sample_rate, carrier_offset):
        # Calculate the number of cycles needed
        #cw_cycles = carrier_offset * (n_samples / sample_rate)
        n_samples = sample_rate * (cw_cycles / carrier_offset)
        print(cw_cycles)
        # Create a CW IQ
        phase = np.arange(n_samples, dtype="float64")
        phase *= 2*np.pi*cw_cycles/n_samples
        i_wav = np.cos(phase)+1
        q_wav = np.sin(phase)+1
        #plt.plot(i_wav)
        #plt.plot(q_wav)
        #plt.show()
        return (i_wav, q_wav)

    
    def send_arbitrary_waveform(self, i_wav, q_wav, sample_rate, remote_fname="WFM1:waveform1"):
        # Interleave I and Q data
        wav = np.zeros(len(i_wav) + len(q_wav), dtype="float64")
        for i in range(len(i_wav)):
            wav[2*i]   = i_wav[i]
            wav[2*i+1] = q_wav[i]
        #plt.plot(wav)
        #plt.show()
        
        # Scale the IQ data
        wav_max = max(wav)
        wav_scaled = np.round((2**(self.SIGGEN_ADC_BITS-1)-1) * wav/wav_max)

        # Pack data into a string
        binwav = pack('>{}h'.format(len(wav_scaled)), *wav_scaled)

        # Debug writing binary file
        with open("./dummy_binary.bin", 'wb+') as file:
            file.write(binwav)
            file.close()
        
        # Generate the command header
        data_size = 2*len(wav) # Each data point is an int16 (i.e. 2 bytes per point)
        data_str_size = len("{}".format(data_size)) # Number of digits in data_size
        waveform_command_header = ":MEMory:DATA \"{}\",#{}{}".format(
            remote_fname,
            data_str_size,
            data_size
        )

        # Add the waveform binary string to the command
        #waveform_command = "{}{}".format(
        #    waveform_command_header,
        #    binwav
        #)

        # Write the waveform to the siggen
        self.siggen.write_binary_values(waveform_command_header, wav_scaled, datatype='h', is_big_endian=True)

        # Set up the waveform
        self.siggen.write(":SOURce:RADio:ARB:WAVeform \"{}\"".format(remote_fname))
        self.siggen.write(":SOURce:RADio:ARB:SCLock:RATE {}HZ".format(eng_notation.num_to_str(sample_rate)))
        self.siggen.write(":SOURce:RADio:ARB:IQ:MODulation:FILTer 2.1e6")
        #self.siggen.write(":SOURce:RADio:ARB:NOISe:STATe OFF") Option 403 not installed

        
    def connect(self, connect_params):
        # Create the Visa resource manager
        rm = visa.ResourceManager('@py')

        # Save the connection variables
        self.ip_addr = connect_params['ip_addr']
        self.port = connect_params['port']
        try:
            self.connect_timeout = connect_params['connect_timeout']
        except KeyError:
            self.connect_timeout = self.SIGGEN_DEFAULT_CONNECT_TIMEOUT

        # Attempt to connect to the machine
        try:
            self.siggen = rm.open_resource("TCPIP0::{}::{}::INSTR".format(
                    self.ip_addr, self.port
                ), open_timeout=self.connect_timeout)
        except Exception as e:
            raise Signal_Generator_Error(
                    0, 
                    "Unable to connect  to the {} signal generator".format(
                        self.SIGGEN_NAME
                    ),
                    "Double check the connection settings on the machine"
                )
        self.alive = True

        # Set the system to preset for repeatability
        self.preset()

        # Configure default settling times
        self.rf_on_settling_time = self.SIGGEN_DEFAULT_RF_ON_SETTLING_TIME
        self.rf_off_settling_time = self.SIGGEN_DEFAULT_RF_OFF_SETTLING_TIME

        # Configure the default max output power
        self.max_output_power = self.SIGGEN_DEFAULT_MAX_OUTPUT_POWER

        # Just ensure the output is off
        self.rf_off()

    # Put the signal generator back to its preset state
    def preset(self):
        # Set system to preset
        self.siggen.write(':SYSTem:PRESet')

        # Ensure all modulations are off
        self.siggen.write(':SOURce:RADio:ALL:OFF')
        self.siggen.write(':OUTPut:MODulation:STATe OFF')

    # Handle turning on and off the RF output
    def rf_on(self, settling_time=None):
        if settling_time is None:
            settling_time = self.rf_on_settling_time
        self.siggen.write(':SOURce:RADio:ARB:STATe ON')
        self.siggen.write(':OUTPut:MODulation:STATe ON')
        self.siggen.write(':OUTPut:STATe ON')
        time.sleep(settling_time)

    def rf_off(self, settling_time=None):
        if settling_time is None:
            settling_time = self.rf_off_settling_time
        self.siggen.write(':SOURce:RADio:ARB:STATe OFF')
        self.siggen.write(':OUTPut:MODulation:STATe OFF')
        self.siggen.write(':OUTPut:STATe OFF')
        time.sleep(settling_time)

    # Handle setting the frequency and power of the output signal
    def tune_to_frequency(self, freq):
        # Create IQ data for a CW with the following parameters:
        #   1000 samples
        #   10MHz sample rate
        #   1MHz carrier offset
        cw_sample_rate = 100e6
        cw_cycles = 400
        cw_carrier_offset = 0.8e6
        (i_wav, q_wav) = self.create_cw_waveform(
            cw_cycles,
            cw_sample_rate,
            cw_carrier_offset
        )

        # Send the wave to the VSG
        remote_fname = "WFM1:test_cw"
        self.send_arbitrary_waveform(i_wav, q_wav, cw_sample_rate, remote_fname)
        
        # Tune to the center frequency
        self.siggen.write(
                ":SOURce:FREQuency {}HZ".format(eng_notation.num_to_str(freq))
            )

    def set_power(self, power):
        # Software limit the output power
        if power > self.max_output_power:
            power = self.max_output_power
        # Set the actual output power
        self.siggen.write(
                ":POWer:LEVel:AMPLitude {}DBM".format(power)
            )

    # Handle configuring settling times
    def configure_rf_on_settling_time(self, t):
        self.rf_on_settling_time = t

    def configure_rf_off_settling_time(self, t):
        self.rf_off_settling_time = t

    # Handle deletion of the signal generator:
    #   ensure it's back in preset and RF is off
    def power_down(self):
        if self.alive:
            #self.preset()
            #self.rf_off()
            self.siggen.close()
            self.alive = False

    # Ensure the device is powered down on deletion
    def __del__(self):
        self.power_down()
