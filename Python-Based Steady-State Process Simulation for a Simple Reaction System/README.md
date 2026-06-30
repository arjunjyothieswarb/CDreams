# Steady-State CSTR Reactor Simulator

A Python script that models the steady-state behavior of a non-isothermal
Continuous Stirred Tank Reactor (CSTR) running a simple, hypothetical
first-order exothermic reaction:

    A -> B

## What it does

- Solves the coupled steady-state **mass balance** and **energy balance**
  for the reactor using Arrhenius kinetics (`scipy.optimize.fsolve`).
- Scans multiple initial guesses to detect **multiple steady states**
  (ignition/extinction behavior), a classic phenomenon in non-isothermal
  CSTR design.
- Sweeps key operating parameters — feed temperature, residence time,
  and inlet concentration — and plots their effect on conversion and
  reactor temperature.
- With the default parameters, the feed-temperature sweep reproduces a
  textbook ignition curve: conversion jumps from ~10% to ~85%+ over a
  narrow temperature window (~314-318 K), with three coexisting steady
  states in between.

## Requirements

```bash
pip install numpy scipy matplotlib
```

## Usage

```bash
python reaction_simulator.py
```

This prints the base-case steady-state solution to the console, then
generates and displays three plots (also saved as PNG files):

- `conversion_vs_feed_temperature.png`
- `conversion_vs_residence_time.png`
- `conversion_vs_inlet_concentration.png`

## Customizing

Edit the `BASE_CASE` dictionary near the top of the script to model your
own kinetics, thermodynamics, feed conditions, or heat transfer setup.
The parameter sweep ranges can be adjusted inside `main()`.
