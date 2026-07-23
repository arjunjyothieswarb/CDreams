#!/usr/bin/env python3
"""
pump_sizer.py
=============
A preliminary centrifugal pump sizing tool for process engineers.

Given fluid properties, flow rate, pipe geometry, and elevation change,
this script calculates:
  1. Total Dynamic Head (TDH) = static head + friction head + velocity head
  2. Brake Horsepower (BHP) required at a user-defined pump efficiency
  3. A preliminary pump type recommendation and typical efficiency range,
     based on flow rate / head region.

All calculations use consistent US customary units (ft, gpm, ft/s, psi,
lb/ft^3, cP) since that's the standard convention in most pump vendor
catalogs and engineering references (e.g. Crane Technical Paper 410,
Cameron Hydraulic Data, Karassik's "Pump Handbook").

Run interactively:
    python3 pump_sizer.py
"""

import math

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
G = 32.174          # gravitational acceleration, ft/s^2
GC = 32.174          # gravitational constant, lbm*ft/(lbf*s^2)  (numerically = G)
WATER_DENSITY_LB_FT3 = 62.4  # reference density of water at ~60F, lb/ft^3


def get_float(prompt, default=None):
    """Prompt the user for a float, allowing an optional default value."""
    while True:
        raw = input(f"{prompt}" + (f" [{default}]: " if default is not None else ": "))
        if raw.strip() == "" and default is not None:
            return float(default)
        try:
            return float(raw)
        except ValueError:
            print("  -> Please enter a numeric value.")


def gather_inputs():
    """Collect all user inputs needed for the sizing calculation."""
    print("=" * 60)
    print(" PUMP SIZING TOOL - Total Dynamic Head & BHP Calculator")
    print("=" * 60)

    print("\n--- Fluid Properties ---")
    sg = get_float("Specific gravity of fluid (water = 1.0)", default=1.0)
    viscosity_cp = get_float("Fluid viscosity (centipoise, cP)", default=1.0)

    print("\n--- Flow & Pipe Data ---")
    flow_gpm = get_float("Flow rate (gpm)")
    pipe_id_in = get_float("Pipe internal diameter (inches)")
    pipe_length_ft = get_float("Total pipe length, suction + discharge (ft)")
    roughness_ft = get_float(
        "Pipe absolute roughness (ft) [steel ~0.00015]", default=0.00015
    )

    print("\n--- Fittings / Minor Losses ---")
    # Equivalent length method: fittings are lumped into an equivalent
    # length of straight pipe (a common simplification in preliminary sizing).
    fittings_equiv_len_ft = get_float(
        "Equivalent length of fittings/valves (ft) [0 if unknown]", default=0.0
    )

    print("\n--- Elevation & Pressure ---")
    elevation_change_ft = get_float(
        "Elevation change, discharge minus suction (ft, use negative if downhill)"
    )
    delta_p_psi = get_float(
        "Additional discharge-to-suction pressure difference (psi) [0 if none, e.g. open tanks]",
        default=0.0,
    )

    print("\n--- Pump Efficiency ---")
    efficiency_pct = get_float("Assumed pump efficiency (%)", default=70.0)

    return {
        "sg": sg,
        "viscosity_cp": viscosity_cp,
        "flow_gpm": flow_gpm,
        "pipe_id_in": pipe_id_in,
        "pipe_length_ft": pipe_length_ft,
        "roughness_ft": roughness_ft,
        "fittings_equiv_len_ft": fittings_equiv_len_ft,
        "elevation_change_ft": elevation_change_ft,
        "delta_p_psi": delta_p_psi,
        "efficiency_pct": efficiency_pct,
    }


def calculate_velocity(flow_gpm, pipe_id_in):
    """
    Convert flow rate and pipe diameter into fluid velocity (ft/s).

    Q [ft^3/s] = flow_gpm / 448.831   (1 ft^3/s = 448.831 gpm)
    A [ft^2]   = pi/4 * D^2 (D in ft)
    v = Q / A
    """
    pipe_id_ft = pipe_id_in / 12.0
    area_ft2 = (math.pi / 4.0) * pipe_id_ft ** 2
    flow_ft3_s = flow_gpm / 448.831
    velocity_fps = flow_ft3_s / area_ft2
    return velocity_fps, area_ft2


