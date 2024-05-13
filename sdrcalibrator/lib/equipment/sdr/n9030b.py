# from gnuradio import analog, blocks, gr, uhd
import numpy as np
import vxi11, time, math

from sdrcalibrator.lib.equipment.sdr.sdr_error import SDR_Error


class SDR(object):

    # SDR constants
    SDR_NAME = 'Keysight N9030B'
    SDR_DEFAULT_CLOCK_FREQUENCY = 48e6
    SDR_DEFAULT_SAMPLING_FREQUENCY = 12e6
    SDR_DEFAULT_AUTO_DC_OFFSET = None
    SDR_DEFAULT_AUTO_IQ_IMBALANCE = None
    SDR_DEFAULT_GAIN = 0
    SDR_DEFAULT_F0_TUNING_ERROR_THRESHOLD = 1e6
    SDR_DEFAULT_USE_DSP_LO_SHIFT = False
    SDR_DEFAULT_DSP_LO_SHIFT = -6e6
    SDR_DEFAULT_CONDITIONING_SAMPLES = 1000
    SDR_DEFAULT_POWER_LIMIT = -15
    SDR_DEFAULT_POWER_SCALE_FACTOR = None
    SDR_DEFAULT_POWER_SCALE_FACTOR_FILE = False

    SDR_DEFAULT_CONNECT_TIMEOUT = 5
    SDR_DEFAULT_PERFORM_CALIBRATION_AT_STARTUP = False
    SDR_DEFAULT_COMMAND_TIMEOUT = 5
    SDR_DEFAULT_LOWEST_MEASUREABLE_POWER = -100
    SDR_DEFAULT_MIN_ATTENUATION = 6
    SDR_DEFAULT_MAX_ATTENUATION = 70
    SDR_DEFAULT_PERFORM_CALIBRATIONS_DURING_RUN = False

    def __init__(self):
        self.alive = False

    def connect(self, connect_params):
        # Save the connection variables
        self.ip_addr = connect_params['ip_addr']
        try:
            self.connect_timeout = connect_params['connect_timeout']
        except KeyError:
            self.connect_timeout = self.SDR_DEFAULT_CONNECT_TIMEOUT
        
        # Attempt to connect to the machine
        try:
            self.sdr = vxi11.Instrument(self.ip_addr)
            self.wait_for_completion()
        except Exception as e:
            raise SDR_Error(
                    0,
                    "Unable to connect to the {} sdr".format(
                        self.SDR_NAME
                    ),
                    "Double check the connection settings on the machine"
                )
        
        # Successfully connected to the SDR
        self.alive = True
        
        # Ensure the model appears in the identification string
        self.idn = self.sdr.ask("*IDN?")
        self.wait_for_completion()
        if not "Keysight Technologies,N9030B" in self.idn:
            raise SDR_Error(
                    0,
                    "Connected instrument is not {}".format(
                        self.SDR_NAME
                    ),
                    (
                        "Connected instrument is not a {}...\r\n" + 
                        "Identification string: {}\r\n" + 
                        "Double check the connection settings on the machine"
                    ).format(
                        self.SDR_NAME,
                        self.idn
                    )
                )
        
        # Save any operational parameters
        try: # Perform calibration at start of test
            self.perform_calibration_at_startup = connect_params['perform_calibration_at_startup']
        except KeyError:
            self.perform_calibration_at_startup = self.SDR_DEFAULT_PERFORM_CALIBRATION_AT_STARTUP
        try: # Perform calibrations during run as necessary
            self.perform_calibration_during_run = connect_params['perform_calibration_during_run']
        except KeyError:
            self.perform_calibration_during_run = self.SDR_DEFAULT_PERFORM_CALIBRATIONS_DURING_RUN
        try: # Command timeout
            self.command_timeout = connect_params['command_timeout']
        except KeyError:
            self.command_timeout = self.SDR_DEFAULT_COMMAND_TIMEOUT
        try: # Minimum Attenuation
            self.min_attenuation = connect_params['min_attenuation']
        except KeyError:
            self.min_attenuation = self.SDR_DEFAULT_MIN_ATTENUATION
        try: # Max Attenuation
            self.max_attenuation = connect_params['max_attenuation']
        except KeyError:
            self.max_attenuation = self.SDR_DEFAULT_MAX_ATTENUATION
        self.sdr.timeout = self.command_timeout
        
        # Reset the system to its preset state
        self.preset()

        # Perform a calibration at the start if requested
        if self.perform_calibration_at_startup:
            self.calibrate_as_needed(forced_calibration=True)
        
        # Set auto alignment to partial to prevent mid-test calibrations
        self.set_and_check_parameter(':CAL:AUTO', 'PART', vartype="str", param_val="PART")

        # If performing calibrations during the run, check at the beginning to hopefully not worry about them during the test
        if self.perform_calibration_during_run:
            self.calibrate_as_needed()
        
        # Set MXA to take IQ Analyzer (Basic) mode
        self.set_and_check_parameter(':INST:SEL', "BASIC")
        #self.preset()
        
        # Set IF path to auto
        self.set_and_check_parameter(':SENS:IFP:AUTO', "ON", vartype="str", param_val="1")

        # Set measurement to waveform and apply defaults
        self.sdr.write(':CONF:WAV')
        self.wait_for_completion()
        self.sdr.write(':CONF:WAV:NDEF')
        self.wait_for_completion()

        # Turn off averaging
        self.set_and_check_parameter(':SENS:WAV:AVER:STAT', "OFF", vartype="str", param_val="0")

        # Turn off continuous measurements (use single measurement mode)
        self.set_and_check_parameter(':INIT:CONT', 'OFF', vartype="str", param_val="0")

        # Set IQ range to auto
        #self.set_and_check_parameter(':SELS:VOLT:IQ:RANG:AUTO', "ON")

        # Set endianness of output data
        self.set_and_check_parameter(':FORM:BORD', "NORM")

        # Set format of output data
        #self.set_and_check_parameter(':FORM', "REAL:32")

        # Set the filter
        #self.set_and_check_parameter(':SENS:WAV:DIF:FILT:TYPE', "FLAT")




        #raise SDR_Error(
        #    0,
        #    "Debug Error",
        #    "Just exiting to perform debug"
        #)
        
        # Successfully connected
        return True
    
    # Return the serial number for this SDR
    def get_serial_number(self):
        start_index = self.idn.find(',',26)+1
        end_index = self.idn.find(',',start_index)
        return self.idn[start_index:end_index]

    # Handle setting the sampling rate
    # NOTE: This does not actually set the sampling rate, rather the IF bandwidth
    # Must query to find the actual sampling rate
    def set_sampling_frequency(self, if_bandwidth):
        # Set the digital IF bandwidth and use flattop window
        if_bandwidth = int(if_bandwidth) # Prevent floating point errors (and we don't need sub Hz resolution)
        self.set_and_check_parameter(':SENS:WAV:DIF:BAND', "{:.6f} MHz".format(if_bandwidth/1e6), vartype="int", param_val=if_bandwidth)
        self.set_and_check_parameter(':SENS:WAV:DIF:FILT:TYPE', 'FLAT')

        # Determine the actual sample rate
        self.find_sample_rate(if_bandwidth)
        return self.samp_freq
    
    # Run a dummy measurement to get sample rate
    def find_sample_rate(self, sample_rate_guess):
        # Get and return the actual sampling frequency
        self.samp_freq = sample_rate_guess # Provide guess

        # Take a dummy measurement to get the sample rate (sample rate will be set)
        self.take_iq_samples(10240,0)
        
        # Return the value if its needed
        return self.samp_freq

    # Get the applied sampling frequency
    # NOTE: With the current configuration, we cannot set the sample rate directly
    # We set the digital IF bandwidth and query the sampling frequency
    def get_sampling_frequency(self):
        # self.samp_freq = float(self.sdr.ask('SENS:WAV:SRAT?')) This command does not work correctly
        # Sample rate is calculated whenever the IF bandwidth is changed
        # Sample rate is also determined and set whenever a measurement is taken
        return self.samp_freq

    # Handle tuning the LO
    def tune_to_frequency(self, freq):
        freq = int(freq) # Prevent floating point errors (and we don't need sub Hz resolution)
        self.set_and_check_parameter(':SENS:FREQ:CENT', "{:.6f} MHz".format(freq/1e6), vartype="int", param_val=freq)
        self.f0 = freq
        return self.f0

    def current_tuned_frequency(self):
        return self.f0
    
    def current_lo_frequency(self):
        return self.f0
    
    def current_dsp_frequency(self):
        return 0 # No DSP on this SDR

    # Handle taking IQ samples
    def take_iq_samples(self, n, n_skip, retries = 5):
        # Calculate and set the measurement time based on the sample rate
        time_buffer = 1.2
        time = (float(n+n_skip)/self.get_sampling_frequency())*time_buffer
        self.set_and_check_parameter(':SENS:WAV:SWE:TIME', "{:.3f} ms".format(time*1e3), vartype="float5", param_val=int(round(1e5*time)))

        # Start the measurement and wait for it to finish
        self.sdr.write(":INIT:WAV")
        self.wait_for_completion()

        # Calculate the timeout time (emperical)
        read_timeout = int(1.1*(n+n_skip)/14000)+1

        # Fetch the data from the buffer
        samples_str = self.long_ask(":FETC:WAV0?", timeout=read_timeout)

        # Fetch data statistics to get sample rate
        data_statistics_str = self.sdr.ask(":FETC:WAV1?")
        data_statistics_str_arr = data_statistics_str.split(',')
        sample_time = float(data_statistics_str_arr[0])
        self.samp_freq = 1/sample_time

        # Convert data string to complex IQ
        samples_str_arr = samples_str.split(',')
        for i in range(len(samples_str_arr)):
            samples_str_arr[i] = float(samples_str_arr[i])
        samples = np.zeros(len(samples_str_arr)//2, dtype=complex)
        for i in range(len(samples)):
            samples[i] = np.complex(
                samples_str_arr[2*i],
                samples_str_arr[2*i+1]
            )
        
        # Remove unwanted samples and return data
        data = samples[n_skip:n_skip+n]
        return data

    # Handle rounding frequencies to reasonable values
    def frequency_round(self, f):
        return int(1e0 * round(f/1e0)) # Round to nearest Hz
    
    # Handle long execution times for requests
    def long_ask(self, ask_string, timeout=60):
        self.sdr.timeout = timeout
        ret_val = self.sdr.ask(ask_string)
        self.wait_for_completion()
        self.sdr.timeout = self.command_timeout
        return ret_val
    
    # Wait for command to finish
    def wait_for_completion(self,delay_time=0.01, resettle_time = 0.01):
        while not self.sdr.ask('*OPC?'):
            time.sleep(delay_time)
        return
        time.sleep(resettle_time)
    
    # Calculate the ideal attentuation for the expected power
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
    
    # Set a parameter, then check that it was set properly
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
        self.sdr.write(cmd)
        self.wait_for_completion()

        # Read the value back
        actual_param_val = self.sdr.ask(ask_cmd)
        self.wait_for_completion()

        # Convert to int/float if necessary
        if vartype == "int":
            actual_param_val = int(float(actual_param_val))
        if vartype == "float6":
            actual_param_val = int(1e6*float(actual_param_val))
        if vartype == "float5":
            actual_param_val = int(1e5*float(actual_param_val))

        # Check that the response is expected
        if not param_val == actual_param_val:
            raise SDR_Error(
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
            pass
    
    # Perform calibration as needed
    def calibrate_as_needed(self, forced_calibration=False):
        # Check if a calibration is necessary
        if not forced_calibration:
            self.wait_for_completion()
            forced_calibration = int(self.sdr.ask(":STAT:QUES:CAL:COND?"))
            self.wait_for_completion()
        
        # Calibrate if needed
        if forced_calibration:
            cal_result = int(self.long_ask("*CAL?"))
            if cal_result:
                raise SDR_Error(
                    0,
                    "Calibration failed",
                    (
                        "Calibration of {} failed...\r\n"
                        "Return code: {}"
                    ).format(self.SDR_NAME,cal_result)
                )

    # Return to preset
    def preset(self):
        # Set the signal analyzer to preset
        #self.sdr.write('*RST')
        # Restore autoalignment
        #self.sdr.write(':CAL:AUTO ON')
        pass

    # Ensure the device is powered down on deletion
    def __del__(self):
        if self.alive:
            self.preset()
            self.sdr.close()
            self.alive = False
    
    """ This functionality is not supported, just set dummy vars """

    # Handle the auto calibrations for the SDR (Note, this is not supported by this SDR)
    def set_auto_dc_offset(self, set_val):
        self.auto_dc_offset = set_val
        return self.auto_dc_offset
    def get_auto_dc_offset(self):
        return self.auto_dc_offset
    def set_auto_iq_imbalance(self, set_val):
        self.auto_iq_balance = set_val
        return self.auto_iq_balance
    def get_auto_iq_imbalance(self):
        return self.auto_iq_balance

    # Handle the gain settings for the SDR (Note, this is not supported by this SDR)
    def set_gain(self, gain):
        self.gain = gain
        return self.gain
    def get_gain(self):
        return self.gain

    # Configure the f0 tuning threshold before error is raised (Note, this is not supported by this SDR)
    def configure_f0_tuning_threshold(self, tuning_threshold):
        self.f0_tuning_threshold = tuning_threshold

    # Handle the clock and sampling frequencies (Note, this is not supported by this SDR)
    def set_clock_frequency(self, clk_freq):
        self.clk_freq = clk_freq
        return self.clk_freq
    def get_clock_frequency(self):
        return self.clk_freq

    # Handle the DSP LO shift settings (Note, this is not supported by this SDR)
    def set_dsp_lo_shift(self, dsp_lo_shift):
        self.dsp_lo_shift = 0
