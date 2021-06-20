import asyncio
import json
import logging
import re
import voluptuous as vol
import aiohttp
from datetime import timedelta

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.discovery import async_load_platform

REQUIREMENTS = [ ]

_LOGGER = logging.getLogger(__name__)

CONF_ATTRIBUTION = "Data provided by met.hu"
CONF_COUNTY = 'county_id'
CONF_NAME = 'name'
CONF_REGION = 'region_id'

DEFAULT_COUNTY = '13'
DEFAULT_ICON = 'mdi:weather-lightning-rainy'
DEFAULT_NAME = 'MET Alerts HU'
DEFAULT_REGION = '101'

SCAN_INTERVAL = timedelta(minutes=20)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_COUNTY, default=DEFAULT_COUNTY): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_REGION, default=DEFAULT_REGION): cv.string,
})

def _get_icon(argument):
    switcher = {
      "Zivatar": "mdi:weather-lightning-rainy",
      "Felhőszakadás": "mdi:weather-pouring",
      "Széllökés": "mdi:weather-windy",
      "Ónos eső": "mdi:weather-snowy-rainy",
      "Hófúvás": "mdi:weather-snowy-heavy",
      "Eső": "mdi:water-alert",
      "Havazás": "mdi:snowflake",
      "Extrém hideg": "mdi:snowflake-alert",
      "Hőség": "mdi:weather-sunny-alert",
      "Tartós, sűrű köd": "mdi:weather-fog",
    }
    return switcher.get(argument)

def _match_line(my_string, matchthis):
    matched_line = [line for line in my_string.split('\n') if matchthis in line]
    return matched_line

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    region_id = config.get(CONF_REGION)
    county_id = config.get(CONF_COUNTY)

    async_add_devices(
        [METAlertHUSensor(hass, name, region_id, county_id )],update_before_add=True)

async def async_get_mdata(self):
    mjson = {}
    ff_json = "{\"alerts\": ["
    a_dict = dict()

    url = 'https://www.met.hu/idojaras/veszelyjelzes/hover.php?id=wahx&kt=' + self._region_id
    async with self._session.get(url) as response:
      rsp = await response.text()

    url = 'https://www.met.hu/idojaras/veszelyjelzes/hover.php?id=wbhx&kod=' + self._county_id
    async with self._session.get(url) as response:
      rsp1 = await response.text()

    lines = rsp.split("\n") + rsp1.split("\n")
    td_lines = [line for line in lines if "<td class=" in line]
    _LOGGER.debug(len(td_lines))

    for i in range(int((len(td_lines))/3)):
      a_type = re.sub(r'<.*?>','',td_lines[i+2]).strip()
      m = re.search(r'(w\d\.gif)',td_lines[i+1])
      a_lvl = m.group(0).replace('w','').replace('.gif','')
      if not a_type in a_dict:
        a_dict[a_type] = a_lvl
        ff_json += "{\"level\":\"" + a_lvl + "\",\"type\":\"" + a_type + "\"}"
        if i != len(td_lines)/3-1:
          ff_json += ","
      _LOGGER.debug(a_type + ": " + a_lvl)

    td_lines = [line for line in lines if ">Kiadva: " in line]
    last_upd1 = re.sub(r'<.*?>','',td_lines[0]).strip()
    last_upd = re.sub(r'(\(.*?\))','',last_upd1) \
               .replace('[wbhx]','') \
               .replace('[wahx]','') \
               .replace("Kiadva: ",'')

    ff_json += "],\"updated\":\"" + last_upd + "\"}"
    _LOGGER.debug(ff_json)

    mjson = json.loads(ff_json)

    return mjson

class METAlertHUSensor(Entity):

    def __init__(self, hass, name, region_id, county_id):
        """Initialize the sensor."""
        self._hass = hass
        self._name = name
        self._region_id = region_id
        self._county_id = county_id
        self._state = None
        self._mdata = []
        self._icon = DEFAULT_ICON
        self._session = async_get_clientsession(hass)

    @property
    def device_state_attributes(self):
        attr = {}
        dominant_value = 0
        #_LOGGER.debug(self._mdata)

        if 'alerts' in self._mdata:
            attr["alerts"] = self._mdata.get('alerts')
            _LOGGER.debug(attr["alerts"])

            for item in self._mdata['alerts']:
                val = item.get('level')
                if int(val) > dominant_value:
                    attr["dominant_met_alert_value"] = int(val)
                    attr["dominant_met_alert"] = item.get('type')
                    dominant_value = int(val)
        else:
            _LOGGER.debug("no alerts")
            _LOGGER.debug(self)
        attr["provider"] = CONF_ATTRIBUTION
        return attr

    @asyncio.coroutine
    async def async_update(self):
        dominant_value = 0

        mdata = await async_get_mdata(self)

        self._mdata = mdata
        if 'alerts' in self._mdata:
            for item in self._mdata['alerts']:
                val = item.get('level')
                if int(val) > dominant_value:
                    dominant_value = int(val)
                    self._icon = _get_icon(item.get('type'))

        self._state = dominant_value
        return self._state

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return self._icon
