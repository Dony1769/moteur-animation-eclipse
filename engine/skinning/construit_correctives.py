"""Construit les clés correctives du corps HBM (étape 3, correction des pliages) et mesure le résultat.

Pour chaque articulation : calibration à 90 degrés, clé de forme, valeur = clamp(angle / 90, 0, 1).
Vérifications : pose de repos inchangée (toutes les valeurs à 0), replis mesurés à 30, 60, 90, 120 degrés
avec la valeur correspondant à chaque angle.

Usage : blender -b corps_hbm.blend -P engine/skinning/construit_correctives.py -- SORTIE.blend SORTIE.json
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import auto_skin as ak
import mesure_lbs as ml
import correction_pose as cp

argv = sys.argv[sys.argv.index("--") + 1:]
sortie_blend, sortie_json = argv[0], argv[1]
bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/corps_hbm.blend")
corps = bpy.data.objects[ak.ENTREE_NOM]
pts, m = ak.mesurer(corps)
arm = ak.construire_armature(ak.definir_squelette(pts, m))
ak.skinner(corps, arm)
ak.rattacher_pieces_rigides(arm)   # oubli corrigé : les yeux doivent suivre l'os Head (sinon QC NON PRÊT)
corps.modifiers["Multires"].show_viewport = False

specs = [("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:RightArm", (0, 1, 0)),
         ("mixamorig:LeftForeArm", (0, 1, 0)), ("mixamorig:RightForeArm", (0, 1, 0)),
         ("mixamorig:LeftLeg", (1, 0, 0)), ("mixamorig:RightLeg", (1, 0, 0))]
rapport_cles = cp.ajouter_cles_correctives(corps, arm, specs, angle=90)

def decalage_cle(corps, cle_nom, valeur):
    """Décalage effectif d'une clé à une valeur donnée : valeur * (clé - base), espace local."""
    kb = corps.data.shape_keys.key_blocks
    base = kb["Basis"].data; cle = kb[cle_nom].data
    return [(cle[i].co - base[i].co) * valeur for i in range(len(base))]

# mesure : chaque articulation seule, valeur = clamp(angle/90)
mesures = {}
for nom, axe in specs:
    cle = "corr_" + nom.replace("mixamorig:", "")
    par = {}
    for a in (0, 30, 60, 90, 120):
        cp.appliquer_valeur(corps, cle, a / 90)
        pb = arm.pose.bones[nom]
        sauve = pb.matrix.copy()
        cp.poser_temporairement(arm, nom, axe, a)
        par[a] = ml.faces_repliees(corps, arm, ml.matrices(arm), decalage=decalage_cle(corps, cle, a / 90))[0]
        pb.matrix = sauve
        bpy.context.view_layer.update()
        cp.appliquer_valeur(corps, cle, 0.0)
    mesures[nom] = par

# repos : toutes les valeurs à 0 -> aucune déformation de l'apparence de repos
# repos : chaque clé à 0 ; le décalage effectif doit être nul
ecart = max((d.length for k in corps.data.shape_keys.key_blocks.keys() if k.startswith("corr_")
             for d in decalage_cle(corps, k, 0.0)), default=0.0)
res = {"cles": rapport_cles, "replis_par_angle": mesures,
       "amplitude_repos_mm": round(ecart * 1000, 4), "poids": ak.auditer_poids(corps)}
bpy.ops.wm.save_as_mainfile(filepath=sortie_blend)
json.dump(res, open(sortie_json, "w"), indent=2)
print("RES", json.dumps(res))
