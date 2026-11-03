"""Forme corrective pilotée par l'angle (pose-space correction) pour un pli repliant le maillage.

Principe (documentation : Pose Space Deformation ; LBS « elbow collapse » ; « add a small driven corrective »):
1. à l'angle cible, on repère les sommets appartenant à des faces repliées (mesure_lbs) ;
2. on décale ces sommets, dans l'espace de repos, le long de leur normale de repos, par petits pas,
   jusqu'à ce que le pli disparaisse ou qu'un plafond d'amplitude soit atteint ;
3. le décalage est stocké dans une clé de forme ; sa valeur suit l'angle : valeur = clamp(angle / angle_cible).
   Au repos (angle 0) la valeur vaut 0 : l'apparence de repos n'est pas modifiée (testé).

Limite : le décalage est calculé pour une articulation et un angle ; plusieurs formes se combinent additivement.
"""
import math
import bpy
from mathutils import Matrix, Vector
import mesure_lbs as ml

def normales_sommets(corps):
    """Normale de repos moyenne par sommet (moyenne des faces adjacentes, espace local)."""
    acc = [Vector((0.0, 0.0, 0.0)) for _ in corps.data.vertices]
    coords = [v.co for v in corps.data.vertices]
    for p in corps.data.polygons:
        n = ml.normale_newell(coords, list(p.vertices))
        for i in p.vertices:
            acc[i] += n
    return [a.normalized() if a.length > 0 else a for a in acc]

def poser_temporairement(arm, nom, axe, ang):
    pb = arm.pose.bones[nom]
    t = arm.matrix_world @ pb.bone.head_local
    repos = pb.matrix.copy()
    pb.matrix = (Matrix.Translation(t) @ Matrix.Rotation(math.radians(ang), 4, Vector(axe)) @ Matrix.Translation(-t)) @ repos
    # Indispensable : sans mise à jour, pb.matrix relu ensuite peut rester à la pose de repos.
    bpy.context.view_layer.update()
    return repos

def point_sur_segment(p, a, b):
    """Point le plus proche de p sur le segment [a, b] (espace local de l'os)."""
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.dot(ab))) if ab.length > 0 else 0.0
    return a + ab * t

def direction_correction(mode, normale, p, arm, nom, corps):
    if mode == "normale":
        return normale
    if mode == "moins_normale":
        return -normale
    if mode == "vers_os":
        b = arm.data.bones[nom]
        inv = corps.matrix_world.inverted()
        a = inv @ (arm.matrix_world @ b.head_local); c = inv @ (arm.matrix_world @ b.tail_local)
        return point_sur_segment(p, a, c) - p
    raise ValueError(mode)

def voisins_sommets(corps):
    """Voisins directs de chaque sommet (graphe des arêtes du maillage de base)."""
    voisins = [set() for _ in corps.data.vertices]
    for e in corps.data.edges:
        a, b = e.vertices
        voisins[a].add(b); voisins[b].add(a)
    return [sorted(v) for v in voisins]

def lisser_decalage(decal, voisins, passes, amplitude_max):
    """Lissage laplacien du champ de décalage : évite une frontière brutale entre sommets déplacés
    et sommets immobiles (cause des arêtes étirées constatées par controle_gonflement.py).
    Chaque passe : d_i <- 0,5 d_i + 0,5 moyenne(d_voisins), puis plafond d'amplitude."""
    for _ in range(passes):
        nouveau = []
        for i, d in enumerate(decal):
            vs = voisins[i]
            if vs:
                moy = Vector((0.0, 0.0, 0.0))
                for j in vs:
                    moy += decal[j]
                d = d * 0.5 + (moy / len(vs)) * 0.5
            if d.length > amplitude_max:
                d = d.normalized() * amplitude_max
            nouveau.append(d)
        decal[:] = nouveau
    return decal

