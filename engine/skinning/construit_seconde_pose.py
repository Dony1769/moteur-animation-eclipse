"""Ajoute une seconde clé de pose (calibrée à 120°) par articulation, par-dessus la clé à 90°.
Valeur de la seconde clé = clamp((angle - 90) / 30, 0, 1). Mesure à 60, 90, 105, 120 degrés.
Usage : blender -b corps_corr.blend -P engine/skinning/construit_seconde_pose.py -- SORTIE.blend SORTIE.json
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import mesure_lbs as ml
import pose_chaine as pc
import correction_pose as cp
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
sortie_blend, sortie_json = argv[0], argv[1]
bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/corps_corr.blend")
corps = bpy.data.objects["GEO-body_male_realistic"]; arm = bpy.data.objects["Squelette_HBM"]
corps.modifiers["Multires"].show_viewport = False
specs = [("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:RightArm", (0, 1, 0)),
         ("mixamorig:LeftForeArm", (0, 1, 0)), ("mixamorig:RightForeArm", (0, 1, 0)),
         ("mixamorig:LeftLeg", (1, 0, 0)), ("mixamorig:RightLeg", (1, 0, 0))]
rapport = []
for nom, axe in specs:
    cle1 = "corr_" + nom.replace("mixamorig:", "")
    rapport.append(cp.ajouter_cle_seconde_pose(corps, arm, nom, axe, cle1))

kb = corps.data.shape_keys.key_blocks
base = kb["Basis"].data
def decal_total(valeurs):
    out = [Vector((0.0, 0.0, 0.0)) for _ in base]
    for cle, v in valeurs.items():
        d = kb[cle].data
        for i in range(len(base)):
            out[i] += (d[i].co - base[i].co) * v
    return out

def valeurs(angle):
    """Valeurs des clés pour un angle : première clé = clamp(angle/90), seconde = clamp((angle-90)/30)."""
    v1 = min(angle / 90, 1.0); v2 = max(0.0, min((angle - 90) / 30, 1.0))
    return v1, v2

mesures = {}
for nom, axe in specs:
    c1 = "corr_" + nom.replace("mixamorig:", ""); c2 = "c120_" + nom.replace("mixamorig:", "")
    par = {}
    for a in (60, 90, 105, 120):
        v1, v2 = valeurs(a)
        sauve = pc.poser_chaine(arm, [(nom, axe, a)])
        par[a] = ml.faces_repliees(corps, arm, ml.matrices(arm),
                                   decalage=decal_total({c1: v1, c2: v2}))[0]
        pc.restaurer(arm, sauve)
    mesures[nom] = par
# repos : toutes les clés à 0
repos = max((d.length for d in decal_total({k: 0.0 for k in kb.keys() if k != "Basis"})), default=0.0)
res = {"cles": rapport, "replis_par_angle": mesures, "amplitude_repos_mm": round(repos * 1000, 4)}
bpy.ops.wm.save_as_mainfile(filepath=sortie_blend)
json.dump(res, open(sortie_json, "w"), indent=2)
print("RES", json.dumps(res))
