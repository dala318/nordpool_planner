# nordpool_planner custom component for Home Assistant

Requires https://github.com/custom-components/nordpool

> **NOTE**: This is a based on https://github.com/jpulakka/nordpool_diff

[Nord Pool](https://www.nordpoolgroup.com/) gives you spot prices, but making good use of those prices is not easy.
This component provides various a boolean if now is the right time to activate high consumption based on future prices
in a specified range. Given a time-span from now and an number of hours forward it searches for the start-time that has the
lowest average price over a specified duration window.

Apart from potentially saving some money, this kind of temporal shifting of consumption can also save the environment,
because expensive peaks are produced by dirtier energy sources. Also helps solving Europe's electricity crisis.

## Installation

### Option 1: HACS
1. Go to HACS -> Integrations
2. Click the three dots on the top right and select `Custom Repositories`
3. Enter `https://github.com/dala318/nordpool_planner` as repository, select the category `Integration` and click Add
4. A new custom integration shows up for installation (Nordpool Planner) - install it
5. Restart Home Assistant

### Option 2: Manual

1. Install and configure https://github.com/custom-components/nordpool first.
2. Copy the `nordpool_planner` folder to HA `<config_dir>/custom_components/nordpool_planner/`
3. Restart HA. (Skipping restarting before modifying configuration would give "Integration 'nordpool_diff' not found"
   error message from the configuration.)
4. Add the following to your `configuration.yaml` file:

    ```yaml
    sensor:
      - platform: nordpool_planner
        nordpool_entity: sensor.nordpool_kwh_fi_eur_3_095_024
    ```

   Modify the `nordpool_entity` value according to your exact nordpool entity ID.

5. Restart HA again to load the configuration. Now you should see `nordpool_diff_triangle_10` sensor, where
   the `triangle_10` part corresponds to default values of optional parameters, explained below.

## Optional parameters

Optional parameters to configure include `search_length`, `duration` and `accept_level`, defaults are `10`, `2`
and `0.0`, respectively:

 ```yaml
 sensor:
   - platform: nordpool_planner
     nordpool_entity: sensor.nordpool_kwh_fi_eur_3_095_024
     search_length: 10
     duration: 2
     accept_level: 0.0
 ```

`search_length` can be in the range of 2 to 24 and specifies how many hours ahead to serach for lowest price.

`duration` specifies how large window in hours to slide forward in search for a minimum price.

`accept_level` specifies a price level, that if an average over search window is below this value, is accepted and used. Even if not the lowest in the range specified.

## Attributes

Apart from the true/false if now is the time to turn on electricity usage the sensor provides an attribute `start_at` which tell when the next low-point starts

## Usage

Some words should be said about the usage and how it behaves.

The search length variable should be set to to a value within which you could accept no high electricity usage, and the ratio window/search should somewhat correspond to the active/passive time of your main user of electricity. Still, the search window for the optimal spot to electricity is moving along in front of corrent time, so there might be a longer duration of passive usage than the search length. Therefor keeping the search length low (3-5h) should likely be optimal, unless you have a large storage capacity of electricity/heat that can wait for a longer duration and when cheap electricity draw as much as possible.
