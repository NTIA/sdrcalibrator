import vxi11, time, math

from sdrcalibrator.lib.equipment.pwrmtr.pwrmtr_error import Power_Meter_Error


class Power_Meter(object):

    # Power meter constants
    PWRMTR_NAME = 'Keysight N9030B'
    PWRMTR_DEFAULT_CONNECT_TIMEOUT = 5
    PWRMTR_DEFAULT_MEAUREMENT_SPAN = 0.1e6
    PWRMTR_DEFAULT_RESOLUTION_BW = 0.1e3
    PWRMTR_DEFAULT_PERFORM_CALIBRATION_AT_STARTUP = True
    PWRMTR_DEFAULT_COMMAND_TIMEOUT = 5
    PWRMTR_DEFAULT_LOWEST_MEASUREABLE_POWER = -100
    PWRMTR_DEFAULT_MIN_ATTENUATION = 6
    PWRMTR_DEFAULT_MAX_ATTENUATION = 70
    PWRMTR_DEFAULT_PERFORM_CALIBRATIONS_DURING_RUN = False

    def debug_stop(self):
        raise Power_Meter_Error(
                99,
                "Debug Stop",
                "Breakpoint to use while debugging"
            )

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
            self.wait_for_completion()
        except Exception as e:
            raise Power_Meter_Error(
                    0,
                    "Unable to connect to the {} power meter".format(
                        self.PWRMTR_NAME
                    ),
                    "Double check the connection settings on the machine"
                )
        
        # Ensure the model appears in the identification string
        self.idn = self.pwrmtr.ask("*IDN?")
        self.wait_for_completion()
        if not "Keysight Technologies,N9030B" in self.idn:
            raise Power_Meter_Error(
                    0,
                    "Connected instrument is not {}".format(
                        self.PWRMTR_NAME
                    ),
                    (
                        "Connected instrument is not a {}...\r\n" + 
                        "Identification string: {}\r\n" + 
                        "Double check the connection settings on the machine"
                    ).format(
                        self.PWRMTR_NAME,
                        self.idn
                    )
                )
        
        # Successfully connected to the power meter
        self.alive = True

        # Save any operational parameters
        try: # Perform calibration at start of test
            self.perform_calibration_at_startup = connect_params['perform_calibration_at_startup']
        except KeyError:
            self.perform_calibration_at_startup = self.PWRMTR_DEFAULT_PERFORM_CALIBRATION_AT_STARTUP
        try: # Perform calibrations during run as necessary
            self.perform_calibration_during_run = connect_params['perform_calibration_during_run']
        except KeyError:
            self.perform_calibration_during_run = self.PWRMTR_DEFAULT_PERFORM_CALIBRATIONS_DURING_RUN
        try: # Measurement Span
            self.measurement_span = connect_params['measurement_span']
        except KeyError:
            self.measurement_span = self.PWRMTR_DEFAULT_MEAUREMENT_SPAN
        try: # Resolution bandwidth
            self.resolution_bandwidth = connect_params['resolution_bandwidth']
        except KeyError:
            self.resolution_bandwidth = self.PWRMTR_DEFAULT_RESOLUTION_BW
        try: # Command timeout
            self.command_timeout = connect_params['command_timeout']
        except KeyError:
            self.command_timeout = self.PWRMTR_DEFAULT_COMMAND_TIMEOUT
        try: # Minimum Attenuation
            self.min_attenuation = connect_params['min_attenuation']
        except KeyError:
            self.min_attenuation = self.PWRMTR_DEFAULT_MIN_ATTENUATION
        try: # Max Attenuation
            self.max_attenuation = connect_params['max_attenuation']
        except KeyError:
            self.max_attenuation = self.PWRMTR_DEFAULT_MAX_ATTENUATION
        self.pwrmtr.timeout = self.command_timeout
        
        # Reset the system to its preset state
        self.preset()
        
        # Set MXA to take spectrum analyzer (SA) mode
        self.set_and_check_parameter(':INST:SEL', "SA")
        self.preset()

        # Perform a calibration at the start if requested
        if self.perform_calibration_at_startup:
            self.calibrate_as_needed(forced_calibration=True)
        
        # Set auto alignment to partial to prevent mid-test calibrations
        self.set_and_check_parameter(':CAL:AUTO', 'PART', vartype="str", param_val="PART")

        # If performing calibrations during the run, check at the beginning to hopefully not worry about them during the test
        if self.perform_calibration_during_run:
            self.calibrate_as_needed()



    def query_equipment_options(self):
        raise Power_Meter_Error(
                0,
                "Connection is through telnet",
                (
                    "Connection to {} is through telnet\r\n" +
                    "Double check the connection settings on the machine"
                ).format(self.PWRMTR_NAME)
            )

    def tune_to_frequency(self, freq):
        # Check if a calibration is necessary if running calibrations during run
        if self.perform_calibration_during_run:
            self.calibrate_as_needed()
        
        # Set the span
        self.set_and_check_parameter(':FREQ:SPAN', "{:.6f} MHz".format(self.measurement_span/1e6), vartype="int", param_val=self.measurement_span)
        #self.debug_stop()

        # Set the frequency
        freq = int(freq) # Prevent floating point errors (and we don't need sub Hz resolution)
        self.set_and_check_parameter(':FREQ:CENT', "{:.6f} MHz".format(freq/1e6), vartype="int", param_val=freq)

        # Set the resolution bandwidth
        self.set_and_check_parameter(':BAND', "{:.3f} kHz".format(self.resolution_bandwidth/1e3), vartype="int", param_val=self.resolution_bandwidth)

        # Set the FFT Window
        self.set_and_check_parameter(':BAND:SHAP', "FLAT")

    def take_measurement(self, expected_power):
        # Set the attenuation to ideal level for expected power
        ideal_attenuation = self.calculate_attenuation(expected_power)
        self.set_and_check_parameter(':POW:ATT', ideal_attenuation, vartype="int")
        time.sleep(0.5)

        # Start a measurement
        self.wait_for_completion()
        self.pwrmtr.write(":INIT:REST")
        self.wait_for_completion()

        # Find the max power
        self.wait_for_completion()
        self.pwrmtr.write(":CALC:MARK1:MAX")
        self.wait_for_completion()

        # Read the max power
        self.wait_for_completion()
        max_power = float(self.pwrmtr.ask("CALC:MARK1:Y?"))
        self.wait_for_completion()

        # Return the power level
        return max_power
    
    def long_ask(self, ask_string, timeout=60):
        self.pwrmtr.timeout = timeout
        ret_val = self.pwrmtr.ask(ask_string)
        self.wait_for_completion()
        self.pwrmtr.timeout = self.command_timeout
        return ret_val
    
    def wait_for_completion(self,delay_time=0.01, resettle_time = 0.01):
        while not self.pwrmtr.ask('*OPC?'):
            time.sleep(delay_time)
        return
        time.sleep(resettle_time)
    
    def calculate_attenuation(self, expected_power):
        # Calculate the ideal attenuation based on the input power
        ideal_attenuation = expected_power + 50.0

        # Don't let the attenuation fall below the minimum
        if ideal_attenuation < self.min_attenuation:
            ideal_attenuation = self.min_attenuation
        
        # Don't let the attenuation go above the
        if ideal_attenuation > self.max_attenuation:
            ideal_attenuation = self.max_attenuation
        
        # Round attenuation to nearest 2
        ideal_attenuation /= 2
        ideal_attenuation = math.ceil(ideal_attenuation)
        ideal_attenuation = int(ideal_attenuation*2)
        
        # Return the attenuation
        return ideal_attenuation
    
    def set_and_check_parameter(self, cmd, set_val, vartype='str', param_val=None, ask_cmd=None):
        # If no designated response is set, assume the same as set value
        if param_val is None:
            param_val = set_val
        
        # If no designated ask command is set, assume its "[cmd]?"
        if ask_cmd is None:
            ask_cmd = "{}?".format(cmd)
        
        # Wait for anything prior to finish
        self.wait_for_completion()

        # Set the parameter
        cmd = "{} {}".format(cmd,set_val)
        self.pwrmtr.write(cmd)
        self.wait_for_completion()

        # Read the value back
        actual_param_val = self.pwrmtr.ask(ask_cmd)
        self.wait_for_completion()

        # Convert to float if necessary
        if vartype == "int":
            actual_param_val = int(float(actual_param_val))

        # Check that the response is expected
        if not param_val == actual_param_val:
            raise Power_Meter_Error(
                0,
                "Parameter not properly set",
                (
                    "A parameter was not properly set:\r\n" +
                    "    Command: \"{}\"\r\n" +
                    "    Expected value: \"{}\"\r\n" +
                    "    Actual value:   \"{}\""
                ).format(cmd,param_val,actual_param_val)
            )
        else:
            #print("{} -> {}".format(cmd,param_val))
            pass
    
    def calibrate_as_needed(self, forced_calibration=False):
        # Check if a calibration is necessary
        if not forced_calibration:
            self.wait_for_completion()
            forced_calibration = int(self.pwrmtr.ask(":STAT:QUES:CAL:COND?"))
            self.wait_for_completion()
        
        # Calibrate if needed
        if forced_calibration:
            cal_result = int(self.long_ask("*CAL?"))
            if cal_result:
                raise Power_Meter_Error(
                    0,
                    "Calibration failed",
                    (
                        "Calibration of {} failed...\r\n"
                        "Return code: {}"
                    ).format(self.PWRMTR_NAME,cal_result)
                )
    
    def preset(self):
        # Set the signal analyzer to preset
        self.pwrmtr.write('*RST')
        # Restore autoalignment
        self.pwrmtr.write(':CAL:AUTO ON')

    def __del__(self):
        if self.alive:
            self.preset()
            self.pwrmtr.close()
            self.alive = False