def calculate_reynolds(velocity_fps, pipe_id_in, sg, viscosity_cp):
    """
    Reynolds number for pipe flow (dimensionless):
        Re = (density * velocity * diameter) / viscosity

    Using a units-consistent practical formula for liquids:
        Re = 3160 * (flow_gpm) * (SG) / (viscosity_cP * pipe_id_in)  [approx, common field formula]
    Here we instead compute it directly from velocity for transparency.
    """
    pipe_id_ft = pipe_id_in / 12.0
    density_lb_ft3 = sg * WATER_DENSITY_LB_FT3
    viscosity_lb_ft_s = viscosity_cp * 0.000672  # 1 cP = 0.000672 lb/(ft*s)
    re = (density_lb_ft3 * velocity_fps * pipe_id_ft) / viscosity_lb_ft_s
    return re


def friction_factor(re, roughness_ft, pipe_id_ft):
    """
    Darcy friction factor.
      - Laminar flow (Re < 2300): f = 64 / Re
      - Turbulent flow: Swamee-Jain explicit approximation to Colebrook equation,
        avoiding the need for iterative solving while staying accurate to ~1%.
    """
    if re < 2300:
        return 64.0 / re
    rel_roughness = roughness_ft / pipe_id_ft
    f = 0.25 / (
        math.log10(rel_roughness / 3.7 + 5.74 / (re ** 0.9)) ** 2
    )
    return f


def calculate_head(inputs):
    """
    Total Dynamic Head (TDH) is the sum of:
      1. Static head      -> elevation change the pump must overcome
      2. Friction head     -> losses from pipe wall friction + fittings (Darcy-Weisbach)
      3. Pressure head     -> any additional required discharge/suction pressure difference
      4. Velocity head     -> kinetic energy of the fluid (often small, included for completeness)

    Darcy-Weisbach equation:
        h_f = f * (L/D) * (v^2 / (2*g))
    """
    velocity_fps, area_ft2 = calculate_velocity(inputs["flow_gpm"], inputs["pipe_id_in"])
    pipe_id_ft = inputs["pipe_id_in"] / 12.0

    re = calculate_reynolds(
        velocity_fps, inputs["pipe_id_in"], inputs["sg"], inputs["viscosity_cp"]
    )
    f = friction_factor(re, inputs["roughness_ft"], pipe_id_ft)

    total_length_ft = inputs["pipe_length_ft"] + inputs["fittings_equiv_len_ft"]
    friction_head_ft = f * (total_length_ft / pipe_id_ft) * (velocity_fps ** 2) / (2 * G)

    static_head_ft = inputs["elevation_change_ft"]

    # Convert pressure difference (psi) to head (ft) for the given fluid SG:
    # h = (P * 144) / (density) = (P * 2.31) / SG   [ft of fluid, water-based constant 2.31]
    pressure_head_ft = (inputs["delta_p_psi"] * 2.31) / inputs["sg"]

    velocity_head_ft = (velocity_fps ** 2) / (2 * G)

    tdh_ft = static_head_ft + friction_head_ft + pressure_head_ft + velocity_head_ft

    return {
        "velocity_fps": velocity_fps,
        "reynolds": re,
        "friction_factor": f,
        "static_head_ft": static_head_ft,
        "friction_head_ft": friction_head_ft,
        "pressure_head_ft": pressure_head_ft,
        "velocity_head_ft": velocity_head_ft,
        "tdh_ft": tdh_ft,
    }


def calculate_bhp(flow_gpm, tdh_ft, sg, efficiency_pct):
    """
    Brake Horsepower (BHP) required by the pump driver:

        BHP = (Q[gpm] * TDH[ft] * SG) / (3960 * efficiency)

    The constant 3960 comes from converting gpm*ft into horsepower units:
        1 HP = 550 ft-lb/s ;  1 gpm of water = 8.33 lb/min
        3960 = (33000 ft-lb/min-HP) / (8.33 lb/gal)
    """
    efficiency = efficiency_pct / 100.0
    hydraulic_hp = (flow_gpm * tdh_ft * sg) / 3960.0
    bhp = hydraulic_hp / efficiency
    return hydraulic_hp, bhp


def recommend_pump(flow_gpm, tdh_ft):
    """
    Very preliminary pump type recommendation based on typical
    centrifugal pump application charts (approximate ranges only;
    always confirm against a real vendor pump curve/catalog).

    Rules of thumb used here:
      - Low flow, high head            -> Multistage centrifugal / Positive displacement
      - Low-moderate flow, low-mod head-> End-suction centrifugal (ANSI/API)
      - High flow, low-moderate head   -> Axial/mixed flow or double-suction centrifugal
      - High flow, high head           -> Multistage / between-bearings centrifugal
    """
    recommendations = []

    if flow_gpm < 100 and tdh_ft > 500:
        recommendations.append(
            "Low flow / very high head: consider a multistage centrifugal pump "
            "or a positive displacement (e.g., plunger/diaphragm) pump. "
            "Typical efficiency range: 40-65%."
        )
    elif flow_gpm < 500 and tdh_ft <= 500:
        recommendations.append(
            "Low-to-moderate flow, low-to-moderate head: an end-suction, "
            "single-stage centrifugal pump (ANSI or API 610 OH2) is typically suitable. "
            "Typical efficiency range: 50-75%."
        )
    elif flow_gpm >= 500 and tdh_ft <= 300:
        recommendations.append(
            "High flow, low-to-moderate head: consider a double-suction "
            "centrifugal pump or an axial/mixed-flow pump. "
            "Typical efficiency range: 75-88%."
        )
    else:
        recommendations.append(
            "High flow and high head: consider a multistage, between-bearings "
            "centrifugal pump (API 610 BB-type). "
            "Typical efficiency range: 65-80%."
        )

    return recommendations


def print_results(inputs, head_results, hydraulic_hp, bhp, recommendations):
    print("\n" + "=" * 60)
    print(" RESULTS")
    print("=" * 60)

    print("\n--- Hydraulics ---")
    print(f"Fluid velocity in pipe        : {head_results['velocity_fps']:.2f} ft/s")
    print(f"Reynolds number                : {head_results['reynolds']:,.0f} "
          f"({'laminar' if head_results['reynolds'] < 2300 else 'turbulent'})")
    print(f"Darcy friction factor          : {head_results['friction_factor']:.4f}")

    print("\n--- Head Breakdown (ft of fluid) ---")
    print(f"Static (elevation) head        : {head_results['static_head_ft']:.2f} ft")
    print(f"Friction head (pipe + fittings): {head_results['friction_head_ft']:.2f} ft")
    print(f"Pressure head (delta P)        : {head_results['pressure_head_ft']:.2f} ft")
    print(f"Velocity head                  : {head_results['velocity_head_ft']:.3f} ft")
    print(f"{'-'*40}")
    print(f"TOTAL DYNAMIC HEAD (TDH)       : {head_results['tdh_ft']:.2f} ft")

    print("\n--- Power ---")
    print(f"Hydraulic (water) horsepower    : {hydraulic_hp:.2f} HP")
    print(f"Assumed efficiency               : {inputs['efficiency_pct']:.1f}%")
    print(f"BRAKE HORSEPOWER (BHP) REQUIRED : {bhp:.2f} HP")

    print("\n--- Preliminary Pump Selection Guidance ---")
    for rec in recommendations:
        print(f"* {rec}")

    print("\nNote: This is a preliminary screening tool only. Always verify final "
          "selection against manufacturer pump curves (NPSH available vs. required, "
          "efficiency at actual operating point, materials compatibility, etc.).")
    print("=" * 60)


def main():
    inputs = gather_inputs()
    head_results = calculate_head(inputs)
    hydraulic_hp, bhp = calculate_bhp(
        inputs["flow_gpm"], head_results["tdh_ft"], inputs["sg"], inputs["efficiency_pct"]
    )
    recommendations = recommend_pump(inputs["flow_gpm"], head_results["tdh_ft"])
    print_results(inputs, head_results, hydraulic_hp, bhp, recommendations)


if __name__ == "__main__":
    main()