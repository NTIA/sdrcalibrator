# from gnuradio import analog, blocks, gr, uhd
from gnuradio import uhd
import numpy as np

from sdrcalibrator.lib.equipment.sdr.sdr_error import SDR_Error


class SDR(object):

    # SDR constants
    SDR_NAME = 'B210'
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

    def __init__(self):
        self.dsp_freq = 0
        self.f0_tuning_threshold = self.SDR_DEFAULT_F0_TUNING_ERROR_THRESHOLD

    def connect(self, connect_params):
        # Save the connection parameters
        self.connect_params = connect_params
        
        # Search for devices based on search parameters
        search_criteria = uhd.device_addr_t()
        search_criteria['type'] = "b200"
        #search_criteria['product'] = 'B210'
        #for k, v in connect_params:
        #    search_criteria[k] = v
        for k in connect_params.keys():
            search_criteria[k] = connect_params[k]
        found_devices = list(uhd.find_devices(search_criteria))

        # Ensure only a single device was found
        if len(found_devices) < 1:
            raise SDR_Error(
                    0,
                    "Could not find a matching B210",
                    "Try being less restrictive in the search criteria"
                )
        if len(found_devices) > 1:
            err_body = "Please add/correct identifying information.\r\n"
            for device in found_devices:
                err_body += "\r\n{}\r\n".format(device.to_pp_string())
            raise SDR_Error(
                    1,
                    "Found {} devices matching search criteria, " +
                    "need exactly 1".format(
                        len(found_devices)
                    ),
                    err_body
                )

        # Connect to the B210
        try:
            self.usrp = uhd.usrp_source(device_addr=found_devices[0],
                                        stream_args=uhd.stream_args("fc32"),
                                        recv_frame_size=1024)
            self.serial_number = self.usrp.get_usrp_info().get("mboard_serial")
        except Exception as e:
            raise e
            raise SDR_Error(
                    2,
                    "Failed to connect to B210",
                    "Failed to finish the initialization routine during " +
                    "connection to B210..."
                )
        # Set the channel
        #self.usrp.set_subdev_spec("A:A", 0) #RF A: RX2
        self.usrp.set_subdev_spec("A:B") #RF B: RX2
        # Set the input port
        #self.usrp.set_antenna("RX2")
        self.usrp.set_antenna("TX/RX")
        return True
    
    # Return the serial number for this SDR
    def get_serial_number(self):
        return self.serial_number

    # Handle the clock and sampling frequencies
    def set_clock_frequency(self, clk_freq):
        #self.clk_freq = clk_freq
        #return
        # Save operating point for refresh the driver
        set_tries = 5
        for i in range(set_tries+1):
            if i >= set_tries:
                raise RuntimeError

            try:
                previous_gain = self.get_gain()
                previous_freq = self.current_tuned_frequency()
                self.dsp_lo_shift = self.current_dsp_frequency()

                # Delete and refresh the driver
                del self.usrp
                if not self.connect(self.connect_params):
                    raise RuntimeError

                # Proceed with reconfiguration
                self.usrp.set_clock_rate(clk_freq)
                self.clk_freq = clk_freq
                actual_clk_freq = self.get_clock_frequency()
                if not self.frequency_round(self.clk_freq) == self.frequency_round(actual_clk_freq):
                    raise SDR_Error(
                            10,
                            "Clock frequency not set correctly",
                            ("Requested freq: {}\r\n" +
                            "Actual freq: {}").format(
                                self.frequency_round(self.clk_freq),
                                self.frequency_round(actual_clk_freq)
                            )
                        )
                    
                # Reset the gain and frequency
                self.set_gain(previous_gain)
                self.tune_to_frequency(previous_freq)
                
                return actual_clk_freq
            except RuntimeError:
                raise RuntimeError
            except Exception as e:
                print("Failed on attempt {}. Trying again...".format(i+1))
                continue

    def get_clock_frequency(self):
        return self.usrp.get_clock_rate()

    def set_sampling_frequency(self, samp_freq):
        self.usrp.set_samp_rate(samp_freq)
        self.samp_freq = samp_freq
        actual_samp_freq = self.get_sampling_frequency()
        if not self.frequency_round(self.samp_freq) == self.frequency_round(actual_samp_freq):
            raise SDR_Error(
                    11,
                    "Sampling frequency not set correctly",
                    ("Requested freq: {}\r\n" +
                    "Actual freq: {}").format(
                        self.frequency_round(self.samp_freq)/1e6,
                        self.frequency_round(actual_samp_freq)/1e6
                    )
                )
        self.clk_freq = self.get_clock_frequency()
        return actual_samp_freq

    def get_sampling_frequency(self):
        return self.usrp.get_samp_rate()

    # Handle the auto calibrations for the B210
    def set_auto_dc_offset(self, set_val):
        self.usrp.set_auto_dc_offset(set_val)
        self.auto_dc_offset = set_val
        if self.auto_dc_offset is not self.get_auto_dc_offset():
            raise SDR_Error(
                    12,
                    "Unable to set auto DC offset correction"
                )
        return self.get_auto_dc_offset()

    def get_auto_dc_offset(self):
        return self.auto_dc_offset

    def set_auto_iq_imbalance(self, set_val):
        self.usrp.set_auto_iq_balance(set_val)
        self.auto_iq_balance = set_val
        if self.auto_iq_balance is not self.get_auto_iq_imbalance():
            raise SDR_Error(
                    13,
                    "Unable to set auto IQ imbalance correction"
                )
        return self.get_auto_iq_imbalance()

    def get_auto_iq_imbalance(self):
        return self.auto_iq_balance

    # Handle the gain settings for the SDR
    def set_gain(self, gain):
        self.usrp.set_gain(gain)
        self.gain = gain
        actual_gain = self.get_gain()
        if not self.gain == actual_gain:
            raise SDR_Error(
                    14,
                    "Unable to set SDR gain",
                    ("Requested gain {}dBm\r\n" +
                    "Actual gain {}dBm").format(
                        self.gain,
                        actual_gain
                    )
                )
        return actual_gain

    def get_gain(self):
        return self.usrp.get_gain()

    # Configure the f0 tuning threshold before error is raised
    def configure_f0_tuning_threshold(self, tuning_threshold):
        self.f0_tuning_threshold = tuning_threshold

    # Handle tuning the LO
    def tune_to_frequency(self, f):
        # Round the f0 to avoid errors when sweeping frequencies
        self.f0 = self.frequency_round(f)

        # Create and send the tune request
        tune_request = uhd.tune_request(self.f0, self.dsp_lo_shift)
        tune_result = self.usrp.set_center_freq(tune_request)

        # Extract the LO and DSP frequencies
        try:
            tr = str(tune_result)
            tr = tr[
                    tr.index("Actual RF  Freq:")+17:
                ]
            self.lo_freq = float(
                    tr[
                        :tr.index(" ")
                    ]
                )*1e6
            tr = tr[
                    tr.index("Actual DSP Freq:")+17:
                ]
            self.dsp_freq = float(
                    tr[
                        :tr.index(" ")
                    ]
                )*1e6
        except Exception:
            raise SDR_Error(
                    21,
                    "Could not parse tune result",
                    (
                        "Tune result was not as expected:\r\n" +
                        "{}"
                    ).format(tune_result)
                )

        # Check the actual tuned frequency matches and return
        self.f0 = self.current_tuned_frequency()
        if abs(self.f0-f) > self.f0_tuning_threshold:
            raise SDR_Error(
                    20,
                    "f0 improperly tuned",
                    (
                        "Requested f0 frequency: {}MHz\r\n" +
                        "Actual f0 frequency: {}MHz"
                    ).format(
                        self.frequency_round(f)/1e6,
                        self.frequency_round(self.f0)/1e6
                    )
                )
        # Return the center frequency
        return self.f0

    def current_tuned_frequency(self):
        return self.usrp.get_center_freq()
    
    def current_lo_frequency(self):
        return self.lo_freq
    
    def current_dsp_frequency(self):
        return self.dsp_freq

    # Handle the DSP LO shift settings
    def set_dsp_lo_shift(self, dsp_lo_shift):
        self.dsp_lo_shift = dsp_lo_shift

    # Handle taking IQ samples
    def take_iq_samples(self, n, n_skip, retries = 5):
        o_retries = retries
        while True:
            samples = self.usrp.finite_acquisition(n+n_skip)
            data = np.array(samples[n_skip:])
            if not len(data) == n:
                if retries > 0:
                    retries = retries - 1
                else:
                    raise SDR_Error(
                            30,
                            "Failed to acquire IQ samples",
                            "Data acquisition failed {} times in a row... Latest acquisition:" +
                            "Expected IQ data length: {}\r\n" +
                            "Actual IQ data length: {}".format(
                                o_retries,
                                n,
                                len(data)
                            )
                        )
            else:
                return data

    # Handle rounding frequencies to reasonable values
    def frequency_round(self, f):
        return int(1e0 * round(f/1e0)) # Round to nearest Hz

    # Handle the powering down of the SDR
    def power_down(self):
        return

    # Ensure the device is powered down on deletion
    def __del__(self):
        self.power_down()
