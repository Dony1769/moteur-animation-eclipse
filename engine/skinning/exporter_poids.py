"""Exporte la géométrie, les poids et les matrices de pose du corps HBM pour une optimisation numpy (CPU).

Sortie (npz) : rest (N,3) en repère armature ; aretes (E,2) ; W (N,B) poids ; os (B) noms ;
M (A,B,4,4) matrices LBS (pose · repos⁻¹, repère armature) pour chaque angle de ANGLES, bras gauche.
Les clés correctives et le Multires sont désactivés : seul le LBS standard est exporté.
Usage : blender -b --factory-startup --disable-autoexec -P engine/skinning/exporter_poids.py -- BLEND SORTIE.npz
"""
import bpy, sys, numpy as np
from mathutils import Matrix
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import auto_skin as ak
import pose_chaine as pc

argv = sys.argv[sys.argv.index("--") + 1:]
blend, sortie = argv[0], argv[1]
ANGLES = (0, 60, 90, 105, 120)
bpy.ops.wm.open_mainfile(filepath=blend)
corps = bpy.data.objects[ak.ENTREE_NOM]
arm = [m.object for m in corps.modifiers if m.type == "ARMATURE"][0]
corps.modifiers["Multires"].show_viewport = False
if corps.data.shape_keys:
    for k in corps.data.shape_keys.key_blocks: k.value = 0.0
bpy.context.view_layer.update()

# repère armature : toutes les coordonnées sont exprimées dans l'espace de l'armature
inv_arm = arm.matrix_world.inverted()
rest = np.array([(inv_arm @ corps.matrix_world @ v.co)[:] for v in corps.data.vertices], dtype=np.float64)
aretes = np.array([tuple(e.vertices) for e in corps.data.edges], dtype=np.int64)
os_noms = [b.name for b in arm.data.bones]
idx = {n: i for i, n in enumerate(os_noms)}
W = np.zeros((len(rest), len(os_noms)))
for v in corps.data.vertices:
    for g in v.groups:
        nom = corps.vertex_groups[g.group].name
        if nom in idx: W[v.index, idx[nom]] = g.weight
rep_inv = [np.array(arm.data.bones[n].matrix_local.inverted()) for n in os_noms]  # repos : espace os -> armature

# chaînes testées : bras, avant-bras (flexion du coude), jambe (flexion du genou) ; M aplati : index = c*len(ANGLES)+a
CHAINES = [("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:LeftForeArm", (0, 1, 0)), ("mixamorig:LeftLeg", (1, 0, 0))]
M = np.zeros((len(CHAINES) * len(ANGLES), len(os_noms), 4, 4))
etiquettes = []
for ic, (os_pivot, axe) in enumerate(CHAINES):
    for ia, a in enumerate(ANGLES):
        sauve = pc.poser_chaine(arm, [(os_pivot, axe, a)]) if a else None
        bpy.context.view_layer.update()
        for ib, n in enumerate(os_noms):
            M[ic * len(ANGLES) + ia, ib] = np.array(arm.pose.bones[n].matrix) @ rep_inv[ib]
        if a: pc.restaurer(arm, sauve)
        bpy.context.view_layer.update()
        etiquettes.append(f"{os_pivot.replace('mixamorig:', '')}@{a}")

np.savez(sortie, rest=rest, aretes=aretes, W=W, os=np.array(os_noms), M=M, angles=np.array(ANGLES),
         etiquettes=np.array(etiquettes))
print("EXPORT_OK", rest.shape, aretes.shape, W.shape, M.shape)
