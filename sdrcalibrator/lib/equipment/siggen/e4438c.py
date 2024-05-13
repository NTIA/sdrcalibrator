# from __future__ import division, print_function
import time
from gnuradio import eng_notation
import pyvisa as visa

from sdrcalibrator.lib.equipment.siggen.siggen_error import Signal_Generator_Error


class Signal_Generator(object):

    # Signal generator constants
    SIGGEN_NAME = 'Agilent E4438C'
    SIGGEN_DEFAULT_CONNECT_TIMEOUT = 5000
    SIGGEN_DEFAULT_RF_ON_SETTLING_TIME = 1
    SIGGEN_DEFAULT_RF_OFF_SETTLING_TIME = 0
    SIGGEN_DEFAULT_MAX_OUTPUT_POWER = 10

    def __init__(self):
        self.alive = False

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
                    "Unable to connect to the {} signal generator".format(
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

        # Disable modulation on signal
        self.siggen.write(':OUTPut:MODulation:STATe OFF')

        # Just ensure the output is off
        self.rf_off()

    # Put the signal generator back to its preset state
    def preset(self):
        self.siggen.write(':SYSTem:PRESet')

    # Handle turning on and off the RF output
    def rf_on(self, settling_time=None):
        if settling_time is None:
            settling_time = self.rf_on_settling_time
        self.siggen.write(':OUTPut:STATe ON')
        time.sleep(settling_time)

    def rf_off(self, settling_time=None):
        if settling_time is None:
            settling_time = self.rf_off_settling_time
        self.siggen.write(':OUTPut:STATe OFF')
        time.sleep(settling_time)

    # Handle setting the frequency and power of the output signal
    def tune_to_frequency(self, freq):
        self.siggen.write(
                ":FREQuency {}HZ".format(eng_notation.num_to_str(freq))
            )

    def set_power(self, power):
        # Software limit the output power
        if power > self.max_output_power:
            power = self.max_output_power
        # Set the actual output power
        self.siggen.write(
                ":POWer {}DBM".format(power)
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
            self.preset()
            self.rf_off()
            self.siggen.close()
            self.alive = False

    # Ensure the device is powered down on deletion
    def __del__(self):
        self.power_down()
