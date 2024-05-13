import vxi11
#from gnuradio import eng_notation

from sdrcalibrator.lib.equipment.pwrmtr.pwrmtr_error import Power_Meter_Error


class Power_Meter(object):

    # Power meter constants
    PWRMTR_NAME = 'Keysight N1912A'
    PWRMTR_DEFAULT_CONNECT_TIMEOUT = 5000

    def __init__(self):
        self.alive = False

    def connect(self, connect_params):
        # Save the connection variables
        self.ip_addr = connect_params['ip_addr']
        try:
            self.connect_timeout = connect_params['connect_timeout']
        except KeyError:
            self.connect_timeout = self.PWRMTR_DEFAULT_CONNECT_TIMEOUT
        
        # Attempt to connect to the machine
        try:
            self.pwrmtr = vxi11.Instrument(self.ip_addr)
        except Exception as e:
            raise Power_Meter_Error(
                    0,
                    "Unable to connect to the {} power meter".format(
                        self.PWRMTR_NAME
                    ),
                    "Double check the connection settings on the machine"
                )
        self.alive = True

        # Set meter to remote operating mode
        self.pwrmtr.write('SYSTem:REMote')

        # Set units to dBm
        self.pwrmtr.write('UNIT1:POWer DBM')

        # Set data format to ASCII
        self.pwrmtr.write('FORMat ASCii')

        # Set number data byte order to "normal"
        self.pwrmtr.write('FORMat:BORDer NORMal')

        # Set measurement rate to double (40 readings/second)
        self.pwrmtr.write('SENSe:MRATe DOUBle')

    def query_equipment_options(self):
        return self.resources

    def tune_to_frequency(self, freq):
        #self.pwrmtr.write(
        #        "SENSe:FREQuency {}Hz".format(eng_notation.num_to_str(freq))
        #    )
        self.pwrmtr.write(
                "SENSe:FREQuency {}Hz".format(int(freq))
            )

    def take_measurement(self, expected_power):
        return float(self.pwrmtr.ask(
                'MEAS1:POW:AC? -10DBM,2,(@1)'
            ))

    def __del__(self):
        if self.alive:
            self.pwrmtr.close()
