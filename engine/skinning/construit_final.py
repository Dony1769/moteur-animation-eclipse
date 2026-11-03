"""Pipeline final du corps HBM : squelette + os d'aide à l'épaule + skinning + yeux rigides
+ clé corrective 90° + seconde clé 120° + mesures.

Mesures (LBS explicite, chaînes posées hiérarchiquement) pour bras, avant-bras, jambes :
- replis à 60, 90, 105, 120 degrés, avec les valeurs de clés (v1 = clamp(a/90), v2 = clamp((a-90)/30)) ;
- déplacement maximal des sommets à 120° (contrôle anti-gonflement), en millimètres ;
- repos : toutes les clés à 0 -> amplitude nulle.

Usage : blender -b corps_hbm.blend -P engine/skinning/construit_final.py -- SORTIE.blend SORTIE.json
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import auto_skin as ak
import mesure_lbs as ml
import pose_chaine as pc
import correction_pose as cp
from mathutils import Vector

AIDE = "mixamorig:LeftArmHelper"
AIDE_D = "mixamorig:RightArmHelper"
argv = sys.argv[sys.argv.index("--") + 1:]
sortie_blend, sortie_json = argv[0], argv[1]
# lissage du champ de décalage des clés (0 = comportement d'origine, reproductible)
LISSAGE = int(argv[2]) if len(argv) > 2 else 0
# nombre d'itérations de calibration des clés (80 = comportement d'origine)
ITER = int(argv[3]) if len(argv) > 3 else 80
# contrainte de gradient kappa (0 = désactivée)
KAPPA = float(argv[4]) if len(argv) > 4 else 0.0

bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/corps_hbm.blend")
corps = bpy.data.objects[ak.ENTREE_NOM]
pts, m = ak.mesurer(corps)
os_ = ak.definir_squelette(pts, m)
for cote, nom in ((+1, "Left"), (-1, "Right")):
    t, q, _ = os_[f"mixamorig:{nom}Arm"]
    os_[f"mixamorig:{nom}ArmHelper"] = (t.copy(), q.copy(), "mixamorig:Spine1")
arm = ak.construire_armature(os_)
ak.skinner(corps, arm)
ak.rattacher_pieces_rigides(arm)
corps.modifiers["Multires"].show_viewport = False

for nom_aide, nom_bras in ((AIDE, "mixamorig:LeftArm"), (AIDE_D, "mixamorig:RightArm")):
    c = arm.pose.bones[nom_aide].constraints.new("COPY_ROTATION")
    c.target = arm; c.subtarget = nom_bras
    c.target_space = "WORLD"; c.owner_space = "WORLD"; c.influence = 0.5
bpy.context.view_layer.update()

specs = [("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:RightArm", (0, 1, 0)),
         ("mixamorig:LeftForeArm", (0, 1, 0)), ("mixamorig:RightForeArm", (0, 1, 0)),
         ("mixamorig:LeftLeg", (1, 0, 0)), ("mixamorig:RightLeg", (1, 0, 0))]
rapport_cles = cp.ajouter_cles_correctives(corps, arm, specs, angle=90, iterations=ITER, lissage=LISSAGE, kappa=KAPPA)
for nom, axe in specs:
    rapport_cles.append(cp.ajouter_cle_seconde_pose(corps, arm, nom, axe, "corr_" + nom.replace("mixamorig:", ""), iterations=ITER, lissage=LISSAGE, kappa=KAPPA))

kb = corps.data.shape_keys.key_blocks
base = kb["Basis"].data


def decal_total(valeurs):
    out = [Vector((0.0, 0.0, 0.0)) for _ in base]
    for cle, v in valeurs.items():
        d = kb[cle].data
        for i in range(len(base)):
            out[i] += (d[i].co - base[i].co) * v
    return out


def valeurs(a):
    return {"v1": min(a / 90, 1.0), "v2": max(0.0, min((a - 90) / 30, 1.0))}


mesures = {}
deplacement_120 = {}
for nom, axe in specs:
    c1 = "corr_" + nom.replace("mixamorig:", "")
    c2 = "c120_" + nom.replace("mixamorig:", "")
    par = {}
    for a in (60, 90, 105, 120):
        v = valeurs(a)
        sauve = pc.poser_chaine(arm, [(nom, axe, a)])
        par[a] = ml.faces_repliees(corps, arm, ml.matrices(arm), decalage=decal_total({c1: v["v1"], c2: v["v2"]}))[0]
        if a == 120:
            # déplacement réel des sommets (LBS, incluant clés) par rapport au repos, en mm
            _, pose, _ = ml.positions_lbs(corps, arm, ml.matrices(arm), decalage=decal_total({c1: 1.0, c2: 1.0}))
            rest, _, _ = ml.positions_lbs(corps, arm, ml.matrices(arm))
            deplacement_120[nom.replace("mixamorig:", "")] = round(max((p - r).length for p, r in zip(pose, rest)) * 1000, 1)
        pc.restaurer(arm, sauve)
    mesures[nom.replace("mixamorig:", "")] = par

repos = max((d.length for d in decal_total({k: 0.0 for k in kb.keys() if k != "Basis"})), default=0.0)
res = {"lissage": LISSAGE, "iterations": ITER, "kappa": KAPPA, "cles": rapport_cles, "replis_par_angle": mesures,
       "deplacement_max_120_mm": deplacement_120,
       "amplitude_repos_mm": round(repos * 1000, 4), "poids": ak.auditer_poids(corps),
       "os": len(arm.data.bones)}
bpy.ops.wm.save_as_mainfile(filepath=sortie_blend)
json.dump(res, open(sortie_json, "w"), indent=2)
print("RES", json.dumps(res))
