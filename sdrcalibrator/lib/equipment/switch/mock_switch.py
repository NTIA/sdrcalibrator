from sdrcalibrator.lib.equipment.switch.switch_error import RF_Switch_Error


class RF_Switch(object):

    # RF switch constants
    SWITCH_NAME = 'Mock RF Switch'
    SWITCH_DEFAULT_SWAP_INPUTS = False
    SWITCH_DEFAULT_CORRECTION_FACTOR_FILE = None

    def __init__(self):
        self.alive = False

    def connect(self, connect_params, swap_inputs=False):
        self.swap_inputs = swap_inputs
        self.alive = True

    def select_sdr(self):
        pass

    def select_meter(self):
        pass

    def set_to_default(self):
        pass

    def __del__(self):
        if self.alive:
            self.set_to_default()
