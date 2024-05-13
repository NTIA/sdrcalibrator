from sdrcalibrator.lib.equipment.pwrmtr.pwrmtr_error import Power_Meter_Error


class Power_Meter(object):

    # Power meter constants
    PWRMTR_NAME = 'Mock Power Meter'
    PWRMTR_DEFAULT_CONNECT_TIMEOUT = 5000

    def __init__(self):
        self.alive = False

    def connect(self, connect_params):
        self.alive = True

    def query_equipment_options(self):
        assert 0, "Error about not needing to ask for a mock instrument"

    def tune_to_frequency(self, freq):
        pass

    def take_measurement(self, expected_power):
        return expected_power

    def __del__(self):
        if self.alive:
            pass
