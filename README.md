# High Performance Pings

Leverage the corptools data to notify via discord certain events at a corp/alliance level

filter on/off regions/const/system/corps/alliances/types/strucutre type/notification type via admin. end specific notifications to different places via webhooks

configurable @ settings

# What Pings are Available

## Structures

- Attack/Reinforce
  - StructureLostShields
  - StructureLostArmor
  - StructureUnderAttack
- low fuel ()
- abandoned ()
- destroyed (StructureDestroyed)
- low power (StructureWentLowPower)
- anchoring (StructureAnchoring)
- unanchoring (StructureUnanchoring)
- high power (StructureWentHighPower)
- transfer (OwnershipTransferred)

## POS

- Attack/Reinforce
  - TowerAlertMsg

## Sov

- Attacks
  - SovStructureReinforced
  - EntosisCaptureStarted
- POS Anchoring (AllAnchoringMsg) - Currently disabled by CCP

## Moons

- Extraction Started (MoonminingExtractionStarted)
- Extraction Complete (MoonminingExtractionFinished)
- Laser Fired (MoonminingLaserFired)
- Auto Fracture (MoonminingAutomaticFracture)

## HR

- New Application (CorpAppNewMsg)

## Corporation Projects

- Started (CorporationGoalCreated)
- Closed (CorporationGoalClosed)
- Completed (CorporationGoalCompleted)
- Expired (CorporationGoalExpired)
- Limit Reached (CorporationGoalLimitReached)

# Installation

1. This app requires Corp-Tools to leverage Notification Data, install this first.

- Assumptions made:
  - All characters that can provide notifications for the pings are loaded into the Character Audit module with at least notifications and roles modules enabled
  - All corporations that need to be monitored for fuel have a structures token loaded in the Corporation Audit Module.
  - All corporations that need to get fuel/lo/gas notifications have an assets token loaded in the Corporation Audit Module.

1. `pip install allianceauth-corptools-pinger`
1. Add `'pinger',` to your `INSTALLED_APPS` in your projects `local.py`
1. Migrate, Collectstatic, Restart Auth.
1. Configure Pinger at `/admin/pinger/pingerconfig/1/change/`
1. Verify pinger is setup with `python manage.py pinger_stats`

# Fuel Pings

Fuel pings are driven by **Fuel Ping Configs** in admin (`/admin/pinger/fuelpingconfig/`). A config is a named policy: where it applies, which webhooks it pings, and a list of thresholds saying what to say at how many days of fuel left.

## Where a config applies

Each config has four location filters — regions, constellations, systems and structures. A structure matches if it is itself in `structures`, **or** its system is in `systems`, **or** its constellation is in `constellations`, **or** its region is in `regions`. A config with all four filters empty will match structures anywhere. Note: since structures can be deleted, a config with only structures can become a general config if all structures are removed.

When there are multiple configs matching a structure, a specificity logic applies: structures is the most specific level, then systems, then constellations, then regions. If a config matches a structure at system level AND a [threshold](#thresholds) is active, another config that matches at region level won't be considered. If there are multiple configs matching at the same level, all of those which have a threshold active apply. If the `blocks_broader` field is set to `True`, that config will prevent more general configs from being considered even if this config does not have any firing thresholds.

With the `always_ping` field, you can flag a config that will be considered even if there is a more specific one. This is useful for cases when there are some system or constellation level configs in place but you want the region config to still be considered. This also works when the more specific config has `block_broader=True`.

For a ping to be sent to a webhook, this needs to be added in the list of webhook of a config. Note that each webhook still applies its own corporation / alliance / region filters on top as well as the `no_at_pings` field which strips all the mentions from the message.

A config left with no webhooks is discarded before being considered, as it could prevent other configs from being applied.

## Thresholds

Every config has a list of thresholds and each threshold is characterized by a `days` and a number of other attributes. The `days` field determines the range of days: a certain threshold applies starting from its `days` field until the next threshold `days` excluded.

If a threshold for a certain config has triggered for a structure, the following attributes will determine if the ping is to be sent and what's written in it:

- `repeat_days` specifies the frequency of the pings. If left empty, a ping is sent only when the structure first enters the threshold, a value of 1 means one ping per day as long as the structure's fuel left stays in the threshold's range, and so on.
- `message` is an optional custom message that is sent along with the embed. It supports `{days}`, `{structure}` and `{system}` for formatting.
- `color` is the color of the embed. Google "discord color picker" and paste the **decimal** value in this field.
- `ping_groups` are the list of groups that will be mentioned in the message. This field is only shown when the [discord service](https://allianceauth.readthedocs.io/en/latest/features/services/discord.html) is installed.
- `ping_here` and `ping_everyone` will add the corresponding pings to the message.

# Setup

add periodic task, default timing below.

`pinger.tasks.bootstrap_notification_tasks`

make a new cron `*/10 * * * * *`

# Optional Optimization

This is only required if you have issues with backlog on your main workers. Generally not an issue for smaller installations.

## Separate Worker Queue

Edit `myauth/myauth/celery.py`

```python
app.conf.task_routes = {.....
                        'pinger.tasks.corporation_notification_update': {'queue':'pingbot'},
                        .....
                        }
```

## Bare Metal

Add program block to `supervisor.conf`

```ini
[program:pingbot]
command=/path/to/venv/venv/bin/celery -A myauth worker --pool=threads --concurrency=5 -Q pingbot
directory=/home/allianceserver/myauth
user=allianceserver
numprocs=1
stdout_logfile=/home/allianceserver/myauth/log/pingbot.log
stderr_logfile=/home/allianceserver/myauth/log/pingbot.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=60
killasgroup=true
priority=998
```

## Docker

add a new worker container

```compose
  allianceauth_worker_pingbot:
    container_name: allianceauth_worker_pingbot
    <<: [*allianceauth-base, *allianceauth-health-checks]
    entrypoint: ["celery","-A","myauth","worker","--pool=threads","--concurrency=10","-Q","pingbot","-n","P_%n"]
```

## Settings

| Name                     | Description                                                   | Default    |
| ------------------------ | ------------------------------------------------------------- | ---------- |
| `CT_PINGER_VALID_STATES` | A List of Valid States to be queries for Pinger notifications | ["Member"] |
