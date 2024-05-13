""" Mock Signal Generator object for unit tests """

import time

from sdrcalibrator.lib.equipment.siggen.siggen_error import Signal_Generator_Error


class Signal_Generator(object):

    """ Signal Generator Constants """
    SIGGEN_NAME = 'Mock Signal Generator'
    SIGGEN_DEFAULT_CONNECT_TIMEOUT = 5000
    SIGGEN_DEFAULT_RF_ON_SETTLING_TIME = 1
    SIGGEN_DEFAULT_RF_OFF_SETTLING_TIME = 0

    """ Initialize the signal generator """
    def __init__(self):
        self.alive = False

    """ Connect to the siggen """
    def connect(self, connect_params, err=False):
        # Raise a connection error if requested
        if err:
            ehead = "Unable to connect to the signal generator"
            ebody = "Double check the connection settings on the machine"
            raise Signal_Generator_Error(0, ehead, ebody)
        
        # "Connect to the siggen"
        self.alive = True

        # Set the system to preset for repeatability
        self.preset()

        # Configure default settling times
        self.rf_on_settling_time = self.SIGGEN_DEFAULT_RF_ON_SETTLING_TIME
        self.rf_off_settling_time = self.SIGGEN_DEFAULT_RF_OFF_SETTLING_TIME

        # Just ensure the output is off
        self.rf_off()

    """ Put siggen in its preset state """
    def preset(self):
        return

    """ Turn on the output RF """
    def rf_on(self, settling_time=None, actually_settle=False):
        # Determine the settling time
        if settling_time is None:
            settling_time = self.rf_on_settling_time

        # Only settle if for some reason a test absolutely needs this
        if actually_settle:
            time.sleep(settling_time)

    """ Turn off the output RF """
    def rf_off(self, settling_time=None, actually_settle=False):
        # Determine the settling time
        if settling_time is None:
            settling_time = self.rf_off_settling_time

        # Only settle if for some reason a test absolutely needs this
        if actually_settle:
            time.sleep(settling_time)

    """ Set the frequency of the RF output """
    def tune_to_frequency(self, freq):
        return

    """ Set the power of the RF output """
    def set_power(self, power):
        return

    """ Set the rf_on() settling time """
    def configure_rf_on_settling_time(self, t):
        self.rf_on_settling_time = t

    """ Set the rf_off() settling time """
    def configure_rf_off_settling_time(self, t):
        self.rf_off_settling_time = t

    """ Power down the signal generator """
    def power_down(self):
        if self.alive:
            self.preset()
            self.rf_off()
            self.alive = False

    """ Ensure the siggen is powered down when deleted """
    def __del__(self):
        self.power_down()
