import math
from typing import List, Tuple, Dict, Optional

def normalize_deg(a: float) -> float:
    a = a % 360.0
    return a if a >= 0 else a + 360.0

def deg2rad(a: float) -> float:
    return a * math.pi / 180.0

def line_dir_from_angle_deg(angle_deg: float) -> Tuple[float, float]:
    r = deg2rad(angle_deg)
    return (math.cos(r), math.sin(r))

def cross2(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx

def intersect_lines(p1: Tuple[float, float], d1: Tuple[float, float],
                    p2: Tuple[float, float], d2: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    # p1 + t d1 = p2 + u d2
    denom = cross2(d1[0], d1[1], d2[0], d2[1])
    if abs(denom) < 1e-12:
        return None  # lignes presque parallèles
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    t = cross2(dx, dy, d2[0], d2[1]) / denom
    return (p1[0] + t * d1[0], p1[1] + t * d1[1])

def distance_point_to_line(p: Tuple[float, float], q: Tuple[float, float], d: Tuple[float, float]) -> float:
    # distance = | cross(d, p - q) | / ||d||
    px, py = p
    qx, qy = q
    dx, dy = d
    num = abs(cross2(dx, dy, px - qx, py - qy))
    den = math.hypot(dx, dy)
    return num / den

def least_squares_origin(lines: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> Tuple[float, float]:
    """
    Calcule l'origine optimale par moindres carrés.
    Minimise la somme des carrés des distances aux droites.
    
    Méthode mathématique:
    Pour chaque droite (q, d), la distance d'un point (x, y) à la droite est:
    dist = |d_y*(x - q_x) - d_x*(y - q_y)| / sqrt(d_x^2 + d_y^2)
    
    On minimise sum(dist^2) en résolvant le système linéaire 2x2:
    A * [x0, y0]^T = b
    """
    if len(lines) == 0:
        return (0.0, 0.0)
    
    # Construction de la matrice normale A et du vecteur b
    a11, a12, a22 = 0.0, 0.0, 0.0
    b1, b2 = 0.0, 0.0
    
    for (qx, qy), (dx, dy) in lines:
        # Normalisation de la direction
        norm = math.hypot(dx, dy)
        if norm < 1e-12:
            continue
        dx, dy = dx / norm, dy / norm
        
        # Contributions au système normal
        # Équation de droite: dy*x - dx*y = dy*qx - dx*qy
        a11 += dy * dy
        a12 -= dy * dx
        a22 += dx * dx
        
        rhs = dy * qx - dx * qy
        b1 += dy * rhs
        b2 -= dx * rhs
    
    # Résolution du système 2x2
    det = a11 * a22 - a12 * a12
    if abs(det) < 1e-12:
        # Système singulier, on retourne le barycentre des points q
        xs = [q[0] for q, d in lines]
        ys = [q[1] for q, d in lines]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    
    x0 = (a22 * b1 - a12 * b2) / det
    y0 = (a11 * b2 - a12 * b1) / det
    
    return (x0, y0)

def compute_residual_for_phi(phi: float, observations: List[Dict]) -> Tuple[Tuple[float, float], float]:
    """
    Calcule l'origine optimale et le résiduel pour un angle phi donné.
    Retourne: (origin, residual)
    """
    lines = []
    for obs in observations:
        back_bearing = normalize_deg(obs['azimuth_deg'] + phi + 180.0)
        d = line_dir_from_angle_deg(back_bearing)
        q = (obs['x'], obs['y'])
        lines.append((q, d))
    
    origin = least_squares_origin(lines)
    
    # Calcul du résiduel
    residuals = [distance_point_to_line(origin, q, d) for (q, d) in lines]
    residual = sum(residuals) / len(residuals) if residuals else float('inf')
    
    return (origin, residual)

def ternary_search_phi(observations: List[Dict], epsilon: float = 0.01) -> Tuple[float, Tuple[float, float], float]:
    """
    Recherche ternaire pour trouver le phi optimal.
    
    Méthode mathématique:
    La recherche ternaire exploite l'unimodalité de la fonction résiduelle.
    À chaque itération, on divise l'intervalle en trois parties et on élimine
    le tiers avec la plus grande valeur. Complexité: O(log(360/epsilon)).
    
    Retourne: (phi_optimal, origin, residual)
    """
    left, right = 0.0, 360.0
    
    while right - left > epsilon:
        mid1 = left + (right - left) / 3.0
        mid2 = right - (right - left) / 3.0
        
        origin1, res1 = compute_residual_for_phi(mid1, observations)
        origin2, res2 = compute_residual_for_phi(mid2, observations)
        
        if res1 > res2:
            left = mid1
        else:
            right = mid2
    
    phi_opt = (left + right) / 2.0
    origin_opt, residual_opt = compute_residual_for_phi(phi_opt, observations)
    
    return (phi_opt, origin_opt, residual_opt)

def gradient_descent_phi(observations: List[Dict], phi_init: float, learning_rate: float = 0.1, max_iter: int = 100) -> Tuple[float, Tuple[float, float], float]:
    """
    Affine phi par descente de gradient.
    
    Méthode mathématique:
    On calcule la dérivée numérique du résiduel par rapport à phi:
    df/dphi ≈ (f(phi + h) - f(phi - h)) / (2h)
    
    Puis on met à jour: phi_new = phi - learning_rate * df/dphi
    Convergence typique en O(log(1/epsilon)) itérations.
    """
    phi = phi_init
    h = 0.01  # Pas pour la dérivée numérique
    
    for _ in range(max_iter):
        origin_minus, res_minus = compute_residual_for_phi(normalize_deg(phi - h), observations)
        origin_plus, res_plus = compute_residual_for_phi(normalize_deg(phi + h), observations)
        
        # Gradient numérique
        gradient = (res_plus - res_minus) / (2.0 * h)
        
        # Mise à jour
        phi_new = normalize_deg(phi - learning_rate * gradient)
        
        # Test de convergence
        if abs(phi_new - phi) < 0.001:
            break
        
        phi = phi_new
    
    origin_final, residual_final = compute_residual_for_phi(phi, observations)
    return (phi, origin_final, residual_final)

def estimate_origin_and_phi(observations: List[Dict], method: str = 'ternary') -> Tuple[Tuple[float, float], float, float]:
    """
    observations: list of dicts with keys:
      - 'x', 'y': coordinates of the curiosity (in a planar CRS)
      - 'azimuth_deg': azimuth engraved on the table towards that curiosity (degrees, 0=N, 90=E)
    
    method: 'ternary' (défaut, plus rapide), 'gradient', ou 'legacy' (ancien algorithme)
    
    Returns: (origin_xy, phi_deg, residual)
    
    Améliorations mathématiques:
    1. Recherche ternaire: O(log m) au lieu de O(m) pour phi
    2. Moindres carrés: solution analytique optimale pour l'origine
    3. Descente de gradient: convergence rapide vers le minimum local
    4. Multi-start: teste plusieurs valeurs initiales pour éviter les minima locaux
    """
    if method == 'ternary':
        phi, origin, residual = ternary_search_phi(observations, epsilon=0.1)
        # Affinage par gradient
        phi, origin, residual = gradient_descent_phi(observations, phi, learning_rate=0.5, max_iter=50)
        return (origin, phi, residual)
    
    elif method == 'gradient':
        # Départ à phi=0, puis descente
        phi, origin, residual = gradient_descent_phi(observations, 0.0)
        return (origin, phi, residual)
    
    elif method == 'multi-start':
        # Multi-start: teste plusieurs points de départ pour éviter les minima locaux
        best = (None, None, float('inf'))
        for phi_start in [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]:
            phi, origin, residual = gradient_descent_phi(observations, phi_start, learning_rate=0.5, max_iter=100)
            if residual < best[2]:
                best = (origin, phi, residual)
        return best
    
    else:  # legacy
        # Ancien algorithme (pour comparaison)
        best = (None, None, float('inf'))
        phi = 0.0
        while phi < 360.0:
            origin, residual = compute_residual_for_phi(phi, observations)
            if residual < best[2]:
                best = (origin, phi, residual)
            phi += 0.5
        return best

# Exemple d'utilisation (données fictives en mètres):
if __name__ == "__main__":
    observations = [
        {'x': 2900.0, 'y': 200.0, 'azimuth_deg': 360.0},
        {'x': 1601.0, 'y': 1001.0, 'azimuth_deg': 30.0},
        {'x': 1500.0, 'y': 3500.0, 'azimuth_deg': 120.0},
    ]
    
    print("=== Méthode multi-start (8 points de départ + gradient) ===")
    import time
    t0 = time.time()
    origin, phi, resid = estimate_origin_and_phi(observations, method='multi-start')
    t1 = time.time()
    print(f"Origine estimée: ({origin[0]:.2f}, {origin[1]:.2f})")
    print(f"Orientation globale φ: {phi:.4f}°")
    print(f"Résiduel moyen: {resid:.3f} m")
    print(f"Temps d'exécution: {(t1-t0)*1000:.2f} ms\n")
    
    print("=== Méthode classique (balayage linéaire) pour comparaison ===")
    t0 = time.time()
    origin2, phi2, resid2 = estimate_origin_and_phi(observations, method='legacy')
    t1 = time.time()
    print(f"Origine estimée: ({origin2[0]:.2f}, {origin2[1]:.2f})")
    print(f"Orientation globale φ: {phi2:.4f}°")
    print(f"Résiduel moyen: {resid2:.3f} m")
    print(f"Temps d'exécution: {(t1-t0)*1000:.2f} ms")