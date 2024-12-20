# nordpool_planner custom component for Home Assistant

Requires https://github.com/custom-components/nordpool

> **NOTE**: This is a based on https://github.com/jpulakka/nordpool_diff

[Nord Pool](https://www.nordpoolgroup.com/) gives you spot prices, but making good use of those prices is not easy.
This component provides various a boolean if now is the right time to activate high consumption based on future prices in a specified range. Given a time-span from now and an number of hours forward it searches for the start-time that has the lowest average price over a specified duration window.

Apart from potentially saving some money, this kind of temporal shifting of consumption can also save the environment, because expensive peaks are produced by dirtier energy sources. Also helps solving Europe's electricity crisis.

## Installation

### Option 1: HACS
1. Install and configure https://github.com/custom-components/nordpool first.
2. Go to HACS -> Integrations
3. Click the three dots on the top right and select `Custom Repositories`
4. Enter `https://github.com/dala318/nordpool_planner` as repository, select the category `Integration` and click Add
5. A new custom integration shows up for installation (Nordpool Planner) - install it
6. Restart Home Assistant

### Option 2: Manual

1. Install and configure https://github.com/custom-components/nordpool first.
2. Copy the `nordpool_planner` folder to HA `<config_dir>/custom_components/nordpool_planner/`
3. Restart Home Assistant

### Configuration

> **IMPORTANT NOTE**: With version 2 configuration via `configuration.yaml` is no longer possible. Converting that configuration via "import config" is still not implemented. You wil have to remove the old now broken manual configuration and create a new via the GUI.

During setup some preconditions and selections are needed:

* Give a name to the service
* Select type "Moving" or "Static", more about these below (static is still untested)
* Select Prices entity from list to base states on (ENTSO-e are selectable but not as well tested)
* Select which optional features you want activated, more about these below as well
* Submit and set your configuration parameters

### Moving

Two non-optional configuration entities will be created and you need to set these to a value that matches your consumption profile.

* `search_length` specifies how many hours ahead to search for lowest price.
* `duration` specifies how large window to average when searching for lowest price

The service will then take `duration` number of consecutive prices from the nordpool sensor starting from `now` and average them, then shift start one hour and repeat, until reaching `search_length` from now.
If no optional features activated the `duration` window in the current range of prices within `search_length` with lowest average is selected as cheapest and the `low_cost` entity will turn on if `now` is within those hours.

In general you should set `search_length` to a value how long you could wait to activate high-consumption device and `duration` to how long it have to be kept active. But you have to test different settings to find your optimal configuration.

What should be said is that since the `search_length` window is continuously moving forward for every hour that passes the lowest cost `duration` may change as new prices comes inside range of search. There is also no guarantee that it will keep active for `duration` once activated.

### Static

> **NOT FINISHED**: This version of planner is still not fully functional, need some more work to work properly. For now the planner does not guarantee that the `duration` amount of hours are found inside the search-window.

Two non-optional configuration entities will be created and you need to set these to a value that matches your consumption profile.

* `start_hour` specifies the time of day the searching shall start.
* `end_hour` specifies the time of day the searching shall stop.
* `duration` For now this entity specified how many hours of low-price shall be found inside the search range.

More to come about the expected behavior once it's finished.

## Optional features

### Accept cost

Creates a configuration number entity slider that accepts the first price that has an average price below this value, regardless if there are lower prices further ahead.

### Accept rate

Creates a configuration number entity slider that accepts the first price that has an average price-rate to Nordpool average (range / overall) below this value, regardless if there are lower prices further ahead.

This is more dynamic in the sense that it adapts to overall price level, but there are some consideration you need to think of if If Nordpool-average or range-average happens to be Zero or lower (and extra logic may have to be implemented).

* If both negative it will activate, makes no sense to compare inverted rates (negative / negative = positive, but then above set rate is wanted)
* If both zero it will activate, rate is infinite (division by zero, but average is low)
* If only Nordpool average is zero the rate will not work (no feasible rate can be calculated)

In general if you select to have an `accept_rate` active you should also have an `accept_price` set to at least 0 (or quite low) to make it work as expected as the rate can vary quite much when dividing small numbers.

### High cost

This was requested as an extra feature and creates a binary sensor which tell in the current `duration` has the highest cost in the `search_length`. It's to large extent the inverse of the standard `low_cost` entity but without the extra options for `accept_cost` or `accept_rate`.

### Starts at

No extra logic, just creates extra sensor entities that tell in plain values when each of the binary sensors will activate. Same value that is in the extra_attributes of the binary sensor.

## Binary sensor attributes

Apart from the true/false if now is the time to turn on electricity usage the sensor provides some attributes.

`starts_at` tell when the next low-point starts

`cost_at` tell what the average cost is at the lowest point identified

`now_cost_rate` tell a comparison current price / best average. Is just a comparison to how much more expensive the electricity is right now compared to the found slot. E.g. 2 means you could half the cost by waiting for the found slot. It will turn UNAVAILABLE if best average is zero

## Automation blueprints

### Fixed temp and offset

Import this blueprint and choose the nordpool_planner low & high cost states, and the climate entity you want to control.

[![Fixed temp blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fdala318%2Fnordpool_planner%2Fblob%2Fmaster%2Fblueprints%2Fautomation%2Fthermostat_fixed.yaml)

Now, whenever the price goes up or down, Nordpool Planner will change the temperature based on the price.

### Based on input numbers

First make sure to create two input number entities for `base temperature` and `offset`

Import this blueprint and choose your newly created input numbers, the nordpool_planner low & high cost states, and the climate entity you want to control.

[![Dynamic blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fdala318%2Fnordpool_planner%2Fblob%2Fmaster%2Fblueprints%2Fautomation%2Fthermostat_number.yaml)

Now, whenever you change the input numbers or the price goes up or down, Nordpool Planner will change the temperature based on the price and your set numbers.

## Usage

Some words should be said about the usage of planner and how it behaves.

The search length variable should be set to to a value within which you could accept no high electricity usage, and the ratio window/search should somewhat correspond to the active/passive time of your main user of electricity. Still, the search window for the optimal spot to electricity is moving along in front of current time, so there might be a longer duration of passive usage than the search length. Therefor keeping the search length low (3-5h) should likely be optimal, unless you have a large storage capacity of electricity/heat that can wait for a longer duration and when cheap electricity draw as much as possible.

If to explain by an image, first orange is now, second orange is `search_length` ahead in time, width of green is `duration` and placed where it has found the cheapest average price within the orange.

![image](planning_example.png)

Try it and feedback how it works or if there are any improvement to be done!

### Tuning your settings

I found it useful to setup a simple history graph chart comparing the values from `nordpool`, `nordpool_diff` and `nordpool_planner` like this.

![image](planner_evaluation_chart.png)

Where from top to bottom my named entities are:

* nordpool_diff: duration 3 in search_length 10, accept_cost 2.0
* nordpool_diff: duration 2 in search_length 5, accept_cost 2.0 and accept_rate 0.7
* nordpool average: just a template sensor extracting the nordpool attribute average to an entity for easier tracking and comparisons "{{ state_attr('sensor.nordpool_kwh_se3_sek_3_10_025', 'average') | float }}"
* nordpool
* nordpool_diff:
