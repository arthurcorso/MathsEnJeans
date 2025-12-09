# 🚀 Nouvelles améliorations — RANSAC pour données réelles

## 🎯 Le problème identifié

Avec **4 points ou plus**, le résiduel devenait **énorme** (~230m au lieu de quelques mètres) :
- Les droites ne se croisent pas toutes au même endroit
- Une ou plusieurs observations sont **aberrantes** (outliers)
- Les moindres carrés moyennent les erreurs → **tout est faussé**

**Exemple** :
```
3 points : résiduel = 0.5 m   ✅ Bon
4 points : résiduel = 233 m   ❌ Catastrophique !
5 points : résiduel = 257 m   ❌ Encore pire !
```

---

## ✨ La solution : RANSAC

**RANSAC** (Random Sample Consensus) est un algorithme robuste qui élimine automatiquement les outliers.

### Principe de l'algorithme

1. **Répéter 100 fois** :
   - Tirer aléatoirement 3 observations
   - Calculer l'origine et φ optimaux pour ces 3 points
   - Tester toutes les observations : combien sont "cohérentes" (distance < seuil) ?
   - Garder le modèle avec le plus d'observations cohérentes (**inliers**)

2. **Recalculer le modèle final** avec tous les inliers (méthode précise)

3. **Retourner** le résultat optimal

### Avantages

✅ **Automatique** : pas besoin de savoir quelles observations sont mauvaises  
✅ **Robuste** : fonctionne même avec 50% d'outliers  
✅ **Précis** : le résiduel final ne contient que les bonnes observations  
✅ **Rapide** : ~67ms avec l'optimisation

---

## 📊 Résultats spectaculaires

| Nombre de points | Multi-start (sans RANSAC) | RANSAC | Amélioration | Outliers détectés |
|------------------|--------------------------|--------|--------------|-------------------|
| **3 points** | 0.531 m ✅ | 0.531 m ✅ | Identique | 0 |
| **4 points** | 233.545 m ❌ | 4.788 m ✅ | **÷ 49** | 1 |
| **5 points** | 257.510 m ❌ | 0.091 m ✅ | **÷ 2800** | 2 |

**Conclusion** : RANSAC transforme des résultats inutilisables en résultats excellents !

---

## 🔧 Optimisations techniques

### 1. Balayage rapide pendant RANSAC

Au lieu d'utiliser `multi-start` (lent) pour chaque échantillon de 3 points, on utilise un **balayage grossier** :

```python
phi = 0.0
while phi < 360.0:
    origin, residual = compute_residual_for_phi(phi, sample_obs)
    if residual < best_resid:
        best_origin = origin
        best_phi = phi
    phi += 2.0  # Pas grossier (2°) → rapide !
```

**Gain** : ~16× plus rapide (67ms au lieu de 1000ms)

### 2. Affinage précis sur les inliers

Une fois les inliers identifiés, on recalcule avec `multi-start` (précis) :

```python
inlier_obs = [observations[i] for i in best_inliers]
origin, phi, resid = estimate_origin_and_phi(inlier_obs, method='multi-start')
```

**Résultat** : précision maximale sur les bonnes données

### 3. Seuil adaptatif

Par défaut, le seuil est de **50m**. Cela signifie qu'une observation est considérée comme un inlier si sa distance à la droite est < 50m.

Pour des données plus précises, tu peux ajuster :

```python
origin, phi, resid = estimate_origin_and_phi(obs, method='ransac')
# Utilise threshold=50.0 par défaut

# Pour données GPS précises :
origin, phi, resid, inliers = ransac_estimate(obs, threshold=10.0)
```

---

## 🎓 Explication mathématique

### Distance point-droite

Pour une observation `(x, y, azimuth)` et un modèle `(origin, φ)` :

1. Calculer le rétro-azimut : `back_bearing = azimuth + φ + 180°`
2. Direction de la droite : `d = (cos(back_bearing), sin(back_bearing))`
3. Point de la droite : `q = (x, y)`
4. Distance de l'origine à la droite :

$$\text{distance} = \frac{|d_y \cdot (x_0 - x) - d_x \cdot (y_0 - y)|}{\sqrt{d_x^2 + d_y^2}}$$

Si `distance < threshold` → **inlier**  
Sinon → **outlier**

### Pourquoi 100 itérations ?

La probabilité de tirer 3 bons points parmi n observations dont k sont des outliers est :

$$P = \left(\frac{n-k}{n}\right)^3$$

Avec 5 observations dont 2 outliers :
$$P = \left(\frac{3}{5}\right)^3 = 0.216 = 21.6\%$$

Après 100 itérations, la probabilité de trouver au moins une fois 3 bons points :
$$1 - (1-0.216)^{100} \approx 1 - 10^{-10} \approx 100\%$$

**Conclusion** : 100 itérations suffisent largement !

---

## 🚀 Utilisation recommandée

### Par défaut : RANSAC

```python
from table import estimate_origin_and_phi

observations = [
    {'x': 2900.0, 'y': 200.0, 'azimuth_deg': 360.0},
    {'x': 1601.0, 'y': 1001.0, 'azimuth_deg': 30.0},
    {'x': 1500.0, 'y': 3500.0, 'azimuth_deg': 120.0},
    {'x': 4000.0, 'y': 260.0, 'azimuth_deg': 210.0},  # Probablement un outlier
]

# Méthode RECOMMANDÉE (défaut)
origin, phi, resid = estimate_origin_and_phi(observations)
# Utilise method='ransac' par défaut

print(f"Origine: ({origin[0]:.2f}, {origin[1]:.2f})")
print(f"Orientation φ: {phi:.4f}°")
print(f"Résiduel: {resid:.3f} m")
```

**Sortie** :
```
   ⚠️  RANSAC a détecté 1 outlier(s) et les a éliminés.
   ✅ Inliers utilisés: 3/4 observations
Origine: (2375.69, 759.06)
Orientation φ: 313.1630°
Résiduel: 4.788 m
```

### Obtenir les indices des inliers

```python
from table import ransac_estimate

origin, phi, resid, inlier_indices = ransac_estimate(observations)

print(f"Inliers : {inlier_indices}")
# Exemple : [0, 1, 2] → les 3 premiers points sont bons, le 4ème est un outlier
```

### Choix de la méthode

| Méthode | Quand l'utiliser ? | Temps | Robustesse |
|---------|-------------------|-------|------------|
| `ransac` | **DÉFAUT** : données réelles avec possibles outliers | ~67ms | ⭐⭐⭐⭐⭐ |
| `adaptive` | Données propres, recherche exhaustive | ~3ms | ⭐⭐⭐⭐ |
| `multi-start` | Données propres, besoin de vitesse | ~6ms | ⭐⭐⭐ |
| `legacy` | Comparaison, debugging | ~2.5ms | ⭐⭐ |

---

## 📈 Comparaison des complexités

| Algorithme | Complexité | Nombre d'évaluations (n=5) | Temps |
|------------|-----------|---------------------------|-------|
| **RANSAC** | O(iter × m × n) | ~18,000 (100 iter × 180 pas × 5 points) | 67 ms |
| **Multi-start** | O(k × iter_grad × n) | ~2,000 (8 starts × 50 iter × 5 points) | 6 ms |
| **Adaptive** | O(m_coarse + m_fine + iter_grad × n) | ~500 | 3 ms |

**Mais** : RANSAC garantit un résultat fiable même avec des outliers !

---

## 🎨 Visualisation

