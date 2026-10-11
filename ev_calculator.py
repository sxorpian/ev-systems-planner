# ev_route_mapper.py

# EV Database: Stores Usable Battery Capacity (kWh) & EPA Range
EV_DATABASE = {
    "1": {"name": "Tesla Model 3 Long Range", "kwh": 75.0, "epa": 333, "type": "Sedan"},
    "2": {"name": "Rivian R1T (Large Pack)", "kwh": 135.0, "epa": 352, "type": "Truck"},
    "3": {"name": "Ford F-150 Lightning ER", "kwh": 131.0, "epa": 320, "type": "Truck"}
}

def calculate_real_efficiency(base_mi_kwh, speed_mph, temp_f, v_type):
    """Applies climate and aerodynamic penalties to the base vehicle efficiency."""
    # Heating a cabin in the cold drains the battery heavily
    temp_loss = (70 - temp_f) * 0.008 if temp_f < 70 else 0
    
    # Drag increases exponentially above 55mph; trucks suffer more than sedans
    drag_multiplier = 0.015 if v_type == "Sedan" else 0.025
    speed_loss = (speed_mph - 55) * drag_multiplier if speed_mph > 55 else 0
    
    # Cap total efficiency loss at 95% to prevent mathematical errors
    total_loss = min(temp_loss + speed_loss, 0.95) 
    return base_mi_kwh * (1 - total_loss)

# --- APPLICATION START ---
print("--- EV Route & Battery Mapper ---")
for key, ev in EV_DATABASE.items():
    print(f"[{key}] {ev['name']} ({ev['kwh']} kWh | {ev['epa']} EPA mi)")

choice = input("\nSelect EV (1-3): ")
selected_ev = EV_DATABASE.get(choice, EV_DATABASE["1"])

# Calculate the baseline miles per kWh
base_efficiency = selected_ev["epa"] / selected_ev["kwh"]
current_battery_kwh = selected_ev["kwh"]

print(f"\n[Loaded] {selected_ev['name']} | Base Efficiency: {base_efficiency:.2f} mi/kWh")

legs = int(input("\nHow many legs are in your route? "))
total_distance = 0.0
total_kwh_used = 0.0

# --- ROUTE MAPPING LOOP ---
for i in range(legs):
    print(f"\n--- Leg {i+1} ---")
    dist = float(input("Distance (miles): "))
    spd = float(input("Average Speed (mph): "))
    tmp = float(input("Temperature (F): "))
    
    # Calculate the penalty for this specific segment of the drive
    leg_eff = calculate_real_efficiency(base_efficiency, spd, tmp, selected_ev["type"])
    kwh_used = dist / leg_eff
    
    # Drain the battery
    current_battery_kwh -= kwh_used
    total_distance += dist
    total_kwh_used += kwh_used
    
    print(f"> Leg {i+1} Real Efficiency: {leg_eff:.2f} mi/kWh")
    print(f"> Energy Consumed:       {kwh_used:.1f} kWh")
    
    # Stranded Check
    if current_battery_kwh <= 0:
        print("\n[!] CRITICAL: BATTERY DEPLETED. VEHICLE STRANDED.")
        break

# --- FINAL TRIP DATA ---
if current_battery_kwh > 0:
    batt_pct = (current_battery_kwh / selected_ev["kwh"]) * 100
    trip_avg_eff = total_distance / total_kwh_used
    
    # Calculate how far the car can go based on how you just drove it, not the EPA rating
    dynamic_range_left = current_battery_kwh * trip_avg_eff
    
    print("\n===============================")
    print("      FINAL ARRIVAL STATS      ")
    print("===============================")
    print(f"Total Distance:       {total_distance:.1f} miles")
    print(f"Overall Efficiency:   {trip_avg_eff:.2f} mi/kWh")
    print(f"Battery Remaining:    {batt_pct:.1f}% ({current_battery_kwh:.1f} kWh)")
    print(f"Dynamic Range Left:   {dynamic_range_left:.1f} miles")# ev_route_mapper.py

