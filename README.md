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
* Select type "Moving" or "Static", more about these below (only moving is properly implemented)
* Select Nordpool prices entity from list to base states on (ENTSO-e are selectable but very untested)
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

> **WORK IN PROGRESS**: This version of entity is still not fully tested, may need some more work to work properly.

`end_hour` can be in the range of 0 to 23 and specifies at what time within 24 hours the amount of active hours shall be selected.

The integration will use `var_end_hour_entity` if supplied and can be interpreted as int, otherwise `end_hour` or the default value.

> **NOT IMPLEMENTED**: No support implemented to use this setting
`split_hours` tell if allowed to find low-cost hours that are not consecutive

## Optional features

### Accept cost

Creates a configuration number entity slider that accepts the first price that has an average price below this value, regardless if there are lower prices further ahead.
<!-- `accept_cost` specifies a price level in the currency of your `nordpool_entity`, that if an "average over a duration" is below this value, it is accepted and used. Even if not the lowest in the range specified. -->

### Accept rate

Creates a configuration number entity slider that accepts the first price that has an average price-rate to Nordpool average below this value, regardless if there are lower prices further ahead.
<!-- `accept_rate` specifies a price rate, that if an "average over a duration" divided by nordpool average (`nordpool_entity.attributes.average`) is below this rate, it is accepted and used. Even if not the lowest in the range specified. E.g. if set to 1 an "average over a duration" <= "nordpool average" is accepted. If 0.5 it has to be half the price of "nordpool average". The idea is to not be as sensitive to offsets I price levels but just a generic rule to accept low section, not just the lowest. -->

This is more dynamic in the sense that it adapts to overall price level, but there are some consideration you need to think of (and extra logic may have to be implemented).

* If Nordpool average happens to be Zero it will not work (duration-average / nordpool-average)
* If any of nordpool-average or duration-average is negative the rate will be negative. If both negative the rate will be positive.

### High cost

This was requested as an extra feature and creates a binary sensor which tell in the current `duration` has the highest cost in the `search_length`. It's to large extent the inverse of the standard `low_cost` entity but without the extra options for `accept_cost` or `accept_rate`.

### Starts at

No extra logic, just creates extra sensor entities that tell in plain values when each of the binary sensors will activate. Same value that is in the extra_attributes of the binary sensor.


The planner types has some additional configuration variables

## Binary sensor attributes

Apart from the true/false if now is the time to turn on electricity usage the sensor provides some attributes.

`starts_at` tell when the next low-point starts

`cost_at` tell what the average cost is at the lowest point identified

`now_cost_rate` tell a comparison current price / best average. Is just a comparison to how much more expensive the electricity is right now compared to the found slot. E.g. 2 means you could half the cost by waiting for the found slot. It will turn UNAVAILABLE if best average is zero

## Usage

Some words should be said about the usage and how it behaves.

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