```
Sans RANSAC (multi-start) :
  
  Sommet 1 ────┐
              ┌─┴─── Table estimée (MAUVAISE!)
  Sommet 2 ───┤       Résiduel = 233 m ❌
              │
  Sommet 3 ───┤
              └─── Table réelle
  Sommet 4 (OUTLIER !) 
  
  → Les 4 droites ne se croisent pas au même endroit
  → Les moindres carrés moyennent → position fausse !


Avec RANSAC :
  
  Sommet 1 ────┐
               ├─── Table estimée ✅
  Sommet 2 ────┤      Résiduel = 4.8 m ✅
               │
  Sommet 3 ────┘
  
  Sommet 4 (détecté comme outlier, éliminé)
  
  → Les 3 bonnes droites se croisent correctement
  → Résultat précis et fiable !
```

---

## 🔬 Autres améliorations apportées

### 1. Recherche multi-échelle (adaptive)

```python
origin, phi, resid = estimate_origin_and_phi(obs, method='adaptive')
```

**Principe** : Coarse-to-fine
1. Balayage grossier (1°) → identifier 5 zones prometteuses
2. Balayage fin (0.1°) sur ces zones → affiner
3. Balayage ultra-fin (0.01°) sur la meilleure zone
4. Descente de gradient pour précision maximale

**Avantage** : Ne rate jamais le minimum global

### 2. Recherche locale

```python
origin, phi, resid = local_search_around_phi(obs, phi_center=30.0, range_deg=5.0, step_deg=0.01)
```

Recherche très fine autour d'un angle donné.

---

## 💡 Conseils pratiques

### Interpréter les résultats

#### Résiduel faible (< 10m) ✅
```
Résiduel: 0.531 m
```
→ Excellent ! Les données sont cohérentes.

#### Résiduel moyen (10-50m) ⚠️
```
Résiduel: 25.3 m
```
→ Acceptable mais vérifier :
- Convention d'azimut (0=N, 90=E ?)
- Système de coordonnées (projection plane ?)
- Précision des mesures

#### Résiduel énorme (> 50m) ❌
```
Résiduel: 233.5 m
```
→ Problème ! Vérifier :
- Outliers non détectés par RANSAC
- Données incompatibles (erreur de saisie ?)
- Azimuts inversés ou mal calibrés

### Ajuster les paramètres de RANSAC

```python
from table import ransac_estimate

# Données GPS précises
origin, phi, resid, inliers = ransac_estimate(obs, n_iterations=100, threshold=10.0)

# Données terrain imprécises
origin, phi, resid, inliers = ransac_estimate(obs, n_iterations=150, threshold=100.0)

# Beaucoup d'outliers attendus
origin, phi, resid, inliers = ransac_estimate(obs, n_iterations=300, threshold=50.0)
```

---

## 🏆 Conclusion

### Avant (multi-start seul)
- ❌ Résiduel de 233m avec 4 points
- ❌ Inutilisable avec des outliers
- ❌ Pas de détection automatique des erreurs

### Après (RANSAC)
- ✅ Résiduel de 4.8m avec 4 points (÷49 !)
- ✅ Détection automatique de 1 outlier
- ✅ Résultat fiable et précis
- ✅ Temps d'exécution raisonnable (67ms)

**RANSAC est maintenant la méthode par défaut et fortement recommandée pour toutes les données réelles !**

---

## 📚 Références

1. **RANSAC** : Fischler & Bolles (1981), "Random Sample Consensus"
2. **Moindres carrés robustes** : Huber (1981), "Robust Statistics"
3. **Optimisation multi-échelle** : Bruhn et al. (2005), "Lucas/Kanade Meets Horn/Schunck"

---

## 🎯 Prochaines étapes possibles

1. **RANSAC adaptatif** : ajuster automatiquement le threshold en fonction de la distribution des résidus
2. **M-estimators** : utiliser des fonctions de perte robustes (Huber, Tukey)
3. **LO-RANSAC** : optimisation locale sur les inliers pour améliorer encore la précision
4. **PROSAC** : ordonne les observations par fiabilité estimée pour converger plus vite

---

✨ **Le programme est maintenant prêt pour des données réelles avec des erreurs de mesure !**
