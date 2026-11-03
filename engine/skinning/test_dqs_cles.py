"""Test DQS (Preserve Volume) + clés correctives, replis sur le maillage évalué. Référence de repos = forme avec clés.
Fichiers d entrée : scratchpad/corps_pose2.blend (produit par construit_seconde_pose.py). Résultats : docs/rapports/hbm_dqs_cles.json"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import pose_chaine as pc
import mesure_lbs as ml
from collections import defaultdict


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
    _, _, dom = ml.positions_lbs(corps, arm, ml.matrices(arm))
    mats = ml.matrices(arm)
    n = 0
    for p in corps.data.polygons:
        boucle = list(p.vertices)
        nr = ml.normale_newell(rest, boucle)
        npz = ml.normale_newell(pose, boucle)
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
corps = bpy.data.objects["GEO-body_male_realistic"]
arm = bpy.data.objects["Squelette_HBM"]
corps.modifiers["Multires"].show_viewport = False
am = [m for m in corps.modifiers if m.type == "ARMATURE"][0]
kb = corps.data.shape_keys.key_blocks

out = {}
for mode in ("LBS", "DQS"):
    am.use_deform_preserve_volume = (mode == "DQS")
    out[mode] = {}
    for nom, axe in [("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:LeftForeArm", (0, 1, 0)), ("mixamorig:LeftLeg", (1, 0, 0))]:
        cle1 = "corr_" + nom.replace("mixamorig:", "")
        cle2 = "c120_" + nom.replace("mixamorig:", "")
        par = {}
        for a in (60, 90, 105, 120):
            v1 = min(a / 90, 1.0)
            v2 = max(0.0, min((a - 90) / 30, 1.0))
            kb[cle1].value = v1
            kb[cle2].value = v2
            bpy.context.view_layer.update()
            sauve = pc.poser_chaine(arm, [(nom, axe, a)])
            par[a] = replis_evalues(corps, arm)
            pc.restaurer(arm, sauve)
        for k in kb:
            k.value = 0.0
        out[mode][nom.replace("mixamorig:", "")] = par
json.dump(out, open(argv[0], "w"), indent=2)
print("RES", json.dumps(out))
