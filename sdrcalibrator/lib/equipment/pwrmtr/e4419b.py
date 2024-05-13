from gnuradio import eng_notation
from serial.serialutil import SerialException
import pyvisa as visa

from sdrcalibrator.lib.equipment.pwrmtr.pwrmtr_error import Power_Meter_Error


class Power_Meter(object):

    # Power meter constants
    PWRMTR_NAME = 'Agilent E4419B'
    PWRMTR_DEFAULT_CONNECT_TIMEOUT = 5000

    def __init__(self):
        self.alive = False

        # Create the Visa resource manager and get a list of resources
        self.rm = visa.ResourceManager('@py')
        self.resources = self.rm.list_resources()

    def connect(self, connect_params):
        # Check if we are connecting based off an equipment id and
        # save the string
        if 'equipment_id' in connect_params:
            connect_params['equipment_string'] = self.resources[
                    connect_params['equipment_id']
                ]
        if 'equipment_string' in connect_params:
            self.equipment_string = connect_params['equipment_string']
        else:
            raise Power_Meter_Error(
                    10,
                    "No equipment identifier provided",
                    "Double check the connection parameters"
                )

        # Get the connect timeout if necessary
        try:
            self.connect_timeout = connect_params['connect_timeout']
        except KeyError:
            self.connect_timeout = self.PWRMTR_DEFAULT_CONNECT_TIMEOUT

        # Attempt to connect to the machine
        try:
            self.pwrmtr = self.rm.open_resource(
                    self.equipment_string, open_timeout=self.connect_timeout
                )
        except SerialException:
            raise Power_Meter_Error(
                    1,
                    "Unable to connect to the {} power meter".format(
                        self.PWRMTR_NAME
                    ),
                    "Permission is likely denied, try running:" +
                    "\r\nsudo chmod 777 /dev/ttyUSB0"
                )
        except Exception:
            raise Power_Meter_Error(
                        0,
                        "Unable to connect to the {} power meter".format(
                            self.PWRMTR_NAME
                        ),
                        "Try double checking the connection parameters"
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
        self.pwrmtr.write(
                "SENSe:FREQuency {}Hz".format(eng_notation.num_to_str(freq))
            )

    def take_measurement(self, expected_power):
        return eng_notation.str_to_num(self.pwrmtr.query(
                'MEAS1:POW:AC? -10DBM,2,(@1)'
            ))

    def __del__(self):
        if self.alive:
            self.pwrmtr.close()