# EV Database: Stores Usable Battery Capacity (kWh) & EPA Range
EV_DATABASE = {
    "1": {"name": "Tesla Model 3 Long Range", "kwh": 75.0, "epa": 333, "type": "Sedan"},
    "2": {"name": "Rivian R1T (Large Pack)", "kwh": 135.0, "epa": 352, "type": "Truck"},
    "3": {"name": "Ford F-150 Lightning ER", "kwh": 131.0, "epa": 320, "type": "Truck"}
}

def calculate_real_efficiency(base_mi_kwh, speed_mph, temp_f, v_type):
    """Applies climate and aerodynamic penalties to the base vehicle efficiency."""
    # Heating a cabin in the cold drains the battery heavily
    temp_loss = (70 - temp_f) * 0.008 if temp_f < 70 else 0
    
    # Drag increases exponentially above 55mph; trucks suffer more than sedans
    drag_multiplier = 0.015 if v_type == "Sedan" else 0.025
    speed_loss = (speed_mph - 55) * drag_multiplier if speed_mph > 55 else 0
    
    # Cap total efficiency loss at 95% to prevent mathematical errors
    total_loss = min(temp_loss + speed_loss, 0.95) 
    return base_mi_kwh * (1 - total_loss)

# --- APPLICATION START ---
print("--- EV Route & Battery Mapper ---")
for key, ev in EV_DATABASE.items():
    print(f"[{key}] {ev['name']} ({ev['kwh']} kWh | {ev['epa']} EPA mi)")

choice = input("\nSelect EV (1-3): ")
selected_ev = EV_DATABASE.get(choice, EV_DATABASE["1"])

# Calculate the baseline miles per kWh
base_efficiency = selected_ev["epa"] / selected_ev["kwh"]
current_battery_kwh = selected_ev["kwh"]

print(f"\n[Loaded] {selected_ev['name']} | Base Efficiency: {base_efficiency:.2f} mi/kWh")

legs = int(input("\nHow many legs are in your route? "))
total_distance = 0.0
total_kwh_used = 0.0

# --- ROUTE MAPPING LOOP ---
for i in range(legs):
    print(f"\n--- Leg {i+1} ---")
    dist = float(input("Distance (miles): "))
    spd = float(input("Average Speed (mph): "))
    tmp = float(input("Temperature (F): "))
    
    # Calculate the penalty for this specific segment of the drive
    leg_eff = calculate_real_efficiency(base_efficiency, spd, tmp, selected_ev["type"])
    kwh_used = dist / leg_eff
    
    # Drain the battery
    current_battery_kwh -= kwh_used
    total_distance += dist
    total_kwh_used += kwh_used
    
    print(f"> Leg {i+1} Real Efficiency: {leg_eff:.2f} mi/kWh")
    print(f"> Energy Consumed:       {kwh_used:.1f} kWh")
    
    # Stranded Check
    if current_battery_kwh <= 0:
        print("\n[!] CRITICAL: BATTERY DEPLETED. VEHICLE STRANDED.")
        break

# --- FINAL TRIP DATA ---
if current_battery_kwh > 0:
    batt_pct = (current_battery_kwh / selected_ev["kwh"]) * 100
    trip_avg_eff = total_distance / total_kwh_used
    
    # Calculate how far the car can go based on how you just drove it, not the EPA rating
    dynamic_range_left = current_battery_kwh * trip_avg_eff
    
    print("\n===============================")
    print("      FINAL ARRIVAL STATS      ")
    print("===============================")
    print(f"Total Distance:       {total_distance:.1f} miles")
    print(f"Overall Efficiency:   {trip_avg_eff:.2f} mi/kWh")
    print(f"Battery Remaining:    {batt_pct:.1f}% ({current_battery_kwh:.1f} kWh)")
    print(f"Dynamic Range Left:   {dynamic_range_left:.1f} miles")