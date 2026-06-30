#!/usr/bin/env python3
"""
reaction_simulator.py

Steady-state, non-isothermal CSTR simulator for the reaction A -> B
(first-order, exothermic). Solves the coupled mass and energy balances
and sweeps key operating parameters to show their effect on conversion.

See README.md for the full theory, equations, units, and usage
instructions.
"""

import numpy as np
from scipy.optimize import fsolve
import matplotlib.pyplot as plt

R_GAS = 8.314  # kJ/(kmol*K), universal gas constant

# Base-case parameters for the hypothetical reaction A -> B.
# Edit these to model your own reaction system (see README.md).
BASE_CASE = {
    # --- Kinetics (Arrhenius) ---
    "k0": 2.0e7,         # 1/s, pre-exponential (frequency) factor
    "Ea": 6.0e4,         # kJ/kmol, activation energy

    # --- Thermodynamics ---
    "dH_rxn": -8.5e4,    # kJ/kmol, heat of reaction (negative = exothermic)

    # --- Feed conditions ---
    "C_A0": 4.0,         # kmol/m^3, inlet concentration of A
    "T0": 320.0,         # K, feed temperature
    "Q0": 0.05,          # m^3/s, volumetric feed flow rate

    # --- Reactor / operating parameters ---
    "tau": 30.0,         # s, residence time (V / Q0)

    # --- Physical properties of reacting mixture (assumed ~constant) ---
    "rho": 1000.0,       # kg/m^3, mixture density
    "Cp": 4.0,           # kJ/(kg*K), mixture heat capacity

    # --- Heat transfer (jacket / coolant) ---
    "U": 0.4,            # kJ/(s*m^2*K), overall heat transfer coefficient
    "A_ht": 5.0,         # m^2, heat transfer area
    "Tc": 300.0,         # K, coolant/jacket temperature
}
# Note: with these defaults, the feed-temperature sweep crosses an
# "ignition" region (~314-318 K) with three coexisting steady states.
# See README.md for why.


# ----------------------------------------------------------------------
# CORE MODEL FUNCTIONS
# ----------------------------------------------------------------------
def rate_constant(T, k0, Ea):
    """
    Arrhenius rate constant k(T) = k0 * exp(-Ea / (R*T)).

    Guards against numerical overflow/invalid values when the nonlinear
    solver (fsolve) explores extreme or non-physical temperature guesses
    on its way to a solution (e.g. T <= 0 or very large T).
    """
    T_safe = np.asarray(T, dtype=float)
    if T_safe.ndim == 0:
        if T_safe <= 0 or not np.isfinite(T_safe):
            return 0.0
    exponent = np.clip(-Ea / (R_GAS * np.where(T_safe > 1e-6, T_safe, 1e-6)),
                        -700, 700)
    return k0 * np.exp(exponent)


def mass_balance_X(T, tau, k0, Ea):
    """
    Steady-state CSTR mass balance, solved explicitly for conversion X
    given temperature T and residence time tau (first-order kinetics):

        X = k(T)*tau / (1 + k(T)*tau)
    """
    k = rate_constant(T, k0, Ea)
    return (k * tau) / (1.0 + k * tau)


def energy_balance_X(T, params):
    """
    Steady-state CSTR energy balance, solved explicitly for conversion X
    given temperature T (rearranged form of the heat balance):

        X = [rho*Cp*(T - T0) + (U*A_ht/Q0)*(T - Tc)] / (C_A0 * (-dH_rxn))
    """
    rho, Cp = params["rho"], params["Cp"]
    T0, Tc = params["T0"], params["Tc"]
    U, A_ht, Q0 = params["U"], params["A_ht"], params["Q0"]
    C_A0, dH_rxn = params["C_A0"], params["dH_rxn"]

    sensible_heat = rho * Cp * (T - T0)
    jacket_heat = (U * A_ht / Q0) * (T - Tc)
    return (sensible_heat + jacket_heat) / (C_A0 * (-dH_rxn))


def steady_state_residual(vars_, params):
    """
    Residual vector for simultaneous solution of mass balance and
    energy balance. vars_ = [T, X]. Returns [0, 0] at a steady state.
    """
    T, X = vars_
    X_mass = mass_balance_X(T, params["tau"], params["k0"], params["Ea"])
    X_energy = energy_balance_X(T, params)
    return [X - X_mass, X - X_energy]


def find_steady_states(params, T_guesses=None):
    """
    Solve for steady-state (T, X) pairs by trying multiple initial
    temperature guesses (to catch multiple steady states, if present),
    then de-duplicating solutions that converge to (numerically) the
    same point.

    Returns a sorted list of (T, X) tuples.
    """
    if T_guesses is None:
        # Scan a wide range of initial temperature guesses
        T_guesses = np.linspace(params["T0"] - 20, params["T0"] + 150, 25)

    solutions = []
    for T_guess in T_guesses:
        X_guess = 0.5
        try:
            sol, info, ier, msg = fsolve(
                steady_state_residual,
                x0=[T_guess, X_guess],
                args=(params,),
                full_output=True,
                xtol=1e-10,
            )
            T_sol, X_sol = sol
            # Keep only physically valid solutions (0 <= X <= 1, T > 0)
            if ier == 1 and -1e-6 <= X_sol <= 1.0 + 1e-6 and T_sol > 0:
                X_sol = min(max(X_sol, 0.0), 1.0)
                solutions.append((round(T_sol, 4), round(X_sol, 6)))
        except Exception:
            continue

    # De-duplicate near-identical solutions
    unique = []
    for T_sol, X_sol in solutions:
        if not any(abs(T_sol - Tu) < 0.05 for Tu, _ in unique):
            unique.append((T_sol, X_sol))

    return sorted(unique, key=lambda pair: pair[0])


# ----------------------------------------------------------------------
# PARAMETER SWEEPS
# ----------------------------------------------------------------------
def sweep_feed_temperature(base_params, T0_range):
    """Vary feed temperature T0; return arrays of T0, T_steady, X_steady.

    For each T0, all steady states found are recorded (a T0 value may
    appear more than once if multiple steady states exist there).
    """
    T0_list, T_list, X_list = [], [], []
    for T0 in T0_range:
        params = dict(base_params)
        params["T0"] = T0
        for T_sol, X_sol in find_steady_states(params):
            T0_list.append(T0)
            T_list.append(T_sol)
            X_list.append(X_sol)
    return np.array(T0_list), np.array(T_list), np.array(X_list)


def sweep_residence_time(base_params, tau_range):
    """Vary residence time tau; return arrays of tau, T_steady, X_steady."""
    tau_list, T_list, X_list = [], [], []
    for tau in tau_range:
        params = dict(base_params)
        params["tau"] = tau
        for T_sol, X_sol in find_steady_states(params):
            tau_list.append(tau)
            T_list.append(T_sol)
            X_list.append(X_sol)
    return np.array(tau_list), np.array(T_list), np.array(X_list)


def sweep_inlet_concentration(base_params, CA0_range):
    """Vary inlet concentration C_A0; return arrays of C_A0, T_steady, X_steady.

    Note: changing C_A0 changes the energy-balance line (via the
    C_A0*(-dH_rxn) denominator), so conversion AND temperature both
    respond to this parameter for an exothermic reaction.
    """
    CA0_list, T_list, X_list = [], [], []
    for CA0 in CA0_range:
        params = dict(base_params)
        params["C_A0"] = CA0
        for T_sol, X_sol in find_steady_states(params):
            CA0_list.append(CA0)
            T_list.append(T_sol)
            X_list.append(X_sol)
    return np.array(CA0_list), np.array(T_list), np.array(X_list)


# ----------------------------------------------------------------------
# PLOTTING
# ----------------------------------------------------------------------
def plot_vs_feed_temperature(T0_arr, T_arr, X_arr, save_path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax1.scatter(T0_arr, X_arr, s=12, color="tab:blue")
    ax1.set_xlabel("Feed Temperature, T0 (K)")
    ax1.set_ylabel("Steady-State Conversion, X")
    ax1.set_title("Conversion vs. Feed Temperature")
    ax1.grid(True, alpha=0.3)

    ax2.scatter(T0_arr, T_arr, s=12, color="tab:red")
    ax2.set_xlabel("Feed Temperature, T0 (K)")
    ax2.set_ylabel("Steady-State Reactor Temperature, T (K)")
    ax2.set_title("Reactor Temperature vs. Feed Temperature")
    ax2.grid(True, alpha=0.3)

    fig.suptitle("CSTR Steady-State Behavior: Effect of Feed Temperature\n"
                  "(multiple points at one T0 indicate multiple steady states)")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"Saved plot: {save_path}")


