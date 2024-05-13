import re
import requests
# from typing import Optional, Set
# from urllib.parse import urlparse <- For Python3
#from urlparse import urlparse # Python2
from urllib.parse import urlparse # Python3
import xml.etree.ElementTree as etree
# import time

from sdrcalibrator.lib.equipment.switch.switch_error import RF_Switch_Error


class RF_Switch(object):

    # RF switch constants
    SWITCH_NAME = 'X300'
    SWITCH_DEFAULT_SWAP_INPUTS = False
    SWITCH_DEFAULT_CORRECTION_FACTOR_FILE = None

    def __init__(self):
        self.alive = False

    def connect(self, connect_params, swap_inputs=False):
        self.set_url(connect_params['ip_addr'])
        self.alive = True
        self.swap_inputs = swap_inputs

        self._state_tree = None              # type: Optional[etree.Element]
        self._diagnostics_tree = None        # type: Optional[etree.Element]
        self._state_tags_cache = None        # type: Optional[Set[str]]
        self._diagnostics_tags_cache = None  # type: Optional[Set[str]]

    def set_url(self, base_url):
        # Parse the url
        if not base_url.startswith('http'):
            base_url = 'http://' + base_url
        parsed_url = urlparse(base_url)

        # Get the URL hostname (IP address)
        ip = parsed_url.hostname
        if not ip:
            raise RF_Switch_Error(
                    10,
                    "Could not parse URL for webrelay switch",
                    "Double check the connection parameters"
                )

        # Get the port if one exists (default to 80 if not)
        port = parsed_url.port
        if not port:
            port = 80

        # Determine the connection scheme (http or https)
        scheme = parsed_url.scheme

        # Create the webrelay base URL
        _base_url = scheme + "://" + ip + ':' + str(port)

        # Generate the necessary controller URLs
        self._state_url = _base_url + "/state.xml"
        self._diagnostics_url = _base_url + "/diagnostics.xml"

    def _update_xml_tree(self, tree_url):
        try:
            response = requests.get(tree_url, timeout=1.0)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise RF_Switch_Error(
                    0,
                    "Could not connect to webrelay switch",
                    "Double check the switch connection\r\n{}".format(str(e))
                )

        try:
            return etree.fromstring(response.content)
        except etree.ParseError:
            # Invalid XML, probably an HTML error code page--try naive parse
            regex = b'<title>(.*)</title>'
            try:
                err_body = str(re.search(
                        regex,
                        response.content,
                        re.IGNORECASE
                    ).group(1))
            except AttributeError:
                # Simple regex failed, no big deal
                err_body = "Could not parse XML for error"
            raise RF_Switch_Error(
                    11,
                    "Switch returned invalid XML",
                    err_body + "\r\n{}".format(tree_url)
                )

    def _update_state(self, url=None):
        if url is None:
            url = self._state_url
        self._state_tree = self._update_xml_tree(url)

    @property
    def state_tags(self):
        if self._state_tags_cache is None:
            self._update_state()
            self._state_tags_cache = {
                str(c.tag) for c in self._state_tree.getchildren()
            }
        return self._state_tags_cache

    def state(self, tag):
        self._update_state()
        if tag in self.state_tags:
            return str(self._state_tree.find(tag).text)
        else:
            raise RF_Switch_Error(
                    12,
                    "WebRelay does not have tag {}".format(tag),
                    "Check that the webrelay is in the correct mode."
                )

    def set_relay_state(self, relay, state):
        """Set a relay state.
        Example usage:
            >>> # Turn relay 1 off
            >>> wr.set_relay_state(1, 0)
        """
        assert relay in (1, 2, 3, 4) and state in (0, 1)
        query = "?relay" + str(relay) + "state=" + str(state)
        url = self._state_url + query
        self._update_state(url)

    def relay_state(self, relay):
        assert relay in (1, 2, 3, 4)
        return self.state('relay' + str(relay) + 'state')

    def sensor_state(self, sensor):
        assert sensor in (1, 2, 3, 4)
        return self.state('sensor' + str(sensor))

    # Diagnostics:
    def _update_diagnostics(self, url=None):  # -> None:
        if url is None:
            url = self._diagnostics_url
        self._diagnostics_tree = self._update_xml_tree(url)

    @property
    def diagnostics_tags(self):  # -> Set[str]:
        if self._diagnostics_tags_cache is None:
            self._update_diagnostics()
            self._diagnostics_tags_cache = {
                str(c.tag) for c in self._diagnostics_tree.getchildren()
            }

        return self._diagnostics_tags_cache

    def diagnostics(self, tag):  # def diagnostics(self, tag: str) -> str:
        self._update_diagnostics()
        if tag in self.diagnostics_tags:
            return str(self._diagnostics_tree.find(tag).text)
        else:
            raise RF_Switch_Error(
                    13,
                    "WebRelay does not have tag {}".format(tag),
                    "Check that the webrelay is in the correct mode."
                )

    def reset_diagnostics(self):  # -> None:
        """Reset diagnostics states and counters"""
        query = '?memoryPowerUpFlag=0&devicePowerUpFlag=0&powerLossCounter=0'
        url = self._diagnostics_url + query
        self._update_diagnostics(url)

    def select_sdr(self):
        if self.swap_inputs:
            self.set_relay_state(2, 0)
            self.set_relay_state(1, 1)
        else:
            self.set_relay_state(1, 0)
            self.set_relay_state(2, 1)

    def select_meter(self):
        if self.swap_inputs:
            self.set_relay_state(1, 0)
            self.set_relay_state(2, 1)
        else:
            self.set_relay_state(2, 0)
            self.set_relay_state(1, 1)

    def set_to_default(self):
        self.set_relay_state(2, 0)
        self.set_relay_state(1, 0)

    def __del__(self):
        if self.alive:
            self.set_to_default()


""" class SwitchDriver(object):
    def __init__(self, profile):
        self.profile = profile
        self.webrelay = X300(self.profile['ip_addr'])
        self.webrelay.set_relay_state(2, 0)
        self.webrelay.set_relay_state(1, 0)

    def select_radio(self):
        if self.profile['pwr_mtr_at_open']:
            self.webrelay.set_relay_state(2, 0)
            self.webrelay.set_relay_state(1, 1)
        else:
            self.webrelay.set_relay_state(1, 0)
            self.webrelay.set_relay_state(2, 1)

    def select_meter(self):
        if self.profile['pwr_mtr_at_open']:
            self.webrelay.set_relay_state(1, 0)
            self.webrelay.set_relay_state(2, 1)
        else:
            self.webrelay.set_relay_state(2, 0)
            self.webrelay.set_relay_state(1, 1)

    def __del__(self):
        self.webrelay.set_relay_state(2, 0)
        self.webrelay.set_relay_state(1, 0)
        return
        #self.switch.close() """
