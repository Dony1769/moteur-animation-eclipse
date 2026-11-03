"""Test des combinaisons : replis avec et sans clés correctives, chaînes posées hiérarchiquement.

Valeur de chaque clé = clamp(angle de son os / 90, 0, 1). Compare les replis sans correction et avec correction.
Usage : blender -b corps_corr.blend -P engine/skinning/test_combinaisons.py -- SORTIE.json
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import mesure_lbs as ml
import pose_chaine as pc
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
sortie = argv[0]
bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/corps_corr.blend")
corps = bpy.data.objects["GEO-body_male_realistic"]; arm = bpy.data.objects["Squelette_HBM"]
corps.modifiers["Multires"].show_viewport = False
kb = corps.data.shape_keys.key_blocks

def decal_total(valeurs):
    """Somme des décalages : valeurs = {nom_cle: valeur}."""
    base = kb["Basis"].data
    out = [Vector((0.0, 0.0, 0.0)) for _ in base]
    for cle, v in valeurs.items():
        d = kb[cle].data
        for i in range(len(base)):
            out[i] += (d[i].co - base[i].co) * v
    return out

SCENARIOS = {
    "bras_gauche_coude_90": [("mixamorig:LeftArm", (0, 1, 0), 90), ("mixamorig:LeftForeArm", (0, 1, 0), 90)],
    "bras_gauche_coude_60": [("mixamorig:LeftArm", (0, 1, 0), 60), ("mixamorig:LeftForeArm", (0, 1, 0), 60)],
    "deux_bras_90": [("mixamorig:LeftArm", (0, 1, 0), 90), ("mixamorig:RightArm", (0, 1, 0), 90)],
    "deux_jambes_90": [("mixamorig:LeftLeg", (1, 0, 0), 90), ("mixamorig:RightLeg", (1, 0, 0), 90)],
    "corps_entier_60": [("mixamorig:LeftArm", (0, 1, 0), 60), ("mixamorig:LeftForeArm", (0, 1, 0), 60),
                        ("mixamorig:RightArm", (0, 1, 0), 60), ("mixamorig:RightForeArm", (0, 1, 0), 60),
                        ("mixamorig:LeftLeg", (1, 0, 0), 60), ("mixamorig:RightLeg", (1, 0, 0), 60)],
}
res = {}
for nom_sc, etapes in SCENARIOS.items():
    cles = {}
    for os_nom, _, ang in etapes:
        cles["corr_" + os_nom.replace("mixamorig:", "")] = min(ang / 90, 1.0)
    sauve = pc.poser_chaine(arm, etapes)
    sans = ml.faces_repliees(corps, arm, ml.matrices(arm))[0]
    avec = ml.faces_repliees(corps, arm, ml.matrices(arm), decalage=decal_total(cles))[0]
    pc.restaurer(arm, sauve)
    res[nom_sc] = {"sans_correction": sans, "avec_correction": avec}
json.dump(res, open(sortie, "w"), indent=2)
print("RES", json.dumps(res))

# Témoins de cohérence : un os seul en chaîne doit donner le même résultat que le test à un os.
for nom_t, axe_t, ang_t in [("mixamorig:LeftArm", (0, 1, 0), 60), ("mixamorig:LeftLeg", (1, 0, 0), 90)]:
    sauve = pc.poser_chaine(arm, [(nom_t, axe_t, ang_t)])
    n_chaine = ml.faces_repliees(corps, arm, ml.matrices(arm))[0]
    pc.restaurer(arm, sauve)
    res["temoin_" + nom_t.replace("mixamorig:", "") + "_" + str(ang_t)] = n_chaine
json.dump(res, open(sortie, "w"), indent=2)
print("TEMOINS", {k: v for k, v in res.items() if k.startswith("temoin")})
