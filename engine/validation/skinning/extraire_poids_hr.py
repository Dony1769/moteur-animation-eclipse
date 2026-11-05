"""Poids du maillage haute résolution (MULTIRES niveau 3) par transfert barycentrique de Blender (phase 4, axe 5).

Remplace le transfert « plus proche sommet » (entrée 148). Méthode : Data Transfer de Blender, poids de groupes,
interpolation sur la face la plus proche (POLYINTERP_NEAREST), appliquée au maillage MULTIRES appliqué.

Vérification incluse : les sommets du maillage appliqué doivent coïncider avec ceux de l'évaluation MULTIRES
(sinon le transfert ne serait pas à la même topologie).

Sortie npz : hr_rest_applique (N,3) ; hr_pesos (N,J) poids par os (ordre noms_os) ; hr_ecart_topologie_m (scalaire).
Usage : blender -b --factory-startup --disable-autoexec corps_skin.blend -P engine/validation/skinning/extraire_poids_hr.py -- corps_skin.blend SORTIE.npz
"""
import bpy
import sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
entree, sortie = argv[0], argv[1]
OBJ = "GEO-body_male_realistic"

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
src = bpy.data.objects[OBJ]
noms_os = [b.name for b in arm.data.bones]
scene = bpy.context.scene


def lire_co(mesh):
    n = len(mesh.vertices)
    co = np.empty(n * 3)
    mesh.vertices.foreach_get("co", co)
    return co.reshape(n, 3)


# évaluation MULTIRES au repos (référence de topologie)
src_ev = src.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
ref_co = lire_co(src_ev)

# source de poids : maillage de base sans MULTIRES
base = src.copy()
base.data = src.data.copy()
base.name = "POIDS_base"
scene.collection.objects.link(base)
for mo in list(base.modifiers):
    if mo.type in ("MULTIRES", "ARMATURE"):
        base.modifiers.remove(mo)

# cible : maillage de base avec MULTIRES appliqué (haute résolution), sans armature
hr = src.copy()
hr.data = src.data.copy()
hr.name = "POIDS_hr"
scene.collection.objects.link(hr)
for mo in list(hr.modifiers):
    if mo.type != "MULTIRES":
        hr.modifiers.remove(mo)
mr = hr.modifiers[0]
# niveau de subdivision de la référence d'évaluation (entrée 148 : appliquer au niveau de base donnerait 10 582 sommets)
niveau = int(mr.total_levels)
mr.levels = niveau
mr.render_levels = niveau
bpy.ops.object.select_all(action="DESELECT")
hr.select_set(True)
bpy.context.view_layer.objects.active = hr
bpy.ops.object.modifier_apply(modifier=mr.name)
app_co = lire_co(hr.data)
ecart_topologie = float(np.abs(app_co - ref_co).max()) if len(app_co) == len(ref_co) else float("inf")
print("TOPOLOGIE sommets appliqués", len(app_co), "évaluation", len(ref_co), "écart max", ecart_topologie)

# transfert barycentrique des poids de groupes
# Data Transfer (modificateur) : poids de groupes, interpolation sur la face la plus proche (barycentrique)
dt = hr.modifiers.new("TRANSFERT_POIDS", "DATA_TRANSFER")
dt.object = base
dt.use_vert_data = True
dt.data_types_verts = {"VGROUP_WEIGHTS"}
dt.vert_mapping = "POLYINTERP_NEAREST"
dt.layers_vgroup_select_src = "ALL"
dt.layers_vgroup_select_dst = "NAME"
bpy.ops.object.select_all(action="DESELECT")
hr.select_set(True)
bpy.context.view_layer.objects.active = hr
bpy.ops.object.modifier_apply(modifier=dt.name)
bpy.context.view_layer.update()

# poids dense par os
N = len(hr.data.vertices)
J = len(noms_os)
pesos = np.zeros((N, J), dtype=np.float32)
groupes = {g.index: g.name for g in hr.vertex_groups}
for v in hr.data.vertices:
    for g in v.groups:
        nom = groupes.get(g.group)
        if nom in noms_os and g.weight > 0:
            pesos[v.index, noms_os.index(nom)] = g.weight

np.savez_compressed(sortie, hr_rest_applique=app_co.astype(np.float32), hr_pesos=pesos,
                    hr_ecart_topologie_m=np.array(ecart_topologie), noms_os=np.array(noms_os))
print("POIDS_HR_OK", sortie, "sommets", N, "somme des poids moyenne", float(pesos.sum(1).mean()))
