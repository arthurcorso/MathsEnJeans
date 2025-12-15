"""
Script de test pour comparer les méthodes d'optimisation.

Compare RANSAC (robuste) vs multi-start (rapide) sur des jeux de données
avec 4 et 5 points d'observation.
"""

from table import estimate_origin_and_phi
import time


def test_observations(observations, name):
    """Teste différentes méthodes sur un jeu d'observations."""
    print(f"\n{'='*60}")
    print(f"Test avec {name}")
    print('='*60 + '\n')
    
    # RANSAC (recommandé)
    print("🏆 Méthode RANSAC (robuste aux outliers)")
    t0 = time.time()
    origin, phi, resid = estimate_origin_and_phi(observations, method='ransac')
    t1 = time.time()
    print(f"   Origine: ({origin[0]:.2f}, {origin[1]:.2f})")
    print(f"   φ: {phi:.4f}°")
    print(f"   Résiduel: {resid:.3f} m")
    print(f"   Temps: {(t1-t0)*1000:.2f} ms\n")
    
    # Multi-start (pour comparaison)
    print("⚡ Méthode MULTI-START (pour comparaison)")
    t0 = time.time()
    origin2, phi2, resid2 = estimate_origin_and_phi(observations, method='multi-start')
    t1 = time.time()
    print(f"   Origine: ({origin2[0]:.2f}, {origin2[1]:.2f})")
    print(f"   φ: {phi2:.4f}°")
    print(f"   Résiduel: {resid2:.3f} m")
    print(f"   Temps: {(t1-t0)*1000:.2f} ms")


if __name__ == "__main__":
    # Jeu de test avec 4 points
    observations_4 = [
        {'x': 2900.0, 'y': 200.0, 'azimuth_deg': 360.0},
        {'x': 1601.0, 'y': 1001.0, 'azimuth_deg': 30.0},
        {'x': 1500.0, 'y': 3500.0, 'azimuth_deg': 120.0},
        {'x': 4000.0, 'y': 260.0, 'azimuth_deg': 210.0},
    ]
    
    # Jeu de test avec 5 points (dont possiblement des outliers)
    observations_5 = observations_4 + [
        {'x': 400.0, 'y': 480.0, 'azimuth_deg': 200.0}
    ]
    
    test_observations(observations_4, "4 points")
    test_observations(observations_5, "5 points")
    
    print(f"\n{'='*60}")
    print("💡 RANSAC détecte et élimine automatiquement les outliers !")
    print("   → Résiduel plus petit et fiable")
    print('='*60)
