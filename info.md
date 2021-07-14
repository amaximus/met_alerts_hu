[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

<p><a href="https://www.buymeacoffee.com/6rF5cQl" rel="nofollow" target="_blank"><img src="https://camo.githubusercontent.com/c070316e7fb193354999ef4c93df4bd8e21522fa/68747470733a2f2f696d672e736869656c64732e696f2f7374617469632f76312e7376673f6c6162656c3d4275792532306d6525323061253230636f66666565266d6573736167653d25463025394625413525413826636f6c6f723d626c61636b266c6f676f3d6275792532306d6525323061253230636f66666565266c6f676f436f6c6f723d7768697465266c6162656c436f6c6f723d366634653337" alt="Buy me a coffee" data-canonical-src="https://img.shields.io/static/v1.svg?label=Buy%20me%20a%20coffee&amp;message=%F0%9F%A5%A8&amp;color=black&amp;logo=buy%20me%20a%20coffee&amp;logoColor=white&amp;labelColor=b0c4de" style="max-width:100%;"></a></p>

# Home Assistant custom component for meteo alerts in Hungary

This custom component gathers regular and special meteo alerts from met.hu (valid only for Hungary).

The state of the sensor will be the alert level of most dominant alert. The name of the alert with highest alert level
will also be added into a dedicated attribute.

The sensor will also report in attributes the values of all other meteo alerts, if there are any.

#### Installation
The easiest way to install it is through [HACS (Home Assistant Community Store)](https://github.com/hacs/integration),
search for <i>MET Alerts Hungary</i> in the Integrations.<br />

#### Configuration:
Define sensor with the following configuration parameters:<br />

---
| Name | Optional | `Default` | Description |
| :---- | :---- | :------- | :----------- |
| name | **Y** | `met_alerts_hu` | name of the sensor |
| region_id | **Y** | `` | region identifier |
| county_id | **Y** | `` | county identifier |
---

region_id can found as kt value in the URL when hovering on the region at [MET Vészjelzés](https://www.met.hu/idojaras/veszelyjelzes/index.php). When set it will display the current weather alerts.

county_id can be found as serial value of the county when counties are sorted alphabetically (1: reserved, 2: Baranya;...; 20: Zala). When set it will display the special meteo conditions e.g. forecasts from next 0-24 hours.

If you don't want to combine the two (weather alerts and forecasts) but still want to have both information, define two sensors, one with region_id set and one with county_id set.

![Meteo alerts attributes](https://raw.githubusercontent.com/amaximus/met_alerts_hu/main/met_alerts_attrs.png)

#### Example
```
platform: met_alerts_hu
name: 'MET alerts'
region_id: 101 # Budapest
county_id: 13 # Pest county
```

#### Lovelace UI
If you want to show the dominant alert use the following:

```
type: conditional
conditions:
  - entity: sensor.met_alerts
    state_not: '0'
card:
  type: custom:button-card
  size: 30px
  styles:
    label:
      - font-size: 90%
    card:
      - height: 80px
    icon:
      - color: >
          [[[
            var met_level = states['sensor.met_alerts'].state;
            if ( met_level == 0 ) {
              return "green";
            } else if ( met_level == 1 ) {
              return "var(--paper-item-icon-active-color)";
            } else if ( met_level == 2 ) {
              return "orange";
            } else if ( met_level == 3 ) {
              return "red";
            }
            return "black";
          ]]]
  label: >
    [[[
      var met_alert = states['sensor.met_alerts'].attributes.dominant_met_alert;
      return met_alert;
    ]]]
  show_label: true
  show_name: false
  entity: sensor.met_alerts
  color_type: icon
```

![Most dominant meteo alert example](https://raw.githubusercontent.com/amaximus/met_alerts_hu/main/met_alert.png)

If you want to show all alerts use the following (please note that this height of the card
will allow only three alerts to be shown):
```
type: conditional
conditions:
  - entity: sensor.met_alerts
    state_not: '0'
card:
  type: custom:button-card
  size: 30px
  styles:
    label:
      - font-size: 90%
    card:
      - height: 80px
  label: >
    [[[
      var label = ""
      var icolor = "black"
      var met_alerts = states['sensor.met_alerts'].attributes.alerts;
      for (var k=0; k < states['sensor.met_alerts'].attributes.nr_of_alerts; k++) {
        if ( met_alerts[k].level == 1 ) {
          icolor = "var(--paper-item-icon-active-color)";
        } else if ( met_alerts[k].level == 2 ) {
          icolor = "orange";
        } else if ( met_alerts[k].level == 3 ) {
          icolor = "red";
        }
        label += `<ha-icon icon="` + met_alerts[k].icon +
                 `" style="width: 28px; height: 28px; color:` + icolor +
                  (states['sensor.met_alerts'].attributes.nr_of_alerts == 1 ? `; margin-bottom: 10px;">` : `;">`) +
                  `</ha-icon>&nbsp;` +
                  (states['sensor.met_alerts'].attributes.nr_of_alerts == 1 ? `<br>` : ``) +
                 `<span>` + met_alerts[k].type + `</span><br>`;
      }
      return label;
    ]]]
  show_label: true
  show_name: false
  show_icon: false
  entity: sensor.met_alerts
  color_type: icon
```
![All meteo alerts example](https://raw.githubusercontent.com/amaximus/met_alerts_hu/main/met_alert2.png)

## Thanks

Thanks to all the people who have contributed!

[![contributors](https://contributors-img.web.app/image?repo=amaximus/pollen_hu)](https://github.com/amaximus/pollen_hu/graphs/contributors)
