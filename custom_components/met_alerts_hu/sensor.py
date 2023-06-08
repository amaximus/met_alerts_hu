import asyncio
import json
import logging
import re
import voluptuous as vol
import aiohttp
from datetime import datetime
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
CONF_LANG = 'lang'
CONF_NAME = 'name'
CONF_REGION = 'region_id'

DEFAULT_COUNTY = ''
DEFAULT_ICON = 'mdi:weather-lightning-rainy'
DEFAULT_LANG = 'hu'
DEFAULT_NAME = 'MET Alerts HU'
DEFAULT_REGION = ''

SCAN_INTERVAL = timedelta(minutes=20)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_COUNTY, default=DEFAULT_COUNTY): cv.string,
    vol.Optional(CONF_LANG, default=DEFAULT_LANG): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_REGION, default=DEFAULT_REGION): cv.string,
})

def _get_icon(argument):
    switcher = {
      "Zivatar": "mdi:weather-lightning-rainy",
      "Thunderstorm": "mdi:weather-lightning-rainy",
      "Felhőszakadás": "mdi:weather-pouring",
      "Torrential rain": "mdi:weather-pouring",
      "Széllökés": "mdi:weather-windy",
      "Wind Gust": "mdi:weather-windy",
      "Ónos eső": "mdi:weather-snowy-rainy",
      "Freezing rain": "mdi:weather-snowy-rainy",
      "Hófúvás": "mdi:weather-snowy-heavy",
      "Blowing snow": "mdi:weather-snowy-heavy",
      "Eső": "mdi:water-alert",
      "Rain": "mdi:water-alert",
      "Havazás": "mdi:snowflake",
      "Snowfall": "mdi:snowflake",
      "Extrém hideg": "mdi:snowflake-alert",
      "Low temperature": "mdi:snowflake-alert",
      "Hőség": "mdi:weather-sunny-alert",
      "High temperature": "mdi:weather-sunny-alert",
      "Tartós, sűrű köd": "mdi:weather-fog",
      "Dense fog": "mdi:weather-fog",
    }
    return switcher.get(argument)

def _match_line(my_string, matchthis):
    matched_line = [line for line in my_string.split('\n') if matchthis in line]
    return matched_line

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    lang = config.get(CONF_LANG)
    region_id = config.get(CONF_REGION)
    county_id = config.get(CONF_COUNTY)

    async_add_devices(
        [METAlertHUSensor(hass, name, lang, region_id, county_id )],update_before_add=True)

async def async_get_mdata(self):
    mjson = {}
    ff_json = "{\"alerts\": ["
    a_dict = dict()
    rsp = ''
    rsp1 = ''
    id1 = 'wahx'
    id2 = 'wbhx'

    if self._lang.lower() == 'en':
      id1 = 'waex'
      id2 = 'wbex'

    if len(self._region_id) != 0:
      url = 'https://www.met.hu/idojaras/veszelyjelzes/hover.php?id=' + id1 + '&kod=' + self._region_id
      async with self._session.get(url) as response:
        rsp = await response.text()

    if len(self._county_id) != 0:
      url = 'https://www.met.hu/idojaras/veszelyjelzes/hover.php?id=' + id2 + '&kod=' + self._county_id
      async with self._session.get(url) as response:
        rsp1 = await response.text()

    lines = rsp.split("\n") + rsp1.split("\n")
    td_lines = [line for line in lines if "<td class=" in line]
    j = 0 # number of duplicated alerts

    for i in range(int((len(td_lines))/3)):
      a_type = re.sub(r'<.*?>','',td_lines[i*3+2]).strip()
      m = re.search(r'(w\d\.gif)',td_lines[i*3+1])
      if m != None:
        a_lvl = m.group(0).replace('w','').replace('.gif','')
      else:
        a_lvl = '0'
      if not a_type in a_dict:
        a_dict[a_type] = a_lvl
        ff_json += "{\"level\":\"" + a_lvl + \
                   "\",\"type\":\"" + a_type + \
                   "\",\"icon\":\"" + _get_icon(a_type) + "\"}"
        if i != len(td_lines)/3-1:
          ff_json += ","
      else:
        j += 1
      _LOGGER.debug(str(i) + "/" + str(j) + ": " + a_type + ": " + a_lvl)
    ff_json += "],\"nr_of_alerts\":\"" + str(int(len(td_lines)/3) - j) + "\""

    td_lines = [line for line in lines if ">Kiadva: " in line]
    if len(td_lines) > 0:
      last_upd1 = re.sub(r'<.*?>','',td_lines[0]).strip()
      last_upd = re.sub(r'(\(.*?\))','',last_upd1) \
                .replace('[wbex]','') \
                .replace('[wbhx]','') \
                .replace('[waex]','') \
                .replace('[wahx]','') \
                .replace("Kiadva: ",'')
    else:
      now = datetime.now()
      last_upd = now.strftime("%Y-%m-%d %H:%M")

    ff_json += ",\"updated\":\"" + last_upd + "\"}"
    ff_json_final = ff_json.replace('},]','}]')
    _LOGGER.debug(ff_json_final)

    mjson = json.loads(ff_json_final)

    return mjson

class METAlertHUSensor(Entity):

    def __init__(self, hass, name, lang, region_id, county_id):
        """Initialize the sensor."""
        self._hass = hass
        self._name = name
        self._lang = lang
        self._region_id = region_id
        self._county_id = county_id
        self._state = None
        self._mdata = []
        self._icon = DEFAULT_ICON
        self._session = async_get_clientsession(hass)

    @property
    def extra_state_attributes(self):
        attr = {}
        dominant_value = 0

        if 'alerts' in self._mdata:
            attr["alerts"] = self._mdata.get('alerts')

            for item in self._mdata['alerts']:
                val = item.get('level')
                if int(val) > dominant_value:
                    attr["dominant_met_alert_value"] = int(val)
                    attr["dominant_met_alert"] = item.get('type')
                    dominant_value = int(val)
            attr["updated"] = self._mdata.get('updated')
            attr["nr_of_alerts"] = self._mdata.get('nr_of_alerts')
        else:
            _LOGGER.debug("no alerts")
        attr["provider"] = CONF_ATTRIBUTION
        return attr

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
