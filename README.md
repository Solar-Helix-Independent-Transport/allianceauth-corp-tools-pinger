# High Performance Pings

Leverage the corptools data to notify via discord certain events at a corp/alliance level

filter on/off regions/const/system/corps/alliances/types/strucutre type/notification type via admin. end specific notifications to different places via webhooks

configurable @ settings

## Structures

- attack/reinforce
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

- attack/reinforce
  - TowerAlertMsg

## Sov

- attacks
  - SovStructureReinforced
  - EntosisCaptureStarted
- pos anchoring (AllAnchoringMsg)

## Moons

- Extraction Started (MoonminingExtractionStarted)
- Extraction Complete (MoonminingExtractionFinished)
- Laser Fired (MoonminingLaserFired)
- auto fracture (MoonminingAutomaticFracture)

## HR

- New application (CorpAppNewMsg)
