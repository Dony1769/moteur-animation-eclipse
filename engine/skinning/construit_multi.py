"""Correction par angle à trois échantillons indépendants (pose space, interpolation linéaire par morceaux).

Principe : une clé par échantillon d'angle (60, 90, 120 degrés). Chaque clé est calibrée SEULE à son angle,
à partir d'un décalage nul, donc sans additionner les clés entre elles. Sa valeur suit un chapeau :
valeur(a) = max(0, 1 - |a - a_k| / 30). Ainsi, à tout angle, le décalage total est l'interpolation linéaire
entre les échantillons voisins (partition de l'unité sur [60, 120]).

Témoin : à 0 degré, toutes les valeurs valent 0 (repos inchangé).
Mesures : replis LBS à 60/90/105/120, étirement maximal des arêtes, volume (évalué par Blender).

Usage : blender -b corps_hbm.blend -P engine/skinning/construit_multi.py -- SORTIE.blend SORTIE.json
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import auto_skin as ak
import mesure_lbs as ml
import pose_chaine as pc
import correction_pose as cp
from mathutils import Vector

ECHANTILLONS = (60, 90, 120)
DEMI_SUPPORT = 30.0
import os
ITER = int(os.environ.get("ITER", "150"))
AMP = float(os.environ.get("AMP", "0.04"))
argv = sys.argv[sys.argv.index("--") + 1:]
sortie_blend, sortie_json = argv[0], argv[1]

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
for nom_aide, nom_bras in (("mixamorig:LeftArmHelper", "mixamorig:LeftArm"), ("mixamorig:RightArmHelper", "mixamorig:RightArm")):
    c = arm.pose.bones[nom_aide].constraints.new("COPY_ROTATION")
    c.target = arm; c.subtarget = nom_bras
    c.target_space = "WORLD"; c.owner_space = "WORLD"; c.influence = 0.5
bpy.context.view_layer.update()

SPECS = [("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:RightArm", (0, 1, 0)),
         ("mixamorig:LeftForeArm", (0, 1, 0)), ("mixamorig:RightForeArm", (0, 1, 0)),
         ("mixamorig:LeftLeg", (1, 0, 0)), ("mixamorig:RightLeg", (1, 0, 0))]

if corps.data.shape_keys is None:
    corps.shape_key_add(name="Basis", from_mix=False)
rapport = []
for nom, axe in SPECS:
    base_nom = nom.replace("mixamorig:", "")
    for a_k in ECHANTILLONS:
        decal, hist = cp.calculer_decalage(corps, arm, nom, axe, a_k, iterations=ITER, amplitude_max=AMP, mode="moins_normale")
        cle = corps.shape_key_add(name=f"m{a_k}_{base_nom}", from_mix=False)
        cle.slider_min = 0.0; cle.slider_max = 1.0; cle.value = 0.0
        for i, d in enumerate(decal):
            cle.data[i].co = corps.data.vertices[i].co + d
        rapport.append({"cle": cle.name, "os": nom, "angle": a_k, "replis_avant": hist[0], "replis_apres": hist[-1],
                        "iterations": len(hist), "amplitude_max_mm": round(max(d.length for d in decal) * 1000, 2)})

kb = corps.data.shape_keys.key_blocks


def chapeau(a, a_k):
    return max(0.0, 1.0 - abs(a - a_k) / DEMI_SUPPORT)


def fixer_cles(nom, a):
    base_nom = nom.replace("mixamorig:", "")
    for a_k in ECHANTILLONS:
        kb[f"m{a_k}_{base_nom}"].value = chapeau(a, a_k)
    bpy.context.view_layer.update()


def reset():
    for k in kb:
        k.value = 0.0
    bpy.context.view_layer.update()


def decal_total(valeurs):
    """Décalage total (local) de toutes les clés actives, pondérées par leur valeur."""
    base = kb["Basis"].data
    out = [Vector((0.0, 0.0, 0.0)) for _ in base]
    for cle, v in valeurs.items():
        d = kb[cle].data
        for i in range(len(base)):
            out[i] += (d[i].co - base[i].co) * v
    return out


mesures = {}
for nom, axe in SPECS:
    par = {}
    for a in (0, 60, 90, 105, 120):
        reset()
        fixer_cles(nom, a)
        valeurs = {f"m{a_k}_{nom.replace('mixamorig:', '')}": chapeau(a, a_k) for a_k in ECHANTILLONS}
        sauve = pc.poser_chaine(arm, [(nom, axe, a)])
        par[a] = ml.faces_repliees(corps, arm, ml.matrices(arm), decalage=decal_total(valeurs))[0]
        pc.restaurer(arm, sauve)
    reset()
    mesures[nom.replace("mixamorig:", "")] = par

repos_amp = 0.0
reset()
res = {"echantillons": ECHANTILLONS, "chapeau_demi_support": DEMI_SUPPORT, "iterations": ITER, "amplitude_max": AMP,
       "cles": rapport, "replis_par_angle": mesures, "poids": ak.auditer_poids(corps), "os": len(arm.data.bones)}
bpy.ops.wm.save_as_mainfile(filepath=sortie_blend)
json.dump(res, open(sortie_json, "w"), indent=2)
print("RES", json.dumps(res["replis_par_angle"]))