def calculer_decalage(corps, arm, nom, axe, angle, pas=0.001, iterations=60, amplitude_max=0.02, mode="normale", initial=None, lissage=0):
    """Décalages locaux qui suppriment les replis de l'os `nom` à l'angle `angle`.
    Renvoie (liste de décalages, historique du nombre de faces repliées par itération)."""
    normales = normales_sommets(corps)
    decal = [Vector(d) for d in initial] if initial is not None else [Vector((0.0, 0.0, 0.0)) for _ in corps.data.vertices]
    repos = poser_temporairement(arm, nom, axe, angle)
    historique = []
    voisins = voisins_sommets(corps) if lissage > 0 else None
    try:
        for _ in range(iterations):
            n, _, boucle = ml.faces_repliees(corps, arm, ml.matrices(arm), decalage=decal, detail=True)
            historique.append(n)
            if n == 0:
                break
            for i in boucle:
                dirn = direction_correction(mode, normales[i], Vector(corps.data.vertices[i].co), arm, nom, corps)
                if dirn.length > 0:
                    dirn = dirn.normalized()
                d = decal[i] + dirn * pas
                if d.length > amplitude_max:
                    d = d.normalized() * amplitude_max
                decal[i] = d
            if lissage > 0:
                lisser_decalage(decal, voisins, lissage, amplitude_max)
    finally:
        arm.pose.bones[nom].matrix = repos
        bpy.context.view_layer.update()
    return decal, historique

# -- Clés de forme correctives --------------------------------------------

def ajouter_cles_correctives(corps, arm, specs, angle=90, iterations=80, amplitude_max=0.04, lissage=0):
    """Crée une clé de forme par articulation : `specs` = [(os, axe monde)].
    Chaque clé porte le décalage calculé à l'angle `angle` ; sa valeur doit valoir clamp(angle_pose / angle, 0, 1).
    Renvoie un rapport par clé (replis avant/après à l'angle de calibration)."""
    if corps.data.shape_keys is None:
        corps.shape_key_add(name="Basis", from_mix=False)
    rapport = []
    for nom, axe in specs:
        decal, hist = calculer_decalage(corps, arm, nom, axe, angle, iterations=iterations,
                                        amplitude_max=amplitude_max, mode="moins_normale", lissage=lissage)
        cle = corps.shape_key_add(name="corr_" + nom.replace("mixamorig:", ""), from_mix=False)
        cle.slider_min = 0.0; cle.slider_max = 1.0; cle.value = 0.0
        for i, d in enumerate(decal):
            cle.data[i].co = corps.data.vertices[i].co + d
        rapport.append({"cle": cle.name, "os": nom, "angle": angle, "replis_avant": hist[0],
                        "replis_apres": hist[-1], "iterations": len(hist),
                        "amplitude_max_mm": round(max(d.length for d in decal) * 1000, 2)})
    return rapport

def appliquer_valeur(corps, cle_nom, valeur):
    corps.data.shape_keys.key_blocks[cle_nom].value = max(0.0, min(1.0, valeur))


def ajouter_cle_seconde_pose(corps, arm, nom, axe, cle_premiere, angle_1=90, angle_2=120,
                             iterations=80, amplitude_max=0.04, lissage=0):
    """Deuxième échantillon de l'espace de pose : part du décalage de la première clé (calibrée à angle_1)
    et le corrige à angle_2. La seconde clé porte la différence ; sa valeur = clamp((angle - angle_1)/(angle_2 - angle_1)).
    Ainsi, à angle_1 la somme vaut la première clé, et à angle_2 la somme vaut la correction à angle_2.
    Interpolation linéaire entre les deux échantillons (pose space à une dimension)."""
    kb = corps.data.shape_keys.key_blocks
    base = kb["Basis"].data
    d1 = [(kb[cle_premiere].data[i].co - base[i].co) for i in range(len(base))]
    decal2, hist = calculer_decalage(corps, arm, nom, axe, angle_2, iterations=iterations,
                                     amplitude_max=amplitude_max, mode="moins_normale", initial=d1, lissage=lissage)
    diff = [decal2[i] - d1[i] for i in range(len(base))]
    cle = corps.shape_key_add(name="c" + str(angle_2) + "_" + nom.replace("mixamorig:", ""), from_mix=False)
    cle.slider_min = 0.0; cle.slider_max = 1.0; cle.value = 0.0
    for i in range(len(base)):
        cle.data[i].co = base[i].co + diff[i]
    return {"cle": cle.name, "os": nom, "angle_1": angle_1, "angle_2": angle_2,
            "replis_avant": hist[0], "replis_apres": hist[-1], "iterations": len(hist),
            "amplitude_diff_max_mm": round(max(d.length for d in diff) * 1000, 2)}
