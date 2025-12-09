"""
Module de visualisation avec OpenStreetMap et Folium
Crée une carte interactive montrant la table d'orientation, les curiosités, et les droites
"""

import folium
from folium import plugins
import math
from typing import List, Dict, Tuple, Optional
from table import estimate_origin_and_phi, line_dir_from_angle_deg, normalize_deg


def meters_to_degrees(meters: float, latitude: float = 45.0) -> float:
    """
    Convertit des mètres en degrés de latitude/longitude.
    Approximation pour petites distances.
    """
    # 1 degré de latitude ≈ 111 km
    # 1 degré de longitude ≈ 111 km × cos(latitude)
    return meters / (111000.0 * math.cos(math.radians(latitude)))


def project_point(origin: Tuple[float, float], direction: Tuple[float, float], distance: float) -> Tuple[float, float]:
    """
    Projette un point depuis l'origine dans une direction donnée.
    """
    dx, dy = direction
    return (origin[0] + dx * distance, origin[1] + dy * distance)


def create_interactive_map(observations: List[Dict], 
                          origin: Optional[Tuple[float, float]] = None,
                          phi: Optional[float] = None,
                          residual: Optional[float] = None,
                          inliers_mask: Optional[List[bool]] = None,
                          use_latlon: bool = False,
                          center_lat: float = 45.0,
                          center_lon: float = 6.0,
                          output_file: str = "table_orientation_map.html") -> str:
    """
    Crée une carte interactive avec OpenStreetMap montrant :
    - La table d'orientation (marqueur bleu)
    - Les curiosités observées (marqueurs rouges)
    - Les droites de visée (lignes vertes)
    - Les rétro-azimuts (lignes oranges)
    
    Args:
        observations: Liste des observations avec 'x', 'y', 'azimuth_deg', optionnel 'name'
        origin: Position estimée de la table (x, y). Si None, sera calculée.
        phi: Orientation estimée. Si None, sera calculée.
        use_latlon: Si True, x et y sont des coordonnées lat/lon. Sinon, mètres projetés.
        center_lat: Latitude du centre (pour conversion mètres→degrés si use_latlon=False)
        center_lon: Longitude du centre (pour conversion mètres→degrés si use_latlon=False)
        output_file: Nom du fichier HTML de sortie
    
    Returns:
        Chemin du fichier HTML créé
    """
    
    # Calculer l'origine et phi si non fournis
    if origin is None or phi is None:
        print("🔍 Calcul de la position de la table avec RANSAC...")
        origin_calc, phi_calc, resid, inlier_indices = estimate_origin_and_phi(observations, method='ransac', return_inliers=True)
        if origin is None:
            origin = origin_calc
        if phi is None:
            phi = phi_calc
        if residual is None:
            residual = resid
        if inliers_mask is None:
            # Créer un masque booléen
            inliers_mask = [i in inlier_indices for i in range(len(observations))]
        print(f"✅ Origine: ({origin[0]:.2f}, {origin[1]:.2f})")
        print(f"✅ Orientation φ: {phi:.4f}°")
        print(f"✅ Résiduel: {resid:.3f} m\n")
    
    # Si pas de masque fourni, tous sont des inliers
    if inliers_mask is None:
        inliers_mask = [True] * len(observations)
    
    # Conversion des coordonnées si nécessaire
    if not use_latlon:
        # Convertir TOUTES les coordonnées métriques en lat/lon relatives
        # On suppose que center_lat, center_lon est le centre approximatif
        obs_latlon = []
        for i, obs in enumerate(observations):
            lat = center_lat + meters_to_degrees(obs['y'], center_lat)
            lon = center_lon + meters_to_degrees(obs['x'], center_lat)
            obs_latlon.append({
                'lat': lat,
                'lon': lon,
                'azimuth_deg': obs['azimuth_deg'],
                'name': obs.get('name', f"Point {i+1}"),
                'original_x': obs['x'],
                'original_y': obs['y']
            })
        
        origin_lat = center_lat + meters_to_degrees(origin[1], center_lat)
        origin_lon = center_lon + meters_to_degrees(origin[0], center_lat)
    else:
        # Coordonnées déjà en lat/lon
        obs_latlon = []
        for i, obs in enumerate(observations):
            obs_latlon.append({
                'lat': obs['y'],
                'lon': obs['x'],
                'azimuth_deg': obs['azimuth_deg'],
                'name': obs.get('name', f"Point {i+1}")
            })
        origin_lat = origin[1]
        origin_lon = origin[0]
    
    # Calculer le centre de la carte et les limites
    all_lats = [obs['lat'] for obs in obs_latlon] + [origin_lat]
    all_lons = [obs['lon'] for obs in obs_latlon] + [origin_lon]
    map_center_lat = sum(all_lats) / len(all_lats)
    map_center_lon = sum(all_lons) / len(all_lons)
    
    # Créer la carte
    print("🗺️  Création de la carte interactive...")
    m = folium.Map(
        location=[map_center_lat, map_center_lon],
        zoom_start=14,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Ajuster automatiquement le zoom pour voir tous les points
    bounds = [[min(all_lats), min(all_lons)], [max(all_lats), max(all_lons)]]
    m.fit_bounds(bounds, padding=(50, 50))
    
    # Ajouter des tuiles alternatives
    folium.TileLayer(
        tiles='https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.png',
        attr='Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL.',
        name='Terrain'
    ).add_to(m)
    
    folium.TileLayer(
        tiles='CartoDB positron',
        name='CartoDB Light'
    ).add_to(m)
    
    # Compter les inliers et outliers
    n_inliers = sum(inliers_mask)
    n_outliers = len(observations) - n_inliers
    
    # Ajouter la table d'orientation (marqueur bleu)
    table_popup_html = f"""
    <div style="font-family: Arial, sans-serif; min-width: 250px;">
        <h4 style="margin: 0 0 10px 0; color: #0066cc;">📍 Table d'Orientation</h4>
        <table style="width: 100%; font-size: 12px;">
            <tr><td><b>Latitude:</b></td><td>{origin_lat:.6f}°</td></tr>
            <tr><td><b>Longitude:</b></td><td>{origin_lon:.6f}°</td></tr>
            <tr><td><b>Orientation φ:</b></td><td>{phi:.2f}°</td></tr>
            <tr><td><b>Résiduel:</b></td><td>{residual:.3f} m</td></tr>
            <tr><td><b>Points valides:</b></td><td>{n_inliers}/{len(observations)}</td></tr>
            {f'<tr><td><b>Outliers éliminés:</b></td><td style="color: red;">{n_outliers}</td></tr>' if n_outliers > 0 else ''}
        </table>
        <p style="font-size: 10px; margin-top: 10px; color: #666;">
            <i>✓ Position estimée par RANSAC</i>
        </p>
    </div>
    """
    folium.Marker(
        location=[origin_lat, origin_lon],
        popup=folium.Popup(table_popup_html, max_width=300),
        tooltip="📍 Table d'orientation (clique pour détails)",
        icon=folium.Icon(color='blue', icon='compass', prefix='fa')
    ).add_to(m)
    
    # Ajouter un cercle autour de la table
    folium.Circle(
        location=[origin_lat, origin_lon],
        radius=20,  # 20 mètres
        color='blue',
        fill=True,
        fillOpacity=0.2,
        popup="Zone de la table"
    ).add_to(m)
    
    # Palette de couleurs pour les curiosités
    colors = ['red', 'darkred', 'orange', 'purple', 'darkpurple', 'pink', 'cadetblue', 'darkgreen']
    
    # Pour chaque observation
    for i, obs in enumerate(obs_latlon):
        is_inlier = inliers_mask[i] if inliers_mask else True
        color = colors[i % len(colors)] if is_inlier else 'gray'
        
        # Distance calculée de la table à la curiosité
        if not use_latlon and 'original_x' in obs and 'original_y' in obs:
            dist = math.sqrt((obs['original_x'] - origin[0])**2 + (obs['original_y'] - origin[1])**2)
        else:
            # Approximation Haversine simplifiée
            dist = math.sqrt((obs['lon'] - origin_lon)**2 + (obs['lat'] - origin_lat)**2) * 111000
        
        # Marqueur de la curiosité
        curiosity_popup_html = f"""
        <div style="font-family: Arial, sans-serif; min-width: 250px;">
            <h4 style="margin: 0 0 10px 0; color: {'#666' if not is_inlier else '#cc0000'};">🏔️ {obs['name']}</h4>
            <table style="width: 100%; font-size: 12px;">
                <tr><td><b>Point #:</b></td><td>{i+1}</td></tr>
                <tr><td><b>Latitude:</b></td><td>{obs['lat']:.6f}°</td></tr>
                <tr><td><b>Longitude:</b></td><td>{obs['lon']:.6f}°</td></tr>
                <tr><td><b>Azimut gravé:</b></td><td>{obs['azimuth_deg']:.1f}°</td></tr>
                <tr><td><b>Azimut corrigé:</b></td><td>{normalize_deg(obs['azimuth_deg'] + phi):.1f}°</td></tr>
                <tr><td><b>Distance table:</b></td><td>{dist:.0f} m</td></tr>
                <tr><td><b>Statut:</b></td><td style="color: {'green' if is_inlier else 'red'};">
                    {'✓ Inlier (valide)' if is_inlier else '✗ Outlier (éliminé)'}
                </td></tr>
            </table>
        </div>
        """
        
        # Créer un marqueur numéroté personnalisé
        icon_html = f"""
        <div style="font-size: 14px; font-weight: bold; 
                    color: white; background-color: {color if is_inlier else '#999'}; 
                    border-radius: 50%; width: 30px; height: 30px; 
                    display: flex; align-items: center; justify-content: center;
                    border: 3px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);">
            {i+1}
        </div>
        """
        
        folium.Marker(
            location=[obs['lat'], obs['lon']],
            popup=folium.Popup(curiosity_popup_html, max_width=300),
            tooltip=f"#{i+1} {obs['name']} {'✓' if is_inlier else '✗'}",
            icon=folium.DivIcon(html=icon_html)
        ).add_to(m)
        
        # Ligne de visée depuis la table vers la curiosité (vert)
        azimuth_corrected = normalize_deg(obs['azimuth_deg'] + phi)
        direction = line_dir_from_angle_deg(azimuth_corrected)
        
        # Calculer un point loin dans cette direction
        distance_km = 5.0  # 5 km de ligne
        end_point = project_point(
            (origin_lon, origin_lat),
            (meters_to_degrees(direction[0] * distance_km * 1000, origin_lat),
             meters_to_degrees(direction[1] * distance_km * 1000, origin_lat)),
            1.0
        )
        
        # Ne dessiner les lignes que pour les inliers
        if is_inlier:
            folium.PolyLine(
                locations=[[origin_lat, origin_lon], [end_point[1], end_point[0]]],
                color='green',
                weight=2.5,
                opacity=0.7,
                popup=f"Ligne de visée vers {obs['name']} (azimut {azimuth_corrected:.1f}°)",
                tooltip=f"Visée → {obs['name']}"
            ).add_to(m)
        else:
            # Lignes en gris pour les outliers
            folium.PolyLine(
                locations=[[origin_lat, origin_lon], [end_point[1], end_point[0]]],
                color='gray',
                weight=1,
                opacity=0.3,
                dash_array='5, 5',
                popup=f"⚠️ Outlier: {obs['name']} (azimut {azimuth_corrected:.1f}°)",
                tooltip=f"✗ Outlier: {obs['name']}"
            ).add_to(m)
        
        # Rétro-azimut depuis la curiosité vers la table (orange)
        back_bearing = normalize_deg(obs['azimuth_deg'] + phi + 180.0)
        back_direction = line_dir_from_angle_deg(back_bearing)
        
        # Point loin dans la direction opposée
        back_end_point = project_point(
            (obs['lon'], obs['lat']),
            (meters_to_degrees(back_direction[0] * distance_km * 1000, obs['lat']),
             meters_to_degrees(back_direction[1] * distance_km * 1000, obs['lat'])),
            1.0
        )
        
        # Rétro-azimuts seulement pour les inliers
        if is_inlier:
            folium.PolyLine(
                locations=[[obs['lat'], obs['lon']], [back_end_point[1], back_end_point[0]]],
                color='orange',
                weight=2,
                opacity=0.6,
                dash_array='10, 5',
                popup=f"Rétro-azimut depuis {obs['name']} (azimut {back_bearing:.1f}°)",
                tooltip=f"Rétro ← {obs['name']}"
            ).add_to(m)
    
    # Créer un tableau de données interactif
    data_table_html = f"""
    <div style="position: fixed; top: 70px; right: 10px; width: 350px; 
                background-color: white; border: 2px solid #0066cc; z-index: 9999; 
                font-size: 12px; padding: 15px; border-radius: 8px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-height: 80vh; overflow-y: auto;">
        <h4 style="margin: 0 0 10px 0; color: #0066cc;">📊 Données de Triangulation</h4>
        <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <thead>
                <tr style="background-color: #f0f0f0; border-bottom: 2px solid #0066cc;">
                    <th style="padding: 5px; text-align: center;">#</th>
                    <th style="padding: 5px;">Nom</th>
                    <th style="padding: 5px; text-align: right;">Azimut</th>
                    <th style="padding: 5px; text-align: center;">Statut</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for i, obs in enumerate(obs_latlon):
        is_inlier = inliers_mask[i] if inliers_mask else True
        status_icon = '✓' if is_inlier else '✗'
        status_color = 'green' if is_inlier else 'red'
        row_color = '#fff' if is_inlier else '#f9f9f9'
        
        data_table_html += f"""
                <tr style="background-color: {row_color}; border-bottom: 1px solid #ddd;">
                    <td style="padding: 5px; text-align: center; font-weight: bold;">{i+1}</td>
                    <td style="padding: 5px;">{obs['name']}</td>
                    <td style="padding: 5px; text-align: right;">{obs['azimuth_deg']:.1f}°</td>
                    <td style="padding: 5px; text-align: center; color: {status_color}; font-weight: bold;">{status_icon}</td>
                </tr>
        """
    
    data_table_html += f"""
            </tbody>
        </table>
        <div style="margin-top: 10px; padding: 8px; background-color: #e6f2ff; border-radius: 4px;">
            <p style="margin: 3px 0; font-size: 11px;"><b>Position Table:</b> ({origin[0]:.1f}, {origin[1]:.1f})</p>
            <p style="margin: 3px 0; font-size: 11px;"><b>Orientation φ:</b> {phi:.2f}°</p>
            <p style="margin: 3px 0; font-size: 11px;"><b>Résiduel:</b> {residual:.3f} m</p>
            <p style="margin: 3px 0; font-size: 11px; color: green;"><b>Inliers:</b> {n_inliers}/{len(observations)}</p>
            {f'<p style="margin: 3px 0; font-size: 11px; color: red;"><b>Outliers éliminés:</b> {n_outliers}</p>' if n_outliers > 0 else ''}
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(data_table_html))
    
    # Ajouter une légende améliorée
    legend_html = f'''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 280px; 
                background-color: white; border: 2px solid #0066cc; z-index: 9999; 
                font-size: 13px; padding: 15px; border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h4 style="margin: 0 0 10px 0; color: #0066cc;">📋 Légende</h4>
    <p style="margin: 5px 0;"><i class="fa fa-compass" style="color:blue"></i> <b>Table d'orientation</b></p>
    <p style="margin: 5px 0;"><span style="display:inline-block; width:20px; height:20px; 
       background-color:red; border-radius:50%; text-align:center; color:white; font-size:10px; 
       line-height:20px;">1</span> <b>Curiosités</b> (numérotées)</p>
    <p style="margin: 5px 0;"><span style="color:green; font-weight:bold;">━━━</span> Ligne de visée (inlier)</p>
    <p style="margin: 5px 0;"><span style="color:orange; font-weight:bold;">╍╍╍</span> Rétro-azimut (inlier)</p>
    <p style="margin: 5px 0;"><span style="color:gray; font-weight:bold;">- - -</span> Outliers (éliminés)</p>
    <hr style="margin: 10px 0; border: none; border-top: 1px solid #ddd;">
    <p style="font-size: 11px; margin: 5px 0; color: #666;">
    <i>💡 Les rétro-azimuts des points valides se croisent à la position de la table</i>
    </p>
    <p style="font-size: 10px; margin: 5px 0; color: #999;">
    Algorithme: <b>RANSAC</b> | Résiduel: <b>{residual:.3f}m</b>
    </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Ajouter un contrôle de couches
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Ajouter la mesure de distance
    plugins.MeasureControl(
        position='topleft',
        primary_length_unit='meters',
        secondary_length_unit='kilometers',
        primary_area_unit='sqmeters'
    ).add_to(m)
    
    # Ajouter le mode plein écran
    plugins.Fullscreen(
        position='topright',
        title='Plein écran',
        title_cancel='Quitter plein écran'
    ).add_to(m)
    
    # Ajouter un mini-map
    minimap = plugins.MiniMap(toggle_display=True, position='bottomright')
    m.add_child(minimap)
    
    # Ajouter des coordonnées de souris
    plugins.MousePosition(
        position='bottomleft',
        separator=' | ',
        prefix='Coordonnées: ',
        lat_formatter="function(num) {return L.Util.formatNum(num, 6) + '° N';}",
        lng_formatter="function(num) {return L.Util.formatNum(num, 6) + '° E';}"
    ).add_to(m)
    
    # Ajouter un titre personnalisé
    title_html = f'''
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); 
                width: 600px; background-color: rgba(255,255,255,0.95); 
                border: 3px solid #0066cc; z-index: 9999; 
                padding: 15px; border-radius: 10px; text-align: center;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
        <h3 style="margin: 0; color: #0066cc;">📍 Triangulation de Table d'Orientation</h3>
        <p style="margin: 5px 0; font-size: 13px; color: #333;">
            Algorithme RANSAC | {n_inliers} points valides / {len(observations)} observations
        </p>
        <p style="margin: 5px 0; font-size: 12px; color: #666;">
            Résiduel: <b style="color: {'green' if residual < 10 else 'orange' if residual < 50 else 'red'};">{residual:.3f} m</b> 
            | Précision: <b>{'Excellente ✓' if residual < 10 else 'Bonne ⚡' if residual < 50 else 'Moyenne ⚠'}</b>
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Sauvegarder la carte
    m.save(output_file)
    print(f"✅ Carte sauvegardée dans : {output_file}")
    print(f"📂 Ouvre ce fichier dans ton navigateur pour voir la carte interactive !")
    print(f"\n{'='*60}")
    print(f"📊 Résumé de la carte:")
    print(f"   • {len(observations)} observations totales")
    print(f"   • {n_inliers} points valides (inliers)")
    print(f"   • {n_outliers} outliers éliminés")
    print(f"   • Résiduel final: {residual:.3f} m")
    print(f"{'='*60}\n")
    
    return output_file


if __name__ == "__main__":
    # Exemple d'utilisation avec données fictives
    observations = [
        {'x': 2900.0, 'y': 200.0, 'azimuth_deg': 360.0, 'name': 'Mont Nord'},
        {'x': 1601.0, 'y': 1001.0, 'azimuth_deg': 30.0, 'name': 'Pic Est'},
        {'x': 4000.0, 'y': 260.0, 'azimuth_deg': 210.0, 'name': 'Crête Ouest'},
        {'x': 400.0, 'y': 480.0, 'azimuth_deg': 200.0, 'name': 'Vallée'},
    ]
    
    print("="*60)
    print("Visualisation interactive avec OpenStreetMap")
    print("="*60 + "\n")
    
    # Créer la carte (coordonnées en mètres, converties en lat/lon)
    # Centre approximatif : Grenoble, France
    create_interactive_map(
        observations,
        use_latlon=False,
        center_lat=45.1885,  # Grenoble
        center_lon=5.7245,
        output_file="table_orientation_map.html"
    )
    
    print("="*60)
    print("Visualisation terminée !")
    print("="*60)
