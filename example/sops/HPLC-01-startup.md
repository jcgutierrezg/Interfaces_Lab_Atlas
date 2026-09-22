---
title: LC-MS — daily start-up
equipment: [HPLC-01, MS-01, PUMP-02]
owner: Analytics group
version: 1
reviewed: 2026-09-21
---

# LC-MS — daily start-up

> **EXAMPLE.** Placeholder text that shows the format. It is not a validated procedure: replace it with your own.

**Where:** [[HPLC-01]] and [[MS-01]] on [[BENCH-11.A]] · **Controlled from:** [[PC-02]] · **Nitrogen:** [[N2G-01]]

## Purpose

Bring the LC-MS from standby to ready for a sequence.

## Safety

- PPE: lab coat, gloves, eye protection when handling solvents.
- Hazards: flammable solvents, high voltage inside the MS source, pressurised lines.
- Stop immediately if: a leak alarm sounds, you smell solvent near the source, or the vacuum reading rises.

## Before you start

- [ ] Nitrogen supply on and at pressure ([[N2G-01]]).
- [ ] MS vacuum reading normal on [[PC-02]].
- [ ] Enough mobile phase: fresh bottles are in [[CAB-02.S2]].
- [ ] Vials and caps ready ([[PED-02.D1]]); spare fittings in [[BOX-02]].

## Procedure

1. Top up the mobile phase and purge each pump channel.
2. Start the flow at the method's starting conditions and let the column equilibrate.
3. Switch the MS from standby to operate and let it stabilise.
4. Run a blank, then a check standard, before starting the sequence.

## Shutdown and clean-up

1. Flush the column, then return the MS to standby. Never switch the MS off: it must stay under vacuum.

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| Pressure too high | Blocked inlet filter or guard | Replace the guard cartridge (spares in [[CAB-02.S1]]) |
| Pressure fluctuates | Air in a pump channel | Purge that channel again |
| No MS signal | Nitrogen off or source dirty | Check [[N2G-01]], then report it |

## Reference photos

`photos/BENCH-11--reference.png`: the bench as it should be left.

## Revision history

| Version | Date | Who | Change |
|---|---|---|---|
| 1 | 2026-09-21 | Example | First version |
