import numpy as np
import time
try:
    from sallinuxwrap import SALLinux
except ImportError:
    raise ImportError

from sdrcalibrator.lib.equipment.sdr.sdr_error import SDR_Error


class SDR(object):

    # SDR constants
    SDR_NAME = 'Keysight'

    # Determine values
    SDR_DEFAULT_CLOCK_FREQUENCY = 48e6
    SDR_DEFAULT_SAMPLING_FREQUENCY = 10e6
    SDR_DEFAULT_AUTO_DC_OFFSET = True
    SDR_DEFAULT_AUTO_IQ_IMBALANCE = True
    SDR_DEFAULT_GAIN = 0
    SDR_DEFAULT_F0_TUNING_ERROR_THRESHOLD = 1e6
    SDR_DEFAULT_USE_DSP_LO_SHIFT = False
    SDR_DEFAULT_DSP_LO_SHIFT = -6e6
    SDR_DEFAULT_CONDITIONING_SAMPLES = 0
    SDR_DEFAULT_POWER_LIMIT = -15
    SDR_DEFAULT_POWER_SCALE_FACTOR = None
    SDR_DEFAULT_POWER_SCALE_FACTOR_FILE = False

    # Internal constants
    MAX_SAMPLES_PER_BLOCK = 4098
    SAL_TIME_DATA_CALLBACK = None
    MAX_ATTENUATION = 40 # 62 with Surveyor 4D
    MIN_ATTENUATION = 0
    MIN_MEASUREMENT_WAIT_TIME = 0.3

    points_measured = 0

    # def __init__(self):

    def connect(self, connect_params):
        # Grab the IP address and initialize sensor objects
        ip_addr = connect_params['ip_addr']
        self.keysight_sensor = None
        self.tuner = None
        self.measurement = None

        self.last_sal_scale_factor = 0

        # Try and connect to the sensor
        try:
            # Get the sensor object from the SAL
            sensor_handle = SALLinux.salHandlePointer()
            sms_handle = 0   # Not connecting to an SMS, so this will be 0
            port_num = 0     # Use 0 to connect to the sensor's default port.
            options = 0     # Reserved for future use. Should be set to 0
            application_name = 'sdr_calibrator'
            ret = SALLinux.salConnectSensor3(sensor_handle.cast(), sms_handle, ip_addr, port_num, application_name, options)
            sensor = sensor_handle.value()

            # Recycle the handle
            del sensor_handle

            # Basic validation and store the sensor object
            assert ret == SALLinux.SAL_ERR_NONE
            assert sensor != 0
            self.keysight_sensor = sensor

            # Lock the sensor for our use
            SALLinux.salLockResource(self.keysight_sensor, SALLinux.salResource_tuner)

            # Get the sensors tuner object and store for use later
            tuner = SALLinux.salTunerParms()
            ret = SALLinux.salGetTuner(sensor, tuner)
            assert ret == SALLinux.SAL_ERR_NONE
            self.tuner = tuner

            # Pull the serial number for the sensor
            serial_number_max_length = 50
            sal_char_arr = SALLinux.charArray(serial_number_max_length)
            ret = SALLinux.salGetSensorAttribute(sensor, SALLinux.salATTRIBUTE_SERIAL_NUMBER, sal_char_arr, serial_number_max_length)
            assert ret == SALLinux.SAL_ERR_NONE
            self.serial_number = ''
            i = 0
            while (sal_char_arr[i] != '\x00'):
                self.serial_number += sal_char_arr[i]
                i += 1
            assert self.serial_number != ''
        except Exception:
            raise SDR_Error(
                    2,
                    "Failed to connect to Keysight SDR",
                    "Failed to finish the initialization routine during " +
                    "connection to Keysight sensor..." +
                    "    IP address: {}".format(ip_addr)
                )
        
        return True
    
    # Return the serial number for this SDR
    def get_serial_number(self):
        return self.serial_number
    
    def update_tuner_parameters(self):
        # Get the current tuner for the sensor to retrieve parameters
        current_tuner = SALLinux.salTunerParms()
        SALLinux.salGetTuner(self.keysight_sensor, current_tuner)

        # Update the internal parameters
        self.sampling_frequency = current_tuner.sampleRate
        self.f0 = current_tuner.centerFrequency
        self.attenuation = current_tuner.attenuation        # This is mapped to gain
        self.gain = self.attenuation_to_gain(self.attenuation)
        self.mixer_level = current_tuner.mixerLevel         # This is currently unused/default only
        self.antenna = current_tuner.antenna                # This is currently unused/default only
        self.preamp_enabled = current_tuner.preamp          # This is currently unused/default only
        self.sdram_writing = current_tuner.sdramWriting     # This is currently unused/default only

    def set_sampling_frequency(self, samp_freq):
        # Intify the sample rate (don't need sub-Hz resolution on this)
        samp_freq = int(samp_freq)
        print(samp_freq)

        # Update the tuner to update the sensor
        self.tuner.sampleRate = samp_freq
        ret = SALLinux.salSetTuner(self.keysight_sensor, self.tuner)

        # Make sure there wasn't an error in updating the sensor
        assert ret == SALLinux.SAL_ERR_NONE

        self.update_tuner_parameters()
        print(self.sampling_frequency)
        
        # Check back with the sensor to make sure that the sample frequency was set properly and return it
        return self.get_sampling_frequency()

    def get_sampling_frequency(self):
        backup_sampling_frequency = self.sampling_frequency
        self.update_tuner_parameters() # Retrieves all tuner parameters from the sensor
        #print(self.sampling_frequency)
        if self.sampling_frequency > 0:
            return self.sampling_frequency
        return backup_sampling_frequency
    
    def gain_to_attenuation(self, gain):
        return int(self.MAX_ATTENUATION-gain)
    def attenuation_to_gain(self, attenuation):
        return int(self.MAX_ATTENUATION-attenuation)

    def set_gain(self, gain):
        # Intify the gain and convert to attenuation
        gain = int(gain)
        attenuation = self.gain_to_attenuation(gain)

        # Validity check the attenuation
        """
        if attenuation > self.MAX_ATTENUATION:
            attenuation = self.MAX_ATTENUATION
        if attenuation < self.MIN_ATTENUATION:
            attenuation = self.MIN_ATTENUATION
        """

        # Update the tuner to update the sensor
        self.tuner.attenuation = attenuation
        ret = SALLinux.salSetTuner(self.keysight_sensor, self.tuner)

        self.update_tuner_parameters()
        print(self.gain)

        # Make sure there wasn't an error in updating the sensor
        assert ret == SALLinux.SAL_ERR_NONE
        
        # Check back with the sensor to make sure that the sample frequency was set properly and return it
        return self.get_gain()

    def get_gain(self):
        self.update_tuner_parameters() # Retrieves all tuner parameters from the sensor
        return self.gain
    
    def get_attenuation(self):
        self.update_tuner_parameters() # Retrieves all tuner parameters from the sensor
        return self.attenuation

    # Handle tuning the LO
    def tune_to_frequency(self, f):
        # Round the f0 to avoid errors when sweeping frequencies
        new_f0 = int(self.frequency_round(f))

        # Update the tuner to update the sensor
        self.tuner.centerFrequency = new_f0
        ret = SALLinux.salSetTuner(self.keysight_sensor, self.tuner)

        # Make sure there wasn't an error in updating the sensor
        assert ret == SALLinux.SAL_ERR_NONE
        
        # Check back with the sensor to make sure that the sample frequency was set properly and return it
        return self.current_tuned_frequency()

    def current_tuned_frequency(self):
        self.update_tuner_parameters() # Retrieves all tuner parameters from the sensor
        return self.f0
    
    def current_lo_frequency(self):
        self.update_tuner_parameters() # Retrieves all tuner parameters from the sensor
        return self.f0
    
    def current_dsp_frequency(self):
        self.update_tuner_parameters() # Retrieves all tuner parameters from the sensor
        return 0 # No DSP on this SDR

    # Handle taking IQ samples
    def take_iq_samples(self, n, n_skip, retries = 5):
        o_retries = retries
        while True:
            # Calculate the sample block size and expected number of blocks
            if n < self.MAX_SAMPLES_PER_BLOCK:
                block_size = n
            else:
                block_size = self.MAX_SAMPLES_PER_BLOCK
            expected_num_blocks = int(np.ceil(n/block_size))

            # Calculate the approximate wait time (and add a buffer)
            wait_time = float(n)/self.sampling_frequency
            wait_time *= 2
            if wait_time < self.MIN_MEASUREMENT_WAIT_TIME:
                wait_time = self.MIN_MEASUREMENT_WAIT_TIME

            # Create the time acquisition parameters object using the currently tuned parameters
            timedata_parms = SALLinux.salTimeDataParms3()
            timedata_parms.centerFrequency = self.f0
            timedata_parms.sampleRate = self.sampling_frequency
            timedata_parms.numSamples = int(n)
            timedata_parms.numTransferSamples = block_size
            timedata_parms.dataType = SALLinux.salCOMPLEX_16

            # Create the measurement handle and recover the measurement object for retrieving the data
            measure_handle = SALLinux.salHandlePointer()
            ret = SALLinux.salRequestTimeData3(measure_handle.cast(), self.keysight_sensor, timedata_parms, self.SAL_TIME_DATA_CALLBACK)
            assert ret == SALLinux.SAL_ERR_NONE
            self.measurement = measure_handle.value()

            # Allow measurement to proceed and results to be processed
            time.sleep(wait_time) # Possibly change to polling stateEventIndicator in data header, but this is fine for now
            # Use the following if we are doing a continuous measurement (i.e. setting numSamples = 0)
            #ret = SALLinux.salSendTimeDataCommand(self.measurement, SALLinux.salTimeDataCmd_abort)  # Do we need this one?
            #assert ret == SALLinux.SAL_ERR_NONE
            
            """ Keeping for reference - data_header array
                salUInt64 	sequenceNumber             
                salDataType 	dataType             
                salUInt32 	numSamples             
                salFloat64 	scaleToVolts             
                salStateEventMask 	stateEventIndicator             
                salChangeMask 	changeIndicator             
                salUInt32 	timestampSeconds             
                salUInt32 	timestampNSeconds             
                salLocation 	location             
                salAntennaType 	antenna             
                salFloat64 	attenuation             
                salFloat64 	centerFrequency             
                salFloat64 	sampleRate             
                salFloat64 	sensorVariance             
                salFloat64 	triggerLatency             
                size_t 	userWorkspace             
                salUInt32 	timeAlarms             
                salErrorType 	error             
                char 	errorInfo [SAL_MAX_ERROR_STRING]             
                salTriggerSlope 	triggerSlope             
                salHandle 	measHandle             
                salHandle 	sensorHandle
            """
            # Initialize the data arrays and buffer sizes
            data_header = SALLinux.salTimeData()
            iq_data_points = block_size * 2 # individual I or Q points
            iq_data_bytes = iq_data_points * 2 # 2 bytes per data point
            iq_data = SALLinux.shortArray(iq_data_points) # Transfer buffer
            i_wav = [] # Full python array for data
            q_wav = [] # Full python array for data
            sal_scale_factor = 0
            self.last_sal_scale_factor = 0

            # Keep grabbing data until the end is reached
            retrieval_count = 0 # Number of retrieval attempts
            retrieved_blocks = 0 # Number of blocks successfully retrieved
            while True:
                retrieval_count += 1 # Increment the retrieval attempt counter

                # Use count to prevent endless retrieval failures
                if retrieval_count > 4*expected_num_blocks:
                    #print("here1")
                    break # Just break out of the loop, error handling will happen later

                # Use retrieved_blocks to monitor the number of retrieved blocks (minimum blocks == 1 + ending block)
                if retrieved_blocks > 2*expected_num_blocks:
                    #print("here2")
                    break # Just break out of the loop, error handling will happen later if needed

                # Try and grab the next block
                ret = SALLinux.salGetTimeData(self.measurement, data_header, iq_data, iq_data_bytes)

                # If there was an error, try again (retrieval count will prevent endless attempts)
                if not ret == SALLinux.SAL_ERR_NONE:
                    print(str(ret))
                    continue

                # Check if there is data in the retrieved block
                if data_header.numSamples > 0:
                    # Pull out the data
                    for i in range(data_header.numSamples):
                        i_wav.append(iq_data[i*2])
                        q_wav.append(iq_data[i*2+1])

                    # Save the scale factor for later
                    sal_scale_factor = data_header.scaleToVolts
                    #print(type(sal_scale_factor))

                    # Actually save the scale factor to retrieve it later
                    self.last_sal_scale_factor = sal_scale_factor

                    # Increment the retrieved blocks counter
                    retrieved_blocks += 1

                # Check if this is the last block
                #print(data_header.stateEventIndicator)
                #print(SALLinux.salSTATE_LAST_BLOCK)
                if data_header.stateEventIndicator&16 and SALLinux.salSTATE_LAST_BLOCK&16:
                    #print("here3")
                    break
            
            # Close the measurement in preparation for a possible next one
            SALLinux.salClose(self.measurement)
            self.measurement = None

            # Check to make sure data was retrieved
            assert retrieved_blocks > 0

            # Combine data into an IQ waveform and scale
            full_iq = np.asarray(i_wav) + 1j*np.asarray(q_wav)
            full_iq *= sal_scale_factor

            # Check to make sure enough data was retrieved
            if len(full_iq) < n:
                print(n)
                print(len(full_iq))
                if retries > 0:
                    retries = retries - 1
                    continue
                else:
                    # Dummy array to not kill compression...
                    full_iq = np.zeros(n, dtype=np.complex) + 1e-6
                    #assert False
            
            self.points_measured += 1
            print("    Points measured: {}".format(self.points_measured))

            # Return the data (ensuring we only return what we need)
            print(type(full_iq))
            print(type(full_iq[0]))
            return full_iq[:n]
    
    def get_last_scale_factor(self):
        return self.last_sal_scale_factor

    # Handle rounding frequencies to reasonable values
    def frequency_round(self, f):
        return int(1e0 * round(f/1e0)) # Round to nearest Hz

    # Handle the powering down of the SDR
    def power_down(self):
        if self.measurement is not None:
            SALLinux.salClose(self.measurement)
        if self.keysight_sensor is not None:
            SALLinux.salUnlockResource(self.keysight_sensor, SALLinux.salResource_tuner)
            SALLinux.salClose(self.keysight_sensor)
            self.keysight_sensor = None
            print("successful close")
        return

    # Ensure the device is powered down on deletion
    def __del__(self):
        self.power_down()


    
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

    # Configure the f0 tuning threshold before error is raised (Note, this is not supported by this SDR)
    def configure_f0_tuning_threshold(self, tuning_threshold):
        self.f0_tuning_threshold = tuning_threshold

    # Handle the clock and sampling frequencies (Note, this is not supported by this SDR)
    def set_clock_frequency(self, clk_freq):
        self.clk_freq = clk_freq
        return self.get_clock_frequency()
    def get_clock_frequency(self):
        return self.clk_freq

    # Handle the DSP LO shift settings (Note, this is not supported by this SDR)
    def set_dsp_lo_shift(self, dsp_lo_shift):
        self.dsp_lo_shift = 0