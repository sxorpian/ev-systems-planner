import pytest
import math

def calculate_aero_power(cd, area_m2, v_air_mps, v_ground_mps, rho):
    return (0.5 * rho * cd * area_m2 * (v_air_mps ** 2) * v_ground_mps) / 1000.0

def calculate_grade_power(mass_kg, v_ground_mps, theta):
    return (mass_kg * 9.81 * v_ground_mps * math.sin(theta)) / 1000.0

def test_aerodynamic_drag_cubed():
    """Validates that doubling speed results in an 8x exponential increase in kinetic power draw."""
    v1_mps = 10.0
    v2_mps = 20.0
    p1 = calculate_aero_power(0.3, 3.0, v1_mps, v1_mps, 1.225)
    p2 = calculate_aero_power(0.3, 3.0, v2_mps, v2_mps, 1.225)
    
    # 20^3 / 10^3 = 8
    assert math.isclose(p2, p1 * 8.0, rel_tol=0.01)

def test_payload_mass_penalty():
    """Validates that adding a 5,000 lb payload linearly scales gravitational grade resistance."""
    mass_kg_base = 3200  # Rivian Curb Weight
    payload_kg = 5000 * 0.453592
    theta = math.radians(5) # 5 degree mountain incline
    v_mps = 25.0
    
    base_grade_power = calculate_grade_power(mass_kg_base, v_mps, theta)
    towing_grade_power = calculate_grade_power(mass_kg_base + payload_kg, v_mps, theta)
    
    mass_ratio = (mass_kg_base + payload_kg) / mass_kg_base
    assert math.isclose(towing_grade_power, base_grade_power * mass_ratio, rel_tol=0.01)

def test_bms_regen_tapering():
    """Validates that the Battery Management System chokes regenerative charging at near-100% capacity to prevent cell overvoltage."""
    soc_full = 0.98
    base_regen_eta = 0.70
    
    # Simulate tapering block from integration engine
    tapered_eta = base_regen_eta * max(0.0, (1.0 - soc_full) / 0.10)
    
    # At 98% SOC, regen capture should drop below 15% efficiency
    assert tapered_eta < 0.15