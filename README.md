# ⚡ EV Spatial Routing & Systems Simulator

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32.0-red.svg)](https://streamlit.io/)
[![Deployment](https://img.shields.io/badge/Live_App-Click_Here-success.svg)](#) *(<- Add your Streamlit Cloud link here later)*

A production-grade Python application utilizing topographical numerical integration, stochastic Monte Carlo simulations, and real-time APIs to model Electric Vehicle (EV) kinetic resistance, thermodynamics, and battery degradation over spatial routes. 

Designed as a superior alternative to static route planners, this tool transforms theoretical physics into actionable, probabilistic trip data for everyday EV drivers and fleet operators.

---

## 🏗️ System Architecture & API Integrations

The application operates on a state-space integration loop, calculating energy draw across discrete spatial segments (~100 nodes per route). It integrates three live external APIs:
1. **OSRM (Open Source Routing Machine):** Generates the multi-waypoint geographic polyline (GPS coordinates and distances).
2. **Open-Meteo API:** Injects real-time local weather data (temperature, wind vectors) and spatial topography maps for elevation changes.
3. **NREL (National Renewable Energy Lab) API:** Pings the U.S. Department of Energy database to proactively route the vehicle to the nearest verified DC Fast Charger when the battery drops below 12%.

---

## 📐 The Physics Engine (Numerical Integration)

For every segment between two GPS nodes, the software calculates the exact mechanical power ($P_{mech}$) required to move the vehicle.

### 1. Aerodynamic Drag ($P_{aero}$)
Calculates the power required to push the vehicle through the air. Incorporates live headwind vectors and variable air density ($\rho$) based on current temperature. Towing profiles dynamically increase the drag coefficient ($C_d$) and frontal area ($A$).
$$P_{aero} = \frac{1}{2} \rho \cdot (C_d + \Delta C_d) \cdot (A + \Delta A) \cdot v_{air}^2 \cdot v_{ground}$$

### 2. Rolling Resistance ($P_{roll}$)
Calculates the friction between the tires and the road. Total mass dynamically scales based on user payload inputs (passengers, cargo, or trailers).
$$P_{roll} = C_{rr} \cdot (m_{curb} + m_{payload}) \cdot g \cdot v_{ground} \cdot \cos(\theta)$$

### 3. Gravitational Grade Resistance ($P_{grade}$)
Calculates the energy required to climb an elevation change ($\theta$), or the potential energy recovered when driving downhill. 
$$P_{grade} = (m_{curb} + m_{payload}) \cdot g \cdot v_{ground} \cdot \sin(\theta)$$

### 4. Regenerative Braking (BMS Tapering)
When descending a mountain ($P_{grade} < 0$), kinetic energy is recaptured. The engine applies an advanced Battery Management System (BMS) constraint: regenerative efficiency ($\eta_{regen}$) smoothly tapers to 0% as the battery approaches 100% State of Charge (SOC) to prevent cell overvoltage.

---

## 🧬 Advanced Engineering Modules

### 🎲 Monte Carlo Confidence Engine (Uncertainty Quantification)
Static route planners fail when wind gusts or temperature drops occur. This application runs **100 parallel stochastic passes** using Gaussian distributions for driver speed variance, temperature fluctuations, and wind gusts. It outputs a 95% Confidence Interval for arrival battery and calculates a strict stranding probability.

### 📈 Cruising Speed Optimizer
Driving 80 mph instead of 68 mph exponentially increases energy draw due to $v^3$ aerodynamic drag, forcing extra charging stops. The software sweeps speeds from 55 to 85 mph, modeling both drive time and 150kW fast-charging lag, plotting the exact mathematical sweet spot for the shortest overall journey.

### 💵 Electrochemical Cell Aging & TCO Model
Fast charging degrades lithium-ion cells. The app models the hidden Total Cost of Ownership (TCO) by calculating cell wear cost ($0.035 per kWh throughput equivalent) alongside regional electricity rates, benchmarking it against a 17 MPG ICE vehicle (e.g., Ford Bronco) for operational context.

---

## 🛠️ Local Installation & Execution

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR-USERNAME/ev-route-planner.git](https://github.com/YOUR-USERNAME/ev-route-planner.git)
   cd ev-route-planner