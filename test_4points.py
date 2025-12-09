from table import estimate_origin_and_phi
import time

# Test avec 4 points
observations = [
    {'x': 2900.0, 'y': 200.0, 'azimuth_deg': 360.0},
    {'x': 1601.0, 'y': 1001.0, 'azimuth_deg': 30.0},
    {'x': 1500.0, 'y': 3500.0, 'azimuth_deg': 120.0},
    {'x': 4000.0, 'y': 260.0, 'azimuth_deg': 210.0},
]

print("=== Test avec 4 points ===\n")
print("Multi-start:")
t0 = time.time()
origin, phi, resid = estimate_origin_and_phi(observations, method='multi-start')
t1 = time.time()
print(f"Origine: ({origin[0]:.2f}, {origin[1]:.2f})")
print(f"φ: {phi:.4f}°, Résiduel: {resid:.3f} m")
print(f"Temps: {(t1-t0)*1000:.2f} ms\n")

print("Legacy:")
t0 = time.time()
origin2, phi2, resid2 = estimate_origin_and_phi(observations, method='legacy')
t1 = time.time()
print(f"Origine: ({origin2[0]:.2f}, {origin2[1]:.2f})")
print(f"φ: {phi2:.4f}°, Résiduel: {resid2:.3f} m")
print(f"Temps: {(t1-t0)*1000:.2f} ms\n")

# Test avec 5 points
observations5 = observations + [{'x': 400.0, 'y': 480.0, 'azimuth_deg': 200.0}]
print("=== Test avec 5 points ===\n")
print("Multi-start:")
origin, phi, resid = estimate_origin_and_phi(observations5, method='multi-start')
print(f"Origine: ({origin[0]:.2f}, {origin[1]:.2f})")
print(f"φ: {phi:.4f}°, Résiduel: {resid:.3f} m\n")

print("Legacy:")
origin2, phi2, resid2 = estimate_origin_and_phi(observations5, method='legacy')
print(f"Origine: ({origin2[0]:.2f}, {origin2[1]:.2f})")
print(f"φ: {phi2:.4f}°, Résiduel: {resid2:.3f} m")
