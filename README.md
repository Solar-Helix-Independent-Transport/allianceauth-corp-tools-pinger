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
