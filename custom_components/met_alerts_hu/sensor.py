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
CONF_NAME = 'name'
CONF_REGION = 'region_id'

DEFAULT_NAME = 'MET Alerts HU'
DEFAULT_ICON = 'mdi:weather-lightning-rainy'
DEFAULT_REGION = '101'

SCAN_INTERVAL = timedelta(minutes=20)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_REGION, default=DEFAULT_REGION): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

def _get_icon(argument):
    switcher = {
      "Zivatar": "mdi:weather-lightning-rainy",
      "Felhőszakadás": "mdi:weather-pouring",
      "Széllökés": "mdi:weather-windy",
      "Ónos eső": "mdi:weather-snowy-rainy",
      "Hófúvás": "mdi:weather-snowy-heavy",
    }
    return switcher.get(argument)

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    region_id = config.get(CONF_REGION)

    async_add_devices(
        [METAlertHUSensor(hass, name, region_id )],update_before_add=True)

async def async_get_mdata(self):
    mjson = {}

    url = 'https://www.met.hu/idojaras/veszelyjelzes/hover.php?id=wahx&kod=' + self._region_id
    async with self._session.get(url) as response:
        rsp = await response.text()

    no_newline = rsp.replace("\n","").replace("\r","")
    if not re.search("Nincs",no_newline):
      tags = no_newline.replace("colspan=3>",">{\"alerts\":[<")\
                       .replace("</th></tr>","></th")
      p_json = re.sub(r'/w([1-9])',r'>{"level":"\1","type":"<', tags) \
                 .replace("</tr>","\"}</tr>")
      no_tags = re.sub(r'<.*?>','',p_json)
      f1_json = re.sub(r'\([0-9:]* UTC\)\[wahx\]','"}',no_tags) \
                  .replace("Kiadva: ","],\"updated\":\"")
      f2_json = re.sub(r'\s+',' ',f1_json)
      ff_json = re.sub(r'\s*"\s*','\"',f2_json) \
                .replace("'","\"")

      mjson = json.loads(ff_json)
    return mjson

class METAlertHUSensor(Entity):

    def __init__(self, hass, name, region_id):
        """Initialize the sensor."""
        self._hass = hass
        self._name = name
        self._region_id = region_id
        self._state = None
        self._mdata = []
        self._icon = DEFAULT_ICON
        self._session = async_get_clientsession(hass)

    @property
    def device_state_attributes(self):
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
