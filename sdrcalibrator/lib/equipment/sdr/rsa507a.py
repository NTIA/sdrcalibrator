from sdrcalibrator.lib.equipment.sdr.resources.tekrsa.rsa_api import *
import numpy as np
import time

from sdrcalibrator.lib.equipment.sdr.sdr_error import SDR_Error


class SDR(object):

    # SDR constants
    SDR_NAME = 'Tektronix RSA507A'
    SDR_DEFAULT_CLOCK_FREQUENCY = 56e6
    SDR_DEFAULT_SAMPLING_FREQUENCY = 56e6
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

    def __init__(self):
        self._is_available = False

        # Allowed SR's: 56e6, 28e6, 14e6, ...
        self.ALLOWED_SR = []
        # Allowed BW's : 40e6, 20e6, 10e6, ...
        self.ALLOWED_BW = []

        self.max_sample_rate = 56.0e6
        self.max_attenuation = 51 # dBm, constant
        self.min_attenuation = 0 # dBm, constant
        self.max_frequency = None
        self.min_frequency = None
        
        allowed_sample_rate = self.max_sample_rate # maximum cardinal SR
        allowed_acq_bw = 40.0e6 # maximum corresponding BW

        while allowed_sample_rate > 13670.0:
            # Note: IQ Block acquisition allows for lower SR's. This
            # loop adds only the SR's available for BOTH IQ block and
            # IQ streaming acquisitions.
            self.ALLOWED_SR.append(allowed_sample_rate)
            self.ALLOWED_BW.append(allowed_acq_bw)
            allowed_acq_bw /= 2
            allowed_sample_rate /= 2

        # Create SR/BW mapping dictionary
        # With SR as keys, BW as values
        self.sr_bw_map = {self.ALLOWED_SR[i] : self.ALLOWED_BW[i] for i in range(len(self.ALLOWED_SR))}
        
        #self.dsp_freq = 0
        #self.f0_tuning_threshold = self.SDR_DEFAULT_F0_TUNING_ERROR_THRESHOLD
        print("Remember to copy cyusb.conf to /etc/cyusb.conf")
        print("Remember to run 'sudo chmod 777 /dev/bus/usb/004/002'")

    def connect(self, connect_params):
        # Save the connection parameters
        self.connect_params = connect_params

        if self._is_available:
            return True

        search_connect()

        print("Using the following Tektronix RSA device:")
        print(DEVICE_GetNomenclature())

        try:
            self.get_constraints()
        except ImportError:
            print("Tektronix RSA API not available - disabling radio")
            return False
        
        # Set autoattenuation off and preamp on
        CONFIG_SetAutoAttenuationEnable(False)
        self.ref_level=-25
        CONFIG_SetReferenceLevel(self.ref_level)
        #CONFIG_SetReferenceLevel(-6)
        CONFIG_SetRFPreampEnable(True)
        DEVICE_Stop()
        DEVICE_Run()

        try:
            self._is_available = True
            return True
        except Exception as err:
            raise err
            return False

    @property
    def is_available(self):
        return self._is_available

    def get_constraints(self):
        self.min_frequency = CONFIG_GetMinCenterFreq()
        self.max_frequency = CONFIG_GetMaxCenterFreq()
    
    # Return the serial number for this SDR
    def get_serial_number(self):
        return "DEADBEEF"

    def set_sampling_frequency(self, sample_rate):
        if sample_rate > self.max_sample_rate:
            err_msg = f"Sample rate {sample_rate} too high. Max sample rate is {self.max_sample_rate}."
            print(err_msg)
            raise Exception(err_msg)
        if sample_rate not in self.ALLOWED_SR:
            allowed_sample_rates_str = ", ".join(self.ALLOWED_SR)
            err_msg = (f"Requested sample rate {sample_rate} not in allowed sample rates."
                + " Allowed sample rates are {allowed_sample_rates_str}")
            #logger.error(err_msg)
            raise Exception(err_msg)
        # set bandwidth according to SR setting
        bw = self.sr_bw_map.get(sample_rate)
        IQSTREAM_SetAcqBandwidth(bw)
        msg = "set Tektronix RSA sample rate: {:.1f} samples/sec"
        print(msg.format(IQSTREAM_GetAcqParameters()[1]))

    def get_sampling_frequency(self):
        return IQSTREAM_GetAcqParameters()[1]
    
    def gain_to_attenuation(self, gain):
        return int(gain - self.max_attenuation)
    def attenuation_to_gain(self, attenuation):
        return int(self.max_attenuation+attenuation)

    # Handle the gain settings for the SDR
    def set_gain(self, gain):
        gain = int(gain)
        attenuation = self.gain_to_attenuation(gain)

        #CONFIG_SetAutoAttenuationEnable(False)
        #CONFIG_SetReferenceLevel(-30)
        #CONFIG_SetReferenceLevel(-6)
        #CONFIG_SetRFPreampEnable(True)


        CONFIG_SetRFAttenuator(attenuation)
        self.ref_level=-25-attenuation
        CONFIG_SetReferenceLevel(self.ref_level)
        #CONFIG_SetRFPreampEnable(True)
        DEVICE_Stop()
        DEVICE_Run()
        msg = "Set Tektronix RSA attenuation: {:.1f} dB"
        print(msg.format(CONFIG_GetRFAttenuator()))
        #print("Preamp: {}".format(str(CONFIG_GetRFPreampEnable())))
        
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
        attenuation = CONFIG_GetRFAttenuator()
        return self.attenuation_to_gain(attenuation)

    # Handle tuning the LO
    def tune_to_frequency(self, f):
        # Round the f0 to avoid errors when sweeping frequencies
        self.f0 = self.frequency_round(f)

        CONFIG_SetCenterFreq(self.f0)
        #time.sleep(1)

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
        return CONFIG_GetCenterFreq()
    
    def current_lo_frequency(self):
        return self.current_tuned_frequency()
    
    def current_dsp_frequency(self):
        return 0

    # Handle taking IQ samples
    def take_iq_samples(self, n, n_skip, retries = 5):
        print(
            f"acquire_time_domain_samples starting num_samples = {n}"
        )
        # Determine correct time length for num_samples based on current SR
        total_samples = n + n_skip
        durationMsec = int((total_samples/self.get_sampling_frequency())*1000)+1
        # Calibration data not currently recomputed since calibration not done
        #self.recompute_calibration_data()
        #db_gain = self.sensor_calibration_data["gain_sensor"]
        # Placeholder db_gain:
        print(f"Number of retries = {retries}")
        
        while True:
            try:
                result_data = iqstream_tempfile(
                    self.current_tuned_frequency(),
                    self.ref_level,#self.gain_to_ref_level(self.get_gain()),
                    self.sr_bw_map[self.get_sampling_frequency()],
                    durationMsec
                )
                received_samples = len(result_data)
                if received_samples < total_samples:
                    print(
                        f"Only {received_samples} samples received. Expected {total_samples} samples."
                    )
                    if retries > 0:
                        print("Retrying time domain iq measurement.")
                        retries = retries - 1
                        continue
                    else:
                        error_message = "Max retries exceeded."
                        print(error_message)
                        raise RuntimeError(error_message)
                data = result_data[n_skip : n + n_skip]

                return data
            except Exception as e:
                raise e
                if retries > 0:
                    print("Retrying time domain iq measurement.")
                    retries = retries - 1
                    continue
                else:
                    error_message = "Max retries exceeded."
                    print(error_message)
                    raise RuntimeError(error_message)

    # Handle rounding frequencies to reasonable values
    def frequency_round(self, f):
        return int(1e0 * round(f/1e0)) # Round to nearest Hz

    # Handle the powering down of the SDR
    def power_down(self):
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
