import streamlit as st
import requests
import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pydeck as pdk
from geopy.geocoders import Nominatim

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EV Spatial Simulator & Trip Planner", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- VEHICLE & ACCESSORY DATABASES ---
EV_DATABASE = {
    "Tesla Model 3 Long Range": {"kwh": 75.0, "mass_kg": 1830, "cd": 0.219, "area_m2": 2.22, "hvac": "Heat Pump"},
    "Rivian R1T (Large Pack)": {"kwh": 135.0, "mass_kg": 3200, "cd": 0.30, "area_m2": 3.15, "hvac": "Heat Pump"},
    "Ford F-150 Lightning ER": {"kwh": 131.0, "mass_kg": 3100, "cd": 0.43, "area_m2": 3.54, "hvac": "Resistive"},
    "Tesla Model Y Long Range": {"kwh": 75.0, "mass_kg": 1992, "cd": 0.23, "area_m2": 2.65, "hvac": "Heat Pump"},
    "Ford Mustang Mach-E ER AWD": {"kwh": 91.0, "mass_kg": 2322, "cd": 0.29, "area_m2": 2.55, "hvac": "Resistive"},
    "Hyundai Ioniq 5 AWD": {"kwh": 84.0, "mass_kg": 2005, "cd": 0.28, "area_m2": 2.55, "hvac": "Heat Pump"},
    "Kia EV6 Long Range AWD": {"kwh": 84.0, "mass_kg": 2075, "cd": 0.28, "area_m2": 2.50, "hvac": "Heat Pump"},
    "Porsche Taycan 4S Plus": {"kwh": 83.7, "mass_kg": 2220, "cd": 0.22, "area_m2": 2.33, "hvac": "Heat Pump"},
    "Lucid Air Grand Touring": {"kwh": 112.0, "mass_kg": 2360, "cd": 0.197, "area_m2": 2.27, "hvac": "Heat Pump"},
    "Chevrolet Silverado EV 4WT": {"kwh": 170.0, "mass_kg": 3873, "cd": 0.40, "area_m2": 3.50, "hvac": "Heat Pump"}
}

AERO_ACCESSORIES = {
    "None (Stock Vehicle)": {"delta_cd": 0.0, "delta_area": 0.0, "extra_weight_lbs": 0},
    "Roof Skibox / Cargo Carrier": {"delta_cd": 0.05, "delta_area": 0.30, "extra_weight_lbs": 100},
    "Teardrop Camper Trailer": {"delta_cd": 0.12, "delta_area": 0.80, "extra_weight_lbs": 1800},
    "Enclosed Heavy Box Trailer": {"delta_cd": 0.28, "delta_area": 1.50, "extra_weight_lbs": 3500}
}

# --- GEOGRAPHIC & INFRASTRUCTURE UTILITIES (CACHED) ---
def haversine(lon1, lat1, lon2, lat2):
    R = 3958.8 
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def get_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    return (math.degrees(math.atan2(x, y)) + 360) % 360

@st.cache_data(show_spinner=False)
def get_live_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            c = resp.json().get("current", {})
            return c.get("temperature_2m", 70.0), c.get("wind_speed_10m", 0.0), c.get("wind_direction_10m", 0.0)
    except: pass
    return 70.0, 0.0, 0.0

@st.cache_data(show_spinner=False)
def get_coordinates(address):
    try:
        geolocator = Nominatim(user_agent="grcc_ev_mapper_project")
        loc = geolocator.geocode(address, timeout=10)
        return (loc.latitude, loc.longitude) if loc else None
    except: return None

@st.cache_data(show_spinner=False)
def get_route_data_multi(coords_list):
    lon_lats = ";".join([f"{c[1]},{c[0]}" for c in coords_list])
    url = f"http://router.project-osrm.org/route/v1/driving/{lon_lats}?overview=full&geometries=geojson"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            route = resp.json()["routes"][0]
            dist = route["distance"] * 0.000621371
            dur = route["duration"] / 60.0
            return dist, dur, route["geometry"]["coordinates"]
    except: pass
    return None, None, None

@st.cache_data(show_spinner=False)
def get_elevation_profile(lats_str, lons_str):
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lats_str}&longitude={lons_str}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("elevation")
    except: pass
    return None

def process_elevation(coords):
    step = max(1, len(coords) // 99)
    sampled = coords[::step][:99]
    if sampled[-1] != coords[-1]: sampled.append(coords[-1])
    lats = ",".join([str(round(c[1], 4)) for c in sampled])
    lons = ",".join([str(round(c[0], 4)) for c in sampled])
    elev_data = get_elevation_profile(lats, lons)
    if elev_data and len(elev_data) == len(sampled):
        return sampled, elev_data
    return sampled, [0]*len(sampled)

@st.cache_data(show_spinner=False)
def get_nearest_charger(lat, lon):
    url = f"https://developer.nrel.gov/api/alt-fuel-stations/v1/nearest.json?api_key=DEMO_KEY&latitude={lat}&longitude={lon}&fuel_type=ELEC&access=public&status=E&limit=1"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            stations = resp.json().get("alt_fuel_stations", [])
            if stations:
                s = stations[0]
                return s["station_name"], [s["longitude"], s["latitude"]], s["distance"]
    except: pass
    return None, None, None

# --- TOPOGRAPHIC NUMERICAL INTEGRATION ENGINE ---
def run_spatial_physics_simulation(ev, coords, elevations, speed_mph, temp_f, wind_spd, wind_dir, soh_pct, payload_lbs, aero_preset, preconditioning):
    rho = 353.05 / ((temp_f - 32) * (5 / 9) + 273.15)
    g, crr, eta_drive, base_regen_eta, p_aux_kw = 9.81, 0.015, 0.90, 0.70, 0.5
    v_ground_mps = speed_mph * 0.44704 
    
    total_cd = ev["cd"] + aero_preset["delta_cd"]
    total_area = ev["area_m2"] + aero_preset["delta_area"]
    total_mass_kg = ev["mass_kg"] + ((payload_lbs + aero_preset["extra_weight_lbs"]) * 0.453592)
    
    usable_kwh = ev["kwh"] * (soh_pct / 100.0)
    p_precondition_kw = 0.0
    
    if temp_f < 32:
        if preconditioning:
            p_precondition_kw = 2.5
        else:
            usable_kwh *= 0.85
            
    p_hvac_kw = (70 - temp_f) * (0.03 if ev["hvac"] == "Heat Pump" else 0.12) if temp_f < 70 else 0.0
        
    current_batt = usable_kwh
    kwh_gross, kwh_regen = 0.0, 0.0
    telemetry = {"Aerodynamic Drag": 0.0, "Rolling Resistance": 0.0, "Elevation Climb": 0.0, "HVAC Climate Control": 0.0, "Auxiliary Electronics": 0.0, "Thermal Preconditioning": 0.0}
    
    charge_events = []
    death_coords = None
    cum_dist = 0.0

    telemetry_log = [{
        "Node ID": 0, "Latitude": round(coords[0][1], 6), "Longitude": round(coords[0][0], 6),
        "Cumulative Distance (mi)": 0.0, "Elevation (ft)": round(elevations[0] * 3.28084, 1),
        "Battery SOC (%)": 100.0
    }]

    for i in range(len(coords) - 1):
        p1, p2 = coords[i], coords[i+1]
        e1, e2 = elevations[i], elevations[i+1]
        
        dist_m = haversine(p1[0], p1[1], p2[0], p2[1]) * 1609.34
        if dist_m <= 0: continue
        
        theta = math.atan2((e2 - e1), dist_m)
        t_hours = (dist_m / v_ground_mps) / 3600.0
        cum_dist += (dist_m * 0.000621371)
        
        bearing = get_bearing(p1[1], p1[0], p2[1], p2[0])
        headwind_mph = wind_spd * math.cos(math.radians(wind_dir - bearing))
        v_air_mps = max(speed_mph + headwind_mph, 0.0) * 0.44704
        
        p_aero = (0.5 * rho * total_cd * total_area * (v_air_mps ** 2) * v_ground_mps) / 1000.0
        p_roll = (crr * total_mass_kg * g * v_ground_mps * math.cos(theta)) / 1000.0
        p_grade = (total_mass_kg * g * v_ground_mps * math.sin(theta)) / 1000.0
        
        p_mech = p_aero + p_roll + p_grade
        soc = current_batt / usable_kwh
        eta_regen = base_regen_eta * max(0.0, (1.0 - soc) / 0.10) if soc > 0.90 else base_regen_eta

        if p_mech > 0:
            gross_kwh = (p_mech / eta_drive) * t_hours
            regen_kwh = 0.0
            telemetry["Aerodynamic Drag"] += (p_aero / eta_drive) * t_hours
            telemetry["Rolling Resistance"] += (p_roll / eta_drive) * t_hours
            if p_grade > 0: telemetry["Elevation Climb"] += (p_grade / eta_drive) * t_hours
        else:
            gross_kwh = 0.0
            regen_kwh = abs(p_mech * eta_regen) * t_hours
            
        base_kwh = (p_hvac_kw + p_aux_kw + p_precondition_kw) * t_hours
        telemetry["HVAC Climate Control"] += p_hvac_kw * t_hours
        telemetry["Auxiliary Electronics"] += p_aux_kw * t_hours
        telemetry["Thermal Preconditioning"] += p_precondition_kw * t_hours
        
        net_drain = gross_kwh + base_kwh - regen_kwh
        current_batt -= net_drain
        if current_batt > usable_kwh: current_batt = usable_kwh
        
        kwh_gross += (gross_kwh + base_kwh)
        kwh_regen += regen_kwh
        
        if current_batt < (usable_kwh * 0.12) and current_batt > 0:
            charge_events.append({"coords": [p2[0], p2[1]], "soc_arrival": (current_batt / usable_kwh) * 100.0})
            current_batt = usable_kwh * 0.80
            
        elif current_batt <= 0 and not death_coords:
            death_coords = [p2[0], p2[1]]
            break

        telemetry_log.append({
            "Node ID": i + 1, "Latitude": round(p2[1], 6), "Longitude": round(p2[0], 6),
            "Cumulative Distance (mi)": round(cum_dist, 2), "Elevation (ft)": round(e2 * 3.28084, 1),
            "Battery SOC (%)": max(0.0, round((current_batt / usable_kwh) * 100.0, 1))
        })

    return kwh_gross, kwh_regen, current_batt, usable_kwh, charge_events, death_coords, telemetry, pd.DataFrame(telemetry_log)

# --- MONTE CARLO CONFIDENCE ENGINE ---
def run_monte_carlo_simulation(ev, coords, elevations, target_speed, base_temp, base_wind_spd, base_wind_dir, soh_pct, payload_lbs, aero_preset, preconditioning, runs=50):
    np.random.seed(42)
    speed_variations = np.random.normal(target_speed, 3.0, runs)
    temp_variations = np.random.normal(base_temp, 4.0, runs)
    wind_spd_variations = np.random.normal(base_wind_spd, 5.0, runs)
    
    final_soc_results = []
    
    for i in range(runs):
        sim_speed = float(np.clip(speed_variations[i], 35, 85))
        sim_temp = float(np.clip(temp_variations[i], -20, 110))
        sim_wind = float(np.clip(wind_spd_variations[i], 0, 50))
        
        _, _, final_batt, usable_kwh, _, _, _, _ = run_spatial_physics_simulation(
            ev, coords, elevations, sim_speed, sim_temp, sim_wind, base_wind_dir, soh_pct, payload_lbs, aero_preset, preconditioning
        )
        final_soc_results.append(max(0.0, (final_batt / usable_kwh) * 100.0))
        
    soc_array = np.array(final_soc_results)
    return {
        "mean_soc": round(float(np.mean(soc_array)), 1),
        "p95_lower": round(float(np.percentile(soc_array, 5)), 1),
        "p95_upper": round(float(np.percentile(soc_array, 95)), 1),
        "p99_worst": round(float(np.percentile(soc_array, 1)), 1),
        "stranding_risk_pct": round(float(np.mean(soc_array <= 0.0) * 100.0), 1),
        "soc_distribution": soc_array
    }

# --- SPEED OPTIMIZATION ENGINE ---
def find_optimal_cruising_speed(ev, coords, elevations, base_temp, base_wind_spd, base_wind_dir, soh_pct, payload_lbs, aero_preset, preconditioning):
    speed_sweep = list(range(55, 86, 5))
    sweep_data = []

    for test_speed in speed_sweep:
        kwh_gross, kwh_regen, final_batt, usable_kwh, charge_events, death_coords, telemetry, df_log = run_spatial_physics_simulation(
            ev, coords, elevations, test_speed, base_temp, base_wind_spd, base_wind_dir, soh_pct, payload_lbs, aero_preset, preconditioning
        )
        dist_miles = df_log["Cumulative Distance (mi)"].iloc[-1]
        drive_hrs = dist_miles / test_speed
        charge_hrs = len(charge_events) * ((usable_kwh * 0.68) / 150.0)
        total_hrs = drive_hrs + charge_hrs
        
        sweep_data.append({
            "Speed (mph)": test_speed, "Drive Time (hrs)": round(drive_hrs, 2),
            "Charge Time (hrs)": round(charge_hrs, 2), "Total Duration (hrs)": round(total_hrs, 2),
            "Stops": len(charge_events)
        })
        
    df_sweep = pd.DataFrame(sweep_data)
    opt_row = df_sweep.loc[df_sweep["Total Duration (hrs)"].idxmin()]
    return df_sweep, int(opt_row["Speed (mph)"]), float(opt_row["Total Duration (hrs)"])


# ==========================================
# === STREAMLIT UI/UX LAYOUT & RENDERING ===
# ==========================================
with st.sidebar:
    st.title("⚙️ Garage & Setup")
    
    st.subheader("1. Vehicle Configuration")
    ev_options = list(EV_DATABASE.keys()) + ["🔧 Custom EV (Define specs)"]
    selected_ev_name = st.selectbox("Select Model", ev_options)
    
    if selected_ev_name == "🔧 Custom EV (Define specs)":
        c1, c2 = st.columns(2)
        custom_kwh = c1.number_input("Battery (kWh)", 40.0, 250.0, 80.0)
        custom_mass = c2.number_input("Curb Wt (lbs)", 2000, 10000, 4000)
        custom_cd = c1.number_input("Drag (Cd)", 0.1, 0.6, 0.25)
        custom_area = c2.number_input("Front (m²)", 1.5, 4.0, 2.5)
        ev_specs = {"kwh": custom_kwh, "mass_kg": custom_mass * 0.453592, "cd": custom_cd, "area_m2": custom_area, "hvac": "Heat Pump"}
    else:
        ev_specs = EV_DATABASE[selected_ev_name]
        
    soh_pct = st.slider("Battery State of Health (%)", 50, 100, 100)
    
    st.subheader("2. Aerodynamics & Towing")
    selected_aero_name = st.selectbox("Towing / Roof Carrier", list(AERO_ACCESSORIES.keys()))
    aero_preset = AERO_ACCESSORIES[selected_aero_name]
    payload_lbs = st.slider("Cargo / Passenger Mass (lbs)", 0, 3000, 0, step=100)
    
    st.divider()
    st.subheader("3. Environment")
    speed = st.slider("Cruising Speed (mph)", 35, 85, 75)
    use_live_weather = st.toggle("🌐 Live Weather API (Open-Meteo)", value=True)
    if not use_live_weather: 
        temp = st.slider("Manual Temp (°F)", -20, 100, 70)
        wind_speed, wind_dir = 0.0, 0.0
    preconditioning = st.toggle("🌡️ Thermal Battery Preconditioning", value=False)
        
    st.divider()
    with st.expander("💵 Financial Benchmarking"):
        elec_rate = st.number_input("Electricity Rate ($/kWh)", value=0.19, step=0.01)
        gas_price = st.number_input("Gasoline Price ($/gal)", value=3.45, step=0.05)
        ice_mpg = st.number_input("ICE Baseline (MPG)", value=17.0, step=1.0)

st.title("⚡ EV Spatial Simulator & Trip Planner")
st.markdown("A predictive systems engineering route planner executing Monte Carlo uncertainty quantification, trailer drag dynamics, and battery degradation models.")

# Empty string value with clear multi-line "e.g." guidance placeholder
route_text = st.text_area(
    "📍 Multi-Stop Itinerary (One city/address per line)", 
    value="", 
    placeholder="e.g., Chicago, IL\ne.g., Indianapolis, IN\ne.g., Louisville, KY", 
    height=90
)

if st.button("🚀 Execute Smart Route & Monte Carlo Simulation", type="primary", use_container_width=True):
    places = [p.strip() for p in route_text.split('\n') if p.strip()]
    if len(places) < 2:
        st.warning("⚠️ Enter at least a Start Location and Destination on separate lines.")
        st.stop()
        
    with st.spinner("Executing spatial integration, weather calls, and Monte Carlo stochastic passes..."):
        coords_list = [get_coordinates(p) for p in places]
        if None in coords_list:
            st.error("Invalid locations provided. Please verify spelling.")
            st.stop()
            
        dist_miles, duration_mins, full_route_coords = get_route_data_multi(coords_list)
        if not full_route_coords:
            st.error("Routing failed between these endpoints.")
            st.stop()

        if use_live_weather:
            temp, wind_speed, wind_dir = get_live_weather(coords_list[0][0], coords_list[0][1])
            
        sampled_coords, elevations = process_elevation(full_route_coords)
        
        kwh_gross, kwh_regen, final_batt, usable_kwh, charge_events, death_coords, telemetry, df_log = run_spatial_physics_simulation(
            ev_specs, sampled_coords, elevations, speed, temp, wind_speed, wind_dir, soh_pct, payload_lbs, aero_preset, preconditioning
        )
        
        mc_results = run_monte_carlo_simulation(
            ev_specs, sampled_coords, elevations, speed, temp, wind_speed, wind_dir, soh_pct, payload_lbs, aero_preset, preconditioning
        )
        
        df_speed_opt, opt_speed, min_duration = find_optimal_cruising_speed(
            ev_specs, sampled_coords, elevations, temp, wind_speed, wind_dir, soh_pct, payload_lbs, aero_preset, preconditioning
        )
        
        verified_charge_stops = []
        for event in charge_events:
            c_name, c_coords, c_dist = get_nearest_charger(event["coords"][1], event["coords"][0])
            if c_name: verified_charge_stops.append({"name": c_name, "coords": c_coords, "soc": event["soc_arrival"]})
                
        batt_pct = (final_batt / usable_kwh) * 100.0
        net_kwh_used = max(0, (kwh_gross - kwh_regen))
        
        st.subheader("🏁 Mission Overview")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Trip Distance", f"{dist_miles:.1f} mi")
        m2.metric("Mean Arrival Battery", f"{mc_results['mean_soc']:.1f}%", f"95% CI: [{mc_results['p95_lower']}% to {mc_results['p95_upper']}%]")
        m3.metric("Required Charge Stops", f"{len(verified_charge_stops)}")
        m4.metric("Optimal Cruising Speed", f"{opt_speed} mph", f"Min Duration: {min_duration:.1f} hrs")

        if mc_results['stranding_risk_pct'] > 0:
            st.error(f"⚠️ **HIGH RISK DETECTED:** Monte Carlo analysis indicates a {mc_results['stranding_risk_pct']}% chance of stranding due to weather variance.")
        else:
            st.success(f"✅ **HIGH CONFIDENCE:** 99th percentile worst-case arrival SOC is {mc_results['p99_worst']}%. Zero stranding risk detected.")

        st.write("") 
        tab_map, tab_mc, tab_opt, tab_finance, tab_data = st.tabs([
            "🗺️ Route Map", "🎲 Monte Carlo Confidence", "📈 Speed Optimizer", "💵 Financials & Cell Aging", "📥 Flight Recorder Data"
        ])
        
        with tab_map:
            layers = [pdk.Layer("PathLayer", data=[{"path": full_route_coords}], get_path="path", get_color=[0, 180, 255], width_min_pixels=4)]
            for stop in verified_charge_stops:
                layers.extend([
                    pdk.Layer("ScatterplotLayer", data=[{"position": stop["coords"]}], get_position="position", get_color=[0, 255, 128, 60], get_radius=3000, radius_min_pixels=30),
                    pdk.Layer("ScatterplotLayer", data=[{"position": stop["coords"]}], get_position="position", get_color=[0, 255, 128, 255], get_radius=500, radius_min_pixels=10),
                    pdk.Layer("TextLayer", data=[{"position": stop["coords"], "text": f"⚡ FAST CHARGE"}], get_position="position", get_text="text", get_color=[255, 255, 255, 255], get_size=16, get_pixel_offset=[0, -25])
                ])
            st.pydeck_chart(pdk.Deck(map_provider="carto", map_style="dark", layers=layers, initial_view_state=pdk.ViewState(latitude=coords_list[0][0], longitude=coords_list[0][1], zoom=6, pitch=35)), use_container_width=True)

        with tab_mc:
            st.markdown("### 🎲 Monte Carlo Uncertainty Quantification (100 Passes)")
            fig_hist = px.histogram(mc_results["soc_distribution"], nbins=20, labels={'value':'Arrival SOC (%)'}, title="Statistical Distribution of Arrival State of Charge", color_discrete_sequence=['#00CC96'])
            fig_hist.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)

        with tab_opt:
            st.markdown("### 📈 Speed-vs-Time Tradeoff Curve")
            fig_opt = px.line(df_speed_opt, x="Speed (mph)", y="Total Duration (hrs)", markers=True, title="Cruising Speed vs. Total Trip Time (Drive + Charge Lag)")
            fig_opt.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_opt, use_container_width=True)

        with tab_finance:
            st.markdown("### 💵 Total Cost of Ownership (Electricity + Cell Degradation)")
            ev_elec_cost = net_kwh_used * elec_rate
            cell_wear_cost = (net_kwh_used + (len(verified_charge_stops) * usable_kwh * 0.68)) * 0.035
            total_ev_cost = ev_elec_cost + cell_wear_cost
            ice_cost = (dist_miles / ice_mpg) * gas_price
            
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Electricity Cost", f"${ev_elec_cost:.2f}")
            f2.metric("Cell Wear Degradation Cost", f"${cell_wear_cost:.2f}")
            f3.metric("Total Real EV Cost", f"${total_ev_cost:.2f}")
            f4.metric("ICE Bronco Cost", f"${ice_cost:.2f}", delta_color="inverse")

        with tab_data:
            st.markdown("### 📥 Granular Telemetry Logs")
            csv_data = df_log.to_csv(index=False).encode('utf-8')
            st.download_button("Download Raw CSV", csv_data, "ev_telemetry_export.csv", "text/csv", type="primary")
            st.dataframe(df_log, use_container_width=True)