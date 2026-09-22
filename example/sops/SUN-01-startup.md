---
title: Solar simulator and probe station — daily start-up
equipment: [SUN-01, PRB-01, VAC-02]
owner: Characterisation group
version: 1
reviewed: 2026-09-21
---

# Solar simulator and probe station — daily start-up

> **EXAMPLE.** Placeholder text that shows the format. It is not a validated procedure: replace it with your own.

**Where:** [[SUN-01]] and [[PRB-01]] on [[BENCH-11.A]] · **Controlled from:** [[PC-02]] · **Reference cell:** [[CAB-02.S2]]

## Purpose

Bring the solar simulator to a calibrated 1 sun (AM1.5G, 100 mW/cm²) and the probe station to ready for J-V
measurements.

## Safety

- PPE: lab coat, UV-blocking safety glasses; never look into the beam.
- Hazards: intense light and UV, ozone from the xenon lamp, a hot lamp housing, high voltage in the lamp igniter.
- Stop immediately if: the extraction isn't running, the lamp flickers or the shutter sticks open.

## Before you start

- [ ] Extraction running over the lamp housing (it makes ozone).
- [ ] Probe station chuck clean; vacuum pump [[VAC-02]] on.
- [ ] Spare adapters and leads in [[BOX-02]] if a connection is loose.

## Procedure

1. Switch the lamp on with the shutter closed; let it stabilise for 20 minutes.
2. Put the calibrated reference cell ([[CAB-02.S2]]) at the sample plane and adjust the intensity to 1 sun.
3. Record the reference cell's current in the log on [[PC-02]].
4. Load the device on the chuck, land the probes, then open the shutter and measure.

## Shutdown and clean-up

1. Close the shutter, then switch the lamp off; leave the fan running until the housing is cool.
2. Lift the probes, release the vacuum and switch off [[VAC-02]].

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| Can't reach 1 sun | Lamp ageing | Log the hours; the spare lamp is in [[CAB-02.S1]] |
| Noisy dark current | Stray light or a loose lead | Close the curtain; check the triax adapters |
| Probes won't land cleanly | Worn tips | Replace them (spares in [[CAB-02.S1]]) |

## Reference photos

`photos/BENCH-11--reference.png`: the bench as it should be left.

## Revision history

| Version | Date | Who | Change |
|---|---|---|---|
| 1 | 2026-09-21 | Example | First version |
