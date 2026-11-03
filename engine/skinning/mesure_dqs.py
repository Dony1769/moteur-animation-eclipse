"""Compare la déformation linéaire (LBS) et la déformation par quaternions duaux (DQS, « Preserve Volume »
du modificateur Armature de Blender) sur le maillage de base, replis mesurés sur le maillage ÉVALUÉ.

Replis : même règle que mesure_lbs (normale skinnée opposée à la normale de repos tournée par l'os dominant).
Usage : blender -b corps.blend -P engine/skinning/mesure_dqs.py -- SORTIE.json
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import mesure_lbs as ml
import pose_chaine as pc
from mathutils import Vector

def replis_evalues(corps, arm):
    """Replis sur le maillage évalué (Multires désactivé => même topologie que la base)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = corps.evaluated_get(dg)
    m = ev.to_mesh()
    pose = [corps.matrix_world @ v.co for v in m.vertices]
    # référence de repos = forme de repos AVEC les clés actives (sinon une clé paraît être un pli)
    kb = corps.data.shape_keys.key_blocks
    base = kb["Basis"].data
    rest = []
    for i, v in enumerate(corps.data.vertices):
        p_ = v.co.copy()
        for k in kb:
            if k.name != "Basis" and k.value != 0.0:
                p_ += (k.data[i].co - base[i].co) * k.value
        rest.append(corps.matrix_world @ p_)
    _, _, dom = ml.positions_lbs(corps, arm, ml.matrices(arm))  # os dominant par sommet (poids réels)
    mats = ml.matrices(arm)
    n = 0
    from collections import defaultdict
    for p in corps.data.polygons:
        boucle = list(p.vertices)
        nr = ml.normale_newell(rest, boucle); npz = ml.normale_newell(pose, boucle)
        votes = defaultdict(int)
        for i in boucle:
            if dom[i]:
                votes[dom[i]] += 1
        if not votes or nr.length == 0 or npz.length == 0:
            continue
        R = mats[max(votes, key=votes.get)].to_3x3().normalized()
        if npz.dot(R @ nr) < 0:
            n += 1
    ev.to_mesh_clear()
    return n

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/corps_pose2.blend")
corps = bpy.data.objects["GEO-body_male_realistic"]; arm = bpy.data.objects["Squelette_HBM"]
corps.modifiers["Multires"].show_viewport = False
armature_mod = [m for m in corps.modifiers if m.type == "ARMATURE"][0]
kb = corps.data.shape_keys.key_blocks
for k in kb:
    k.value = 0.0

SCEN = [("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:LeftForeArm", (0, 1, 0)), ("mixamorig:LeftLeg", (1, 0, 0))]
res = {}
for mode in ("LBS", "DQS"):
    armature_mod.use_deform_preserve_volume = (mode == "DQS")
    bpy.context.view_layer.update()
    res[mode] = {}
    for nom, axe in SCEN:
        par = {}
        for a in (60, 90, 120):
            sauve = pc.poser_chaine(arm, [(nom, axe, a)])
            par[a] = replis_evalues(corps, arm)
            pc.restaurer(arm, sauve)
        res[mode][nom.replace("mixamorig:", "")] = par
json.dump(res, open(argv[0], "w"), indent=2)
print("RES", json.dumps(res))
