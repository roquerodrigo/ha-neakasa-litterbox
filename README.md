# Neakasa Litterbox

<!-- ha-marketplace:exclude-start -->
[![CI](https://github.com/roquerodrigo/ha-neakasa-litterbox/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-neakasa-litterbox/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/roquerodrigo/ha-neakasa-litterbox)](https://github.com/roquerodrigo/ha-neakasa-litterbox/releases/latest)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/roquerodrigo)

[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-neakasa-litterbox&category=integration)
<!-- ha-marketplace:exclude-end -->

Follow your [Neakasa M1](https://www.neakasa.com/) self-cleaning litter box
from Home Assistant: the sand level, what the box is doing, when it needs
attention, and every visit of each cat with its weight. You can also start a
cleaning or leveling cycle and change the box's settings. Home Assistant
connects through the Neakasa cloud with the account you use in the Neakasa
app, using the
[neakasa-litterbox-sdk](https://github.com/roquerodrigo/neakasa-litterbox-sdk)
library.

## Features

- See the sand level and what the box is doing, and get an alert when the
  waste bucket is full or the box needs cleaning. Changes show up within
  seconds.
- Start a cleaning or leveling cycle, and turn auto clean, auto level, silent
  mode and child lock on or off.
- Each cat gets its own device, nested under its litter box, with its photo,
  the weight measured on its last visit, and how many times and for how long
  it used the box today.
- Trigger automations on every cat visit, finished cleaning and finished
  leveling.
- Keep each cat's profile weight up to date, so the box credits each visit to
  the right cat.
- Every litter box and cat on your account appears on its own, and new ones
  show up without a restart.

## Requirements

- Home Assistant 2026.10.0 or newer.
- A Neakasa M1 added to your account in the Neakasa app.
- The email and password of that account, and the region it belongs to.
- Internet access from Home Assistant.

<!-- ha-marketplace:exclude-start -->
## Installation

### Home Assistant Marketplace (recommended)

1. Select the **Open your Home Assistant instance** button above, or go to
   **Settings → Marketplace**, select **Add from link** in the upper-right
   corner, enter `roquerodrigo/ha-neakasa-litterbox` and select **Add**.
2. Select **Install**.
3. Restart Home Assistant.

The Marketplace ships with Home Assistant 2026.11 and later. On older
versions, add the repository to HACS as a custom repository of type
**Integration** and install it from there.

### Manual

1. Download `neakasa_litterbox.zip` from the
   [latest release](https://github.com/roquerodrigo/ha-neakasa-litterbox/releases/latest).
2. Extract it into `config/custom_components/neakasa_litterbox/`.
3. Restart Home Assistant.
<!-- ha-marketplace:exclude-end -->

## Configuration

Go to **Settings → Devices & services → Add integration**, search for
**Neakasa Litterbox** and fill in the form.

| Field    | What to enter                                                    | Default       |
|----------|------------------------------------------------------------------|---------------|
| Email    | The email you sign in with in the Neakasa app                    |               |
| Password | The password of that account                                     |               |
| Region   | United States, Europe or Asia / Pacific, matching your account   | United States |

Each Neakasa account is added once, and brings every litter box on it.

To change the password or the region later, open the integration and select
**Reconfigure**. To use a different account, add the integration again. If
the Neakasa cloud stops accepting the saved password, for example after you
change it in the app, Home Assistant asks you for the new one.

The integration is available in English, Portuguese (Brazil) and Spanish.

## Options

Open the integration and select **Configure**. Saving reloads the
integration.

| Setting                    | Default | Range           | Effect                                                                                  |
|----------------------------|---------|-----------------|-----------------------------------------------------------------------------------------|
| Polling interval (seconds) | 600     | 60 or more      | How often Home Assistant reads everything from the cloud, including the visit history  |
| Statistics lookback (days) | 7       | from 1 to 30    | How far back the visit history goes                                                     |

## Entities

### Each litter box

| Entity            | Type          | Shows                                                                           |
|-------------------|---------------|---------------------------------------------------------------------------------|
| Sand level        | Sensor        | Percentage                                                                      |
| Status            | Sensor        | Idle, Cleaning, Restoring, Leveling or Cat appears                              |
| Visits today      | Sensor        | Visits by any cat since midnight                                                |
| Last visit        | Sensor        | When a cat last used the box                                                    |
| Needs cleaning    | Binary sensor | On when the box asks for a cleaning, off again once a cleaning runs             |
| Waste bucket full | Binary sensor | On when the waste bucket needs emptying                                         |
| Clean now         | Button        | Starts a cleaning cycle                                                         |
| Level now         | Button        | Starts a leveling cycle                                                         |
| Auto clean        | Switch        | Configuration                                                                   |
| Auto level        | Switch        | Configuration                                                                   |
| Silent mode       | Switch        | Configuration                                                                   |
| Child lock        | Switch        | Configuration                                                                   |
| Sand calibration  | Number        | Configuration. Tells the box how full the sand is, from 0 to 100 % in steps of 10 |
| Activity          | Event         | Each visit, cleaning and leveling, see Events below                             |

The firmware and hardware versions are shown on the litter box's device page.

### Each cat

| Entity            | Type   | Shows                                                                              |
|-------------------|--------|------------------------------------------------------------------------------------|
| Photo             | Image  | The photo set in the Neakasa app                                                   |
| Measured weight   | Sensor | The weight measured on the cat's last visit                                        |
| Last visit        | Sensor | When the cat last used the box                                                     |
| Visits today      | Sensor | Visits since midnight                                                              |
| Time in box today | Sensor | Total time of today's visits, in minutes                                           |
| Weight            | Number | Configuration. The weight saved in the cat's profile, from 0.1 to 100              |

The Weight entity writes to the cat's profile in the Neakasa cloud, the same
field the app edits. Weights use the unit of the cat's profile in the app (kg
or lb), and Home Assistant converts them to your display unit.

A cat you delete in the Neakasa app is removed from Home Assistant, with its
entities, at the next update.

## Actions

### Set cat weight (`neakasa_litterbox.set_cat_weight`)

Saves a weight to a cat's profile in the Neakasa cloud. The litter box
compares each visit with the profile weights to tell your cats apart, so a
current weight keeps visits on the right cat. The name, photo and other
profile fields stay as they are, and past visits are not reassigned.

| Field                | Required | Accepts                            |
|----------------------|----------|------------------------------------|
| Cat (`device_id`)    | Yes      | A cat device from this integration |
| Weight (`weight`)    | Yes      | A number greater than zero         |
| Unit (`unit`)        | Yes      | `kg` or `lb`                       |

```yaml
action: neakasa_litterbox.set_cat_weight
data:
  device_id: 0123456789abcdef0123456789abcdef
  weight: 4.8
  unit: kg
```

Choosing a litter box instead of a cat, or a cat deleted in the app, fails
with an error.

## Events

The Activity entity of each litter box fires one event for every record the
Neakasa cloud keeps about the box.

| Event type           | Shown as           | When                         |
|----------------------|--------------------|------------------------------|
| `cat_visit`          | Cat visit          | A cat left the box           |
| `cleaning_completed` | Cleaning completed | A cleaning cycle finished    |
| `leveling_completed` | Leveling completed | A leveling cycle finished    |

Events carry these attributes:

| Attribute                | Event types | Contains                                                                   |
|--------------------------|-------------|----------------------------------------------------------------------------|
| `started_at`, `ended_at` | All         | When it really happened, as reported by the box                            |
| `duration_seconds`       | All         | How long it took                                                           |
| `record_id`              | All         | The cloud's identifier of the record                                       |
| `cat_id`, `cat_name`     | `cat_visit` | The cat. Both are empty when the box did not recognize it, and `cat_name` is empty for a cat deleted in the app |
| `weight`, `weight_unit`  | `cat_visit` | The weight measured on that visit                                          |

Each record is reported once, even across restarts. Activity that happened
while Home Assistant was stopped is reported when it starts again, as long as
it falls inside the statistics lookback. When you first add the integration,
past activity is not reported.

Events arrive with the visit history, at each poll, so an event can fire up
to one polling interval after the activity. Use `started_at` and `ended_at`
for the real time. Past events stay in the history for as long as the
Recorder keeps it (10 days by default).

This automation sends a notification after each visit. Your entity ID
depends on the name of your litter box.

```yaml
triggers:
  - trigger: state
    entity_id: event.neakasa_m1_activity
conditions:
  - condition: state
    entity_id: event.neakasa_m1_activity
    attribute: event_type
    state: cat_visit
actions:
  - action: notify.notify
    data:
      message: >-
        {{ trigger.to_state.attributes.cat_name or 'A cat' }} used the litter box
        ({{ trigger.to_state.attributes.weight }} {{ trigger.to_state.attributes.weight_unit }}).
```

## How it works

Home Assistant keeps a live connection to the Neakasa cloud. Changes the
litter box reports, such as the sand level, the status, the switches and the
alerts, reach Home Assistant within seconds.

At every polling interval (10 minutes by default), Home Assistant also reads
everything from the cloud: the litter boxes and cats on your account, the cat
profiles and photos, and the visit history. Visit counts, last visit, measured
weight, time in box and activity events come from that history, so they
update at each poll and not in real time. Pressing Clean now or Level now, or
saving a cat's weight, triggers an extra poll.

When you turn a switch on or off or move the sand calibration slider, the
new value shows right away, and the litter box confirms it within a few
seconds.

While the box is cleaning or leveling, the cloud does not answer status
requests. The entities keep their last values during that time instead of
becoming unavailable.

The Neakasa cloud allows one session per account, and signing in to the
Neakasa app ends the session Home Assistant was using. Home Assistant signs
in again on its own at the next update with the saved password. It also keeps
its session across restarts, so it starts without signing in again.

## Troubleshooting

**Home Assistant refuses to delete a litter box.** A litter box that is still
on your Neakasa account cannot be deleted, and Home Assistant shows
*Failed to remove device entry, rejected by integration*. Remove the litter
box from your account in the Neakasa app first. Once the cloud stops
reporting it, delete the device in Home Assistant, and its cats go with it.

**Visits show up late.** Visits and activity events arrive at each poll.
Lower the polling interval in the options to see them sooner.

**Visits are credited to the wrong cat.** The box tells cats apart by their
profile weight. Update each cat's Weight entity, or use the Set cat weight
action, with a recent measured weight.

**A cat has no last visit or measured weight.** Its last visit is older than
the statistics lookback. Raise the lookback in the options, up to 30 days.

**Something else is wrong.** Open the integration, select **Enable debug
logging**, reproduce the problem and then select **Disable debug logging** to
download the log. Also download the diagnostics from the integration's menu.
The email and password are removed from that file. Attach both to an
[issue](https://github.com/roquerodrigo/ha-neakasa-litterbox/issues).

## Known limitations

- The Neakasa cloud sometimes closes the live connection. Home Assistant
  reopens it on its own, waiting longer after each failure, up to 5 minutes.
  Polling keeps the entities correct in the meantime.
- The visit history only goes back as far as the statistics lookback, at most
  30 days.

## Support

This integration is built and maintained on personal time, on hardware bought
for the purpose. If it is useful to you, consider
[sponsoring the work](https://github.com/sponsors/roquerodrigo). It keeps the
devices, the testing and the releases coming.

Report bugs and request features in the
[issue tracker](https://github.com/roquerodrigo/ha-neakasa-litterbox/issues).

<!-- ha-marketplace:exclude-start -->
## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and
workflow, and [CODE_STYLE.md](CODE_STYLE.md) for the code conventions.

## Acknowledgements

Started from
[ludeeus/integration_blueprint](https://github.com/ludeeus/integration_blueprint).
Talks to the Neakasa cloud through
[neakasa-litterbox-sdk](https://github.com/roquerodrigo/neakasa-litterbox-sdk).

## License

[MIT](LICENSE)
<!-- ha-marketplace:exclude-end -->
