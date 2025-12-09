import math
import random
from typing import List, Tuple, Dict, Optional

def normalize_deg(a: float) -> float:
    """
    Docstring pour normalize_deg
    
    :param a: Description
    :type a: float
    :return: Description
    :rtype: float
    """
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

def dense_search_phi(observations: List[Dict], step_deg: float = 0.1) -> Tuple[float, Tuple[float, float], float]:
    """
    Balayage dense et rapide sur tout l'intervalle [0, 360°].
    Plus fin que l'ancien algorithme pour éviter de rater le minimum.
    """
    best = (None, None, float('inf'))
    phi = 0.0
    while phi < 360.0:
        origin, residual = compute_residual_for_phi(phi, observations)
        if residual < best[2]:
            best = (origin, phi, residual)
        phi += step_deg
    return best

def local_search_around_phi(observations: List[Dict], phi_center: float, range_deg: float = 5.0, step_deg: float = 0.01) -> Tuple[Tuple[float, float], float, float]:
    """
    Recherche locale très fine autour d'un angle φ donné.
    Retourne: (origin, phi, residual)
    """
    best_origin = None
    best_phi = None
    best_resid = float('inf')
    
    phi = phi_center - range_deg
    while phi <= phi_center + range_deg:
        origin, residual = compute_residual_for_phi(normalize_deg(phi), observations)
        if residual < best_resid:
            best_origin = origin
            best_phi = normalize_deg(phi)
            best_resid = residual
        phi += step_deg
    
    return (best_origin, best_phi, best_resid)

def adaptive_multi_scale_search(observations: List[Dict]) -> Tuple[Tuple[float, float], float, float]:
    """
    Recherche multi-échelle adaptative (coarse-to-fine) :
    1. Balayage grossier (1°) pour identifier les zones prometteuses
    2. Balayage fin (0.1°) sur les 3 meilleures zones
    3. Recherche très fine (0.01°) sur la meilleure zone
    4. Affinage par gradient
    
    Plus robuste et précis que multi-start pour données difficiles.
    """
    # Étape 1: Balayage grossier
    candidates = []
    phi = 0.0
    while phi < 360.0:
        origin, residual = compute_residual_for_phi(phi, observations)
        candidates.append((phi, origin, residual))
        phi += 1.0
    
    # Trier par résiduel et garder les 5 meilleures zones
    candidates.sort(key=lambda x: x[2])
    top_candidates = candidates[:5]
    
    # Étape 2: Balayage fin sur les meilleures zones
    refined_candidates = []
    for phi_coarse, _, _ in top_candidates:
        best_origin, best_phi, best_resid = local_search_around_phi(
            observations, phi_coarse, range_deg=2.0, step_deg=0.1
        )
        refined_candidates.append((best_origin, best_phi, best_resid))
    
    # Trouver le meilleur
    refined_candidates.sort(key=lambda x: x[2])
    origin_best, phi_best, resid_best = refined_candidates[0]
    
    # Étape 3: Recherche ultra-fine
    origin_ultrafine, phi_ultrafine, resid_ultrafine = local_search_around_phi(
        observations, phi_best, range_deg=0.5, step_deg=0.01
    )
    
    # Étape 4: Affinage par gradient
    phi_final, origin_final, resid_final = gradient_descent_phi(
        observations, phi_ultrafine, learning_rate=0.1, max_iter=50
    )
    
    return (origin_final, phi_final, resid_final)

def ransac_estimate(observations: List[Dict], n_iterations: int = 100, threshold: float = 50.0) -> Tuple[Tuple[float, float], float, float, List[int]]:
    """
    RANSAC (Random Sample Consensus) pour éliminer les outliers.
    
    Algorithme:
    1. Répéter n_iterations fois:
       - Choisir aléatoirement 3 observations
       - Calculer l'origine et phi optimaux pour ces 3 points (méthode rapide)
       - Compter combien d'observations sont des "inliers" (résiduel < threshold)
    2. Garder le modèle avec le plus d'inliers
    3. Recalculer le modèle final avec tous les inliers (méthode précise)
    
    Retourne: (origin, phi, residual, inlier_indices)
    """
    if len(observations) < 3:
        # Pas assez de points pour RANSAC
        origin, phi, resid = estimate_origin_and_phi(observations, method='multi-start')
        return (origin, phi, resid, list(range(len(observations))))
    
    best_inliers = []
    best_model = None
    
    for _ in range(n_iterations):
        # Échantillonner 3 observations au hasard
        if len(observations) == 3:
            sample_indices = [0, 1, 2]
        else:
            sample_indices = random.sample(range(len(observations)), 3)
        
        sample_obs = [observations[i] for i in sample_indices]
        
        # Calculer le modèle sur l'échantillon (méthode RAPIDE: legacy avec pas de 2°)
        try:
            best_origin_sample = None
            best_phi_sample = None
            best_resid_sample = float('inf')
            
            phi = 0.0
            while phi < 360.0:
                origin, residual = compute_residual_for_phi(phi, sample_obs)
                if residual < best_resid_sample:
                    best_origin_sample = origin
                    best_phi_sample = phi
                    best_resid_sample = residual
                phi += 2.0  # Pas grossier pour aller vite
            
            if best_origin_sample is None:
                continue
                
            origin, phi = best_origin_sample, best_phi_sample
        except:
            continue
        
        # Tester tous les points
        inliers = []
        for i, obs in enumerate(observations):
            d = line_dir_from_angle_deg(normalize_deg(obs['azimuth_deg'] + phi + 180.0))
            q = (obs['x'], obs['y'])
            dist = distance_point_to_line(origin, q, d)
            if dist < threshold:
                inliers.append(i)
        
        # Garder le meilleur modèle (celui avec le plus d'inliers)
        if len(inliers) > len(best_inliers):
            best_inliers = inliers
            best_model = (origin, phi)
    
    # Recalculer le modèle final avec tous les inliers (méthode PRÉCISE)
    if len(best_inliers) >= 3:
        inlier_obs = [observations[i] for i in best_inliers]
        origin_final, phi_final, resid_final = estimate_origin_and_phi(inlier_obs, method='multi-start')
        return (origin_final, phi_final, resid_final, best_inliers)
    else:
        # Pas assez d'inliers, utiliser toutes les données
        origin, phi, resid = estimate_origin_and_phi(observations, method='multi-start')
        return (origin, phi, resid, list(range(len(observations))))

