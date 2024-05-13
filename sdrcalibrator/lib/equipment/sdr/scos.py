import swagger_client
from swagger_client.rest import ApiException
from swagger_client import AdminScheduleEntry
import json, tarfile, tempfile
import urllib3
import time
import numpy as np
from matplotlib import pyplot as plt

from sdrcalibrator.lib.equipment.sdr.sdr_error import SDR_Error


class SDR(object):

    # SDR constants
    SDR_NAME = 'SCOS Sensor'
    SDR_DEFAULT_CLOCK_FREQUENCY = 48e6
    SDR_DEFAULT_SAMPLING_FREQUENCY = 12e6
    SDR_DEFAULT_AUTO_DC_OFFSET = True
    SDR_DEFAULT_AUTO_IQ_IMBALANCE = True
    SDR_DEFAULT_GAIN = 0
    SDR_DEFAULT_F0_TUNING_ERROR_THRESHOLD = 1e6
    SDR_DEFAULT_USE_DSP_LO_SHIFT = False
    SDR_DEFAULT_DSP_LO_SHIFT = -6e6
    SDR_DEFAULT_CONDITIONING_SAMPLES = 10000000
    SDR_DEFAULT_POWER_LIMIT = -15
    SDR_DEFAULT_POWER_SCALE_FACTOR = None
    SDR_DEFAULT_POWER_SCALE_FACTOR_FILE = False

    # def __init__(self):

    def connect(self, connect_params):
        # Create a swagger client configuration
        swagger_config = swagger_client.Configuration()
        swagger_config.api_key["Token"] = connect_params['api_key']
        swagger_config.api_key_prefix["Token"] = connect_params['api_key_prefix']
        swagger_config.host = connect_params['host_url']
        swagger_config.verify_ssl = connect_params['verify_ssl']
        swagger_config.logger_file = connect_params['logger_file']
        swagger_config.debug = connect_params['debug']

        # Suppress insecure request warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Connect and get the capabilities
        try:
            # Create the API instance
            self.api_instance = swagger_client.V1Api(swagger_client.ApiClient(swagger_config))
            
            # Get the capabilities of the scos sensor
            capabilities_json = self.api_instance.v1_capabilities_read("", _preload_content=False)
            self.capabilities = json.loads(capabilities_json.data)
        except ApiException as e:
            raise SDR_Error(
                    0,
                    "Unable to connect to SCOS sensor",
                    "API error:\r\n{}".format(str(e))
                )

        # Made it here with no errors => successfully connected
        return True
    
    # Handle taking IQ samples
    def take_iq_samples(self, n, n_skip, retries = 5):
        # Check that there isn't too many data points
        if n > 15e6:
            raise SDR_Error(
                    0,
                    "Too many data points for SCOS sensor",
                    "SCOS sensor will only take data for 1 second, resulting in 15.36e6 samples.\r\n" + 
                    "Requested samples must be less than this length. (Note: the number of samples\r\n" + 
                    "to skip is ignored in SCOS so this is not contributing to the total samples.)"
                )

        # Create the action in scos
        schedule_name = "sdrcal_{}".format(
                time.strftime('%Y-%m-%d_%H_%M_%S')
            )
        schedule_entry = AdminScheduleEntry(
            name=schedule_name, action="acquire_m4s_700MHz_Verizon_DL"#, relative_stop=1, interval=1
        )
        scos_response = self.api_instance.v1_schedule_create(schedule_entry)

        # Wait for completion of the action
        time.sleep(1)
        scos_response = self.api_instance.v1_schedule_read(schedule_name)
        # wait for completion
        while scos_response.is_active:
            time.sleep(1)
            scos_response = self.api_instance.v1_schedule_read(schedule_name)
        
        # Get the data and sigmf from scos
        got_sigmf = False
        for i in range(retries):
            try:
                time.sleep(1.5)
                scos_response = self.api_instance.v1_tasks_completed_archive(schedule_name, _preload_content=False)
                sigmf_data = scos_response.data
                got_sigmf = True
                break
            except Exception as e:
                continue
        if not got_sigmf:
            raise SDR_Error(
                0,
                "Failed to retrieve data from SCOS",
                "Failted to retrieve data from SCOS {} consecutive times. Latest exception:\r\n".format(retries) + 
                "{}".format(str(e))
            )

        # Delete the task/data to prevent clogging the sensor
        scos_response = self.api_instance.v1_tasks_completed_delete(schedule_name)
        scos_response = self.api_instance.v1_schedule_delete(schedule_name)
        
        # Write the data to a temporary file for extraction
        with tempfile.NamedTemporaryFile() as all_sigmf_file:
            all_sigmf_file.write(sigmf_data)
            all_sigmf_tar = tarfile.open(all_sigmf_file.name)

            # Extract the sigmf meta data
            sigmf_meta_file = all_sigmf_tar.extractfile("{}_1/{}_1.sigmf-meta".format(schedule_name,schedule_name))
            sigmf_meta_str  = sigmf_meta_file.read().decode("utf-8")
            sigmf_meta      = json.loads(sigmf_meta_str)
            
            # Determine the correct data type
            buf_datatype  = None
            if sigmf_meta['global']['core:datatype'] == 'rf32_le': # Real 32bit float, little endian
                buf_datatype  = np.dtype(np.float32)
                buf_datatype = buf_datatype.newbyteorder('<')
            if sigmf_meta['global']['core:datatype'] == 'rf32_be': # Real 32bit float, big endian
                buf_datatype  = np.dtype(np.float32)
                buf_datatype = buf_datatype.newbyteorder('>')
            if sigmf_meta['global']['core:datatype'] == 'cf32_le': # Complex 32bit float, little endian
                buf_datatype  = np.dtype(np.complex64)
                buf_datatype = buf_datatype.newbyteorder('<')
            if sigmf_meta['global']['core:datatype'] == 'cf32_be': # Complex 32bit float, big endian
                buf_datatype  = np.dtype(np.complex64)
                buf_datatype = buf_datatype.newbyteorder('>')
            
            # Panic if datatype not found
            if buf_datatype is None:
                raise SDR_Error(
                    0,
                    "Unknown data type returned",
                    "SCOS sensor returned an unknown data type:\r\n" + 
                    "    Returned datatype: {}".format(sigmf_meta['global']['core:datatype'])
                )

            # Extract the data
            sigmf_data_file = all_sigmf_tar.extractfile("{}_1/{}_1.sigmf-data".format(schedule_name,schedule_name))
            sigmf_data_buf  = sigmf_data_file.read()
            sigmf_data      = np.frombuffer(sigmf_data_buf, dtype=buf_datatype)
            
            # Close the temporary files to trigger for deletion
            sigmf_data_file.close()
            sigmf_meta_file.close()
            all_sigmf_tar.close()
            all_sigmf_file.close()

        # Grab the important metadata parameters
        self.set_sampling_frequency(sigmf_meta['global']['core:sample_rate'])
        self.tune_to_frequency(sigmf_meta['captures'][0]['core:frequency'])
        received_n_points = sigmf_meta['annotations'][-1]['core:sample_start']+sigmf_meta['annotations'][-1]['core:sample_count']

        # Check that the correct number of points was received
        if not len(sigmf_data) == received_n_points:
            raise SDR_Error(
                0,
                "Received unexpected number of data points",
                "SCOS sensor sent an unexpected number of data points:\r\n" + 
                "    Metadata: {}\r\n".format(received_n_points) + 
                "    Received: {}".format(len(sigmf_data))
            )
        print(len(sigmf_data))
        #Debug plot
        fft_data = np.split(sigmf_data,5)
        fft_freqs = np.arange(len(fft_data[0]), dtype=np.float32)
        fft_freqs *= (self.get_sampling_frequency()/len(fft_data[0]))
        fft_freqs -= (self.get_sampling_frequency()/2)
        fft_freqs += self.current_tuned_frequency()
        plt.plot(fft_freqs,fft_data[0])
        plt.plot(fft_freqs,fft_data[1])
        plt.plot(fft_freqs,fft_data[2])
        plt.plot(fft_freqs,fft_data[3])
        plt.show()
        assert False

        # Cut the data to the requested size
        iq_data = sigmf_data[:n]
        if not len(iq_data) == n:
            raise SDR_Error(
                0,
                "Imporper number of samples retained",
                "An improper number of samples was cut from the original data sent from SCOS:\r\n" + 
                "    Retained:  {}\r\n".format(len(iq_data)) + 
                "    Requested: {}\r\n".format(n) + 
                "    Original:  {}\r\n".format(len(sigmf_data))
            )
        #print(len(iq_data))
        #print("Data sample:")
        #for i in range(10):
        #    print("  {0:02d}: {1}".format(i,iq_data[i]))
        
        # Return the iq data
        return iq_data
    
    """
    EVERY THING BELOW THIS LEVEL IS STILL A DUMMY FUNCTION
    EITHER WAITING FOR AN IMPLEMENTATION OR WITHOUT AN 
    ABILITY TO IMPLEMENT THE FUNCTIONALITY
    """
    
    # Return the serial number for this SDR
    def get_serial_number(self):
        return "dummy_scos_serial_number"

    # Handle the clock and sampling frequencies
    def set_clock_frequency(self, clk_freq):
        self.clk_freq = clk_freq
        return self.clk_freq

    def get_clock_frequency(self):
        return self.clk_freq

    def set_sampling_frequency(self, samp_freq):
        self.samp_freq = samp_freq
        return self.samp_freq

    def get_sampling_frequency(self):
        return self.samp_freq

    # Handle the auto calibrations for the B210
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

    # Handle the gain settings for the SDR
    def set_gain(self, gain):
        self.gain = gain
        return self.gain

    def get_gain(self):
        return self.gain

    # Configure the f0 tuning threshold before error is raised
    def configure_f0_tuning_threshold(self, tuning_threshold):
        self.f0_tuning_threshold = tuning_threshold

    # Handle tuning the LO
    def tune_to_frequency(self, f):
        # Round the f0 to avoid errors when sweeping frequencies
        self.f0 = self.frequency_round(f)
        self.lo_freq = self.f0
        self.dsp_freq = 0

        # Return the center frequency
        return self.f0

    def current_tuned_frequency(self):
        return self.f0
    
    def current_lo_frequency(self):
        return self.lo_freq
    
    def current_dsp_frequency(self):
        return self.dsp_freq

    # Handle the DSP LO shift settings
    def set_dsp_lo_shift(self, dsp_lo_shift):
        self.dsp_lo_shift = dsp_lo_shift

    # Handle rounding frequencies to reasonable values
    def frequency_round(self, f):
        return int(1e0 * round(f/1e0)) # Round to nearest Hz

    # Handle the powering down of the SDR
    def power_down(self):
        return

    # Ensure the device is powered down on deletion
    def __del__(self):
        self.power_down()
