"""Banc de test reproductible de la hanche (phase 4, mission anime) : flexion de la cuisse sur le corps HBM skinné.

Méthode de référence (LBS, poids du fichier) : pour chaque angle de flexion, on pose la cuisse gauche, on évalue le
maillage de BASE (sans MULTIRES : la référence de skinning du moteur), puis on mesure en MÈTRES MONDE :
  - étirement des arêtes : rapport longueur posée / longueur de repos (max, p99, part > 1,15 et < 0,85) ;
  - triangles retournés : normale posée opposée à la normale de repos ;
  - variation de volume signé relative au repos ;
  - déplacement maximal d'un sommet (contrôle de cohérence).
Aucun seuil n'est modifié pour faire passer un test : les mesures sont écrites telles quelles.

Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_hanche_banc.py -- BUNDLE_OU_SKIN.blend SORTIE.json
"""
import bpy
import json
import math
import sys
from mathutils import Euler

argv = sys.argv[sys.argv.index("--") + 1:]
entree, sortie = argv[0], argv[1]
OBJET = "GEO-body_male_realistic"
OS = "mixamorig:LeftUpLeg"
ANGLES = [0, 30, 60, 90, 120]

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
src = bpy.data.objects[OBJET]

# copie de base sans MULTIRES (référence du moteur : maillage de base)
copie = src.copy()
copie.data = src.data.copy()
copie.name = "BANC_base"
bpy.context.scene.collection.objects.link(copie)
for mo in list(copie.modifiers):
    if mo.type == "MULTIRES":
        copie.modifiers.remove(mo)
for mo in copie.modifiers:
    if mo.type == "ARMATURE":
        mo.object = arm

pb = arm.pose.bones[OS]
pb.rotation_mode = "XYZ"
dg = bpy.context.evaluated_depsgraph_get


def positions():
    ev = copie.evaluated_get(dg()).data
    return [copie.matrix_world @ v.co for v in ev.vertices], ev


def normales(verts, faces):
    out = []
    for f in faces:
        a, b, c = verts[f[0]], verts[f[1]], verts[f[2]]
        n = (b - a).cross(c - a)
        out.append(n.normalized() if n.length > 1e-12 else None)
    return out


def volume(verts, faces):
    v = 0.0
    for f in faces:
        a, b, c = verts[f[0]], verts[f[1]], verts[f[2]]
        v += a.dot(b.cross(c)) / 6.0
    return v


# repos
pb.rotation_euler = Euler((0, 0, 0), "XYZ")
bpy.context.view_layer.update()
rest_verts, ev_rest = positions()
# Tous les polygones sont pris en compte : triangulation en éventail des quads et n-gones.
# (Erreur corrigée : un filtre « 3 sommets » ne gardait que 20 triangles sur 10 590 polygones.)
faces = []
for p in ev_rest.polygons:
    v = list(p.vertices)
    for k in range(1, len(v) - 1):
        faces.append((v[0], v[k], v[k + 1]))
nb_polygones = len(ev_rest.polygons)  # lu tant que le maillage évalué est valide (il est libéré ensuite)
aretes = sorted({tuple(sorted((p.vertices[i], p.vertices[(i + 1) % len(p.vertices)])))
                 for p in ev_rest.polygons for i in range(len(p.vertices))})
long_rest = {a: (rest_verts[a[0]] - rest_verts[a[1]]).length for a in aretes}
normales_rest = normales(rest_verts, faces)
vol_rest = volume(rest_verts, faces)

# sens de la flexion : le genou doit avancer (-Y, le personnage regarde -Y)
genou = arm.pose.bones["mixamorig:LeftLeg"]
resultats = []


def y_genou_monde():
    bpy.context.view_layer.update()
    return (arm.matrix_world @ genou.matrix @ genou.bone.head).y


# sens : celui qui fait avancer le genou vers -Y (le personnage regarde -Y)
pb.rotation_euler = Euler((0, 0, 0), "XYZ")
y_repos = y_genou_monde()
sens = None
for s in (1.0, -1.0):
    pb.rotation_euler = Euler((math.radians(60) * s, 0, 0), "XYZ")
    if y_genou_monde() < y_repos - 1e-3:
        sens = s
        break
if sens is None:
    raise SystemExit("BANC_ECHEC : aucun sens de flexion n'avance le genou vers -Y")
pb.rotation_euler = Euler((0, 0, 0), "XYZ")
for ang in ANGLES:
    if ang == 0:
        pb.rotation_euler = Euler((0, 0, 0), "XYZ")
        bpy.context.view_layer.update()
        pos, _ = positions()
        ligne = {"angle": 0}
    else:
        pb.rotation_euler = Euler((math.radians(ang) * sens, 0, 0), "XYZ")
        bpy.context.view_layer.update()
        pos, _ = positions()
        ligne = {"angle": ang}
    # étirement des arêtes
    ratios = []
    for a in aretes:
        l0 = long_rest[a]
        if l0 > 1e-9:
            ratios.append((pos[a[0]] - pos[a[1]]).length / l0)
    ratios.sort()
    n = len(ratios)
    ligne["etirement_max"] = round(ratios[-1], 4)
    ligne["etirement_p99"] = round(ratios[int(0.99 * n)], 4)
    ligne["part_etire_gt_1_15"] = round(sum(1 for r in ratios if r > 1.15) / n, 5)
    ligne["part_comprime_lt_0_85"] = round(sum(1 for r in ratios if r < 0.85) / n, 5)
    # triangles retournés
    nouv = normales(pos, faces)
    flips = 0
    for a, b in zip(nouv, normales_rest):
        if a is not None and b is not None and a.dot(b) < 0:
            flips += 1
    ligne["triangles_retournes"] = flips
    ligne["variation_volume_relative"] = round((volume(pos, faces) - vol_rest) / abs(vol_rest), 5)
    ligne["deplacement_max_m"] = round(max((p - r).length for p, r in zip(pos, rest_verts)), 4)
    resultats.append(ligne)

# remise au repos et nettoyage
pb.rotation_euler = Euler((0, 0, 0), "XYZ")
bpy.data.objects.remove(copie, do_unlink=True)

rapport = {
    "entree": entree,
    "objet": OBJET,
    "os": OS,
    "sens_flexion": sens,
    "sommets_base": len(rest_verts),
    "aretes": len(aretes),
    "triangles": len(faces),
    "polygones": nb_polygones,
    "methode": "LBS, maillage de base, mètres monde",
    "mesures": resultats,
}
with open(sortie, "w") as f:
    json.dump(rapport, f, indent=2, ensure_ascii=False)
for l in resultats:
    print("BANC", l)
print("BANC_OK", sortie)