def plot_vs_residence_time(tau_arr, T_arr, X_arr, save_path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax1.plot(tau_arr, X_arr, "o-", markersize=3, color="tab:green")
    ax1.set_xlabel("Residence Time, tau (s)")
    ax1.set_ylabel("Steady-State Conversion, X")
    ax1.set_title("Conversion vs. Residence Time")
    ax1.grid(True, alpha=0.3)

    ax2.plot(tau_arr, T_arr, "o-", markersize=3, color="tab:orange")
    ax2.set_xlabel("Residence Time, tau (s)")
    ax2.set_ylabel("Steady-State Reactor Temperature, T (K)")
    ax2.set_title("Reactor Temperature vs. Residence Time")
    ax2.grid(True, alpha=0.3)

    fig.suptitle("CSTR Steady-State Behavior: Effect of Residence Time")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"Saved plot: {save_path}")


def plot_vs_inlet_concentration(CA0_arr, T_arr, X_arr, save_path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax1.plot(CA0_arr, X_arr, "o-", markersize=3, color="tab:purple")
    ax1.set_xlabel("Inlet Concentration, C_A0 (kmol/m^3)")
    ax1.set_ylabel("Steady-State Conversion, X")
    ax1.set_title("Conversion vs. Inlet Concentration")
    ax1.grid(True, alpha=0.3)

    ax2.plot(CA0_arr, T_arr, "o-", markersize=3, color="tab:brown")
    ax2.set_xlabel("Inlet Concentration, C_A0 (kmol/m^3)")
    ax2.set_ylabel("Steady-State Reactor Temperature, T (K)")
    ax2.set_title("Reactor Temperature vs. Inlet Concentration")
    ax2.grid(True, alpha=0.3)

    fig.suptitle("CSTR Steady-State Behavior: Effect of Inlet Concentration")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"Saved plot: {save_path}")


# ----------------------------------------------------------------------
# MAIN DRIVER
# ----------------------------------------------------------------------
def main():
    print("=" * 70)
    print("Steady-State CSTR Simulator: A -> B (first-order, exothermic)")
    print("=" * 70)

    # 1) Solve the base case and report the operating point(s)
    base_solutions = find_steady_states(BASE_CASE)
    print(f"\nBase case parameters: {BASE_CASE}\n")
    print("Steady-state solution(s) found for the base case:")
    for T_sol, X_sol in base_solutions:
        k_sol = rate_constant(T_sol, BASE_CASE["k0"], BASE_CASE["Ea"])
        print(f"   T = {T_sol:8.2f} K   X = {X_sol:6.4f}   "
              f"k(T) = {k_sol:.4e} 1/s")
    if not base_solutions:
        print("   No steady state found -- try adjusting BASE_CASE parameters "
              "or the initial guess range in find_steady_states().")

    # 2) Sweep #1: Conversion & Temperature vs. Feed Temperature (T0)
    T0_range = np.linspace(280, 360, 60)
    T0_arr, T_arr, X_arr = sweep_feed_temperature(BASE_CASE, T0_range)
    plot_vs_feed_temperature(T0_arr, T_arr, X_arr,
                              "conversion_vs_feed_temperature.png")

    # 3) Sweep #2: Conversion & Temperature vs. Residence Time (tau)
    tau_range = np.linspace(10, 400, 60)
    tau_arr, T_arr2, X_arr2 = sweep_residence_time(BASE_CASE, tau_range)
    plot_vs_residence_time(tau_arr, T_arr2, X_arr2,
                            "conversion_vs_residence_time.png")

    # 4) Sweep #3: Conversion & Temperature vs. Inlet Concentration (C_A0)
    CA0_range = np.linspace(1.0, 8.0, 60)
    CA0_arr, T_arr3, X_arr3 = sweep_inlet_concentration(BASE_CASE, CA0_range)
    plot_vs_inlet_concentration(CA0_arr, T_arr3, X_arr3,
                                 "conversion_vs_inlet_concentration.png")

    print("\nAll sweeps complete. Displaying plots (close windows to exit)...")
    plt.show()


if __name__ == "__main__":
    main()