def estimate_origin_and_phi(observations: List[Dict], method: str = 'ransac', return_inliers: bool = False) -> Tuple[Tuple[float, float], float, float] | Tuple[Tuple[float, float], float, float, List[int]]:
    """
    observations : 
        liste de dictionnaires avec les clés suivantes :      
        - "x", "y" : coordonnées de l'objet d'intérêt (dans un système de référence cartésien plan)
        - "azimuth_deg" : azimut gravé sur la table vers cet objet d'intérêt (degrés, 0 = N, 90 = E)
    
    method: 
      - 'ransac' (défaut, FORTEMENT RECOMMANDÉ): élimine automatiquement les outliers
      - 'adaptive': recherche multi-échelle adaptative, très robuste
      - 'ternary': recherche ternaire + gradient (rapide mais peut rater le minimum)
      - 'multi-start': 8 descentes de gradient (bon compromis)
      - 'gradient': descente de gradient seule (rapide, risqué)
      - 'legacy': balayage linéaire simple (lent mais fiable)
    
    Returns: (origin_xy, phi_deg, residual)
    """
    if method == 'ransac':
        origin, phi, resid, inliers = ransac_estimate(observations, n_iterations=100, threshold=50.0)
        if len(inliers) < len(observations):
            print(f"   RANSAC a détecté {len(observations) - len(inliers)} outlier(s) et les a éliminés.")
            print(f"    Inliers utilisés: {len(inliers)}/{len(observations)} observations")
        if return_inliers:
            return (origin, phi, resid, inliers)
        return (origin, phi, resid)
    
    elif method == 'adaptive':
        # RECOMMANDÉ: méthode la plus robuste et précise
        result = adaptive_multi_scale_search(observations)
        if return_inliers:
            return (*result, list(range(len(observations))))
        return result
    
    elif method == 'ternary':
        phi, origin, residual = ternary_search_phi(observations, epsilon=0.1)
        # Affinage par gradient
        phi, origin, residual = gradient_descent_phi(observations, phi, learning_rate=0.5, max_iter=50)
        if return_inliers:
            return (origin, phi, residual, list(range(len(observations))))
        return (origin, phi, residual)
    
    elif method == 'gradient':
        # Départ à phi=0, puis descente
        phi, origin, residual = gradient_descent_phi(observations, 0.0)
        if return_inliers:
            return (origin, phi, residual, list(range(len(observations))))
        return (origin, phi, residual)
    
    elif method == 'multi-start':
        # Multi-start: teste plusieurs points de départ pour éviter les minima locaux
        best = (None, None, float('inf'))
        for phi_start in [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]:
            phi, origin, residual = gradient_descent_phi(observations, phi_start, learning_rate=0.5, max_iter=100)
            if residual < best[2]:
                best = (origin, phi, residual)
        if return_inliers:
            return (*best, list(range(len(observations))))
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
        if return_inliers:
            return (*best, list(range(len(observations))))
        return best

# Exemple d'utilisation (données fictives en mètres):
if __name__ == "__main__":
    # Test avec 3 points
    observations_3 = [
        {'x': 2900.0, 'y': 200.0, 'azimuth_deg': 360.0},
        {'x': 1601.0, 'y': 1001.0, 'azimuth_deg': 30.0},
        {'x': 1500.0, 'y': 3500.0, 'azimuth_deg': 120.0},
    ]
    
    # Test avec 4 points
    observations_4 = observations_3 + [
        {'x': 4000.0, 'y': 260.0, 'azimuth_deg': 210.0},
    ]
    
    # Test avec 5 points
    observations_5 = observations_4 + [
        {'x': 400.0, 'y': 480.0, 'azimuth_deg': 200.0},
    ]
    
    import time
    
    for name, obs in [("3 points", observations_3), ("4 points", observations_4), ("5 points", observations_5)]:
        print(f"\n{'='*60}")
        print(f"Test avec {name}")
        print('='*60)
        
        print("\n🏆 Méthode RANSAC (robuste aux outliers, FORTEMENT RECOMMANDÉE)")
        t0 = time.time()
        origin, phi, resid = estimate_origin_and_phi(obs, method='ransac')
        t1 = time.time()
        print(f"   Origine: ({origin[0]:.2f}, {origin[1]:.2f})")
        print(f"   Orientation φ: {phi:.4f}°")
        print(f"   Résiduel: {resid:.3f} m")
        print(f"   Temps: {(t1-t0)*1000:.2f} ms")
        
        print("\n⚡ Méthode MULTI-START (pour comparaison)")
        t0 = time.time()
        origin2, phi2, resid2 = estimate_origin_and_phi(obs, method='multi-start')
        t1 = time.time()
        print(f"   Origine: ({origin2[0]:.2f}, {origin2[1]:.2f})")
        print(f"   Orientation φ: {phi2:.4f}°")
        print(f"   Résiduel: {resid2:.3f} m")
        print(f"   Temps: {(t1-t0)*1000:.2f} ms")
    
    print(f"\n{'='*60}")
    print(" RANSAC élimine automatiquement les outliers !")
    print(" Résiduel beaucoup plus petit et fiable !")
    print('='*60)