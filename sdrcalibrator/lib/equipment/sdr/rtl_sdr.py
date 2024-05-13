from gnuradio import analog, blocks, gr, uhd
import numpy as np
from rtlsdr import RtlSdr

from sdrcalibrator.lib.equipment.sdr.sdr_error import SDR_Error

"""
Supported gain values (29): 
    0.0 0.9 1.4 2.7 3.7 7.7 8.7 12.5 14.4 15.7 
    16.6 19.7 20.7 22.9 25.4 28.0 29.7 32.8 33.8 
    36.4 37.2 38.6 40.2 42.1 43.4 43.9 44.5 48.0 
    49.6
"""


class SDR(object):

    # SDR constants
    SDR_NAME = 'RTL-SDR'
    SDR_DEFAULT_CLOCK_FREQUENCY = 2.4e6
    SDR_DEFAULT_SAMPLING_FREQUENCY = 2.4e6
    SDR_DEFAULT_AUTO_DC_OFFSET = True
    SDR_DEFAULT_AUTO_IQ_IMBALANCE = True
    SDR_DEFAULT_GAIN = 0
    SDR_DEFAULT_F0_TUNING_ERROR_THRESHOLD = 10e3
    SDR_DEFAULT_GAIN_TUNING_THRESHOLD = 2
    SDR_DEFAULT_USE_DSP_LO_SHIFT = False
    SDR_DEFAULT_DSP_LO_SHIFT = -6e6
    SDR_DEFAULT_CONDITIONING_SAMPLES = 1000000
    SDR_DEFAULT_POWER_LIMIT = -15
    SDR_DEFAULT_POWER_SCALE_FACTOR = None
    SDR_DEFAULT_POWER_SCALE_FACTOR_FILE = False

    def __init__(self):
        self.alive = False

    def connect(self, connect_params):
        # Eventually handle multiple devices, for now, just connect to the first
        # Issue is all have the same serial in the beginning
        connected_device_serials = RtlSdr.get_device_serial_addresses()
        if len(connected_device_serials) < 1:
            raise SDR_Error(
                    0,
                    "Could not find a matching RTLSDR",
                    "Try being less restrictive in the search criteria"
                )
        elif len(connected_device_serials) > 1:
            err_body = "Please add/correct identifying information.\r\n"
            for device in connected_device_serials:
                err_body += "SN: {}\r\n".format(device)
            raise SDR_Error(
                    1,
                    ("Found {} devices matching search criteria, " +
                    "need exactly 1").format(
                        len(connected_device_serials)
                    ),
                    err_body
                )
        device_index = RtlSdr.get_device_index_by_serial(connected_device_serials[0])
        self.sdr = RtlSdr(device_index)
        self.alive = True
        self.serial_number = connected_device_serials[0]

        # Set the tuning thresholds
        self.configure_f0_tuning_threshold(self.SDR_DEFAULT_F0_TUNING_ERROR_THRESHOLD)
        self.configure_gain_tuning_threshold(self.SDR_DEFAULT_GAIN_TUNING_THRESHOLD)
    
    # Return the serial number for this SDR
    def get_serial_number(self):
        return self.serial_number

    def set_sampling_frequency(self, samp_freq):
        self.sdr.set_sample_rate(samp_freq)
        #self.sdr.set_bandwidth(samp_freq)
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
        # return actual sampling frequency
        return actual_samp_freq

    def get_sampling_frequency(self):
        return self.sdr.get_sample_rate()

    # Handle the gain settings for the SDR
    def set_gain(self, gain):
        self.sdr.set_gain(gain)
        self.gain = gain
        actual_gain = self.get_gain()
        if not self.is_close(self.gain, actual_gain, self.gain_tuning_threshold):
            raise SDR_Error(
                    14,
                    "Unable to set SDR gain",
                    ("Requested gain: {}dBm\r\n" +
                    "Actual gain: {}dBm\r\n" +
                    "Gain tuning threshold: {}dBm").format(
                        self.gain,
                        actual_gain,
                        self.gain_tuning_threshold
                    )
                )
        return actual_gain

    def get_gain(self):
        return self.sdr.get_gain()

    # Handle tuning the LO
    def tune_to_frequency(self, freq):
        freq = int(freq) # Prevent floating point errors (and we don't need sub Hz resolution)
        retries = 5
        tuned = False
        latest_exception = None
        for i in range(retries):
            try:
                self.sdr.set_center_freq(freq)
            except IOERROR as e:
                latest_exception = e
                continue
            tuned = True
            break
        if not tuned:
            raise SDR_Error(
                    20,
                    "f0 could not be tuned",
                    (
                        "Requested f0 frequency: {}MHz\r\n" +
                        "Failed to tune {} times in a row.\r\n" +
                        "Latest exception:\r\n{}"
                    ).format(
                        self.frequency_round(freq)/1e6,
                        retries,
                        str(latest_exception)
                    )
                )
        self.f0 = freq
        actual_f0 = self.current_tuned_frequency()
        if not self.is_close(self.f0, actual_f0, self.f0_tuning_threshold): #self.f0 == actual_f0:
            raise SDR_Error(
                    20,
                    "f0 improperly tuned",
                    (
                        "Requested f0 frequency: {}MHz\r\n" +
                        "Actual f0 frequency: {}MHz\r\n" +
                        "Frequency tuning threshold: {}MHz"
                    ).format(
                        self.frequency_round(self.f0)/1e6,
                        self.frequency_round(actual_f0)/1e6,
                        self.frequency_round(self.f0_tuning_threshold)/1e6
                    )
                )
        return self.f0

    def current_tuned_frequency(self):
        return self.sdr.get_center_freq()
    
    def current_lo_frequency(self):
        return self.sdr.get_center_freq()
    
    def current_dsp_frequency(self):
        return 0 # No DSP on this SDR

    # Handle taking IQ samples (8294400 seems to be the max)
    def take_iq_samples(self, n, n_skip, retries = 5):
        o_retries = retries
        while True:
            try:
                # RTLSDR must take samples in multiples of 512
                sample_multiple = 512
                total_samples = n+n_skip
                total_samples += (sample_multiple-(total_samples%sample_multiple))
                samples = self.sdr.read_samples(total_samples)
            except IOError as e:
                if retries > 0:
                    retries -= 1
                    continue
                else:
                    raise SDR_Error(
                            30,
                            "Failed to acquire IQ samples",
                            "Data acquisition failed {} times in a row... Latest acquisitionerror:\r\n{}".format(
                                o_retries,
                                str(e)
                            )
                        )
            data = np.array(samples[n_skip:n+n_skip])
            if not len(data) == n:
                if retries > 0:
                    retries = retries - 1
                else:
                    raise SDR_Error(
                            30,
                            "Failed to acquire IQ samples",
                            ("Data acquisition failed {} times in a row... Latest acquisition:" +
                            "Expected IQ data length: {}\r\n" +
                            "Actual IQ data length: {}").format(
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
    
    # Configure the f0 and gain tuning threshold before error is raised
    def configure_f0_tuning_threshold(self, tuning_threshold):
        self.f0_tuning_threshold = tuning_threshold
    def configure_gain_tuning_threshold(self, tuning_threshold):
        self.gain_tuning_threshold = tuning_threshold
    
    # Handle checking if two values are within a threshold
    def is_close(self, val1, val2, threshold):
        dif = abs(val1-val2)
        return (dif < threshold)

    # Handle the powering down of the SDR
    def power_down(self):
        if self.alive:
            self.sdr.close()
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

    # Handle the clock and sampling frequencies (Note, this is not supported by this SDR)
    def set_clock_frequency(self, clk_freq):
        self.clk_freq = clk_freq
        return self.clk_freq
    def get_clock_frequency(self):
        return self.clk_freq

    # Handle the DSP LO shift settings (Note, this is not supported by this SDR)
    def set_dsp_lo_shift(self, dsp_lo_shift):
        self.dsp_lo_shift = 0