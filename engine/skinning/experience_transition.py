"""Expérience : élargir la transition des poids autour des articulations (épaule, coude, genou).

Part de la source (corps HBM extrait), refait le squelette et le skinning de base, puis relisse seulement
la zone proche des articulations. Mesure les faces repliées (mesure_lbs) à 30, 60, 90, 120 degrés.

Usage : blender -b corps_hbm.blend -P engine/skinning/experience_transition.py -- RAYON PASSES SORTIE.json
(RAYON 0 = aucune correction, témoin de référence.)
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import auto_skin as ak
import mesure_lbs as ml

argv = sys.argv[sys.argv.index("--") + 1:]
rayon, passes, sortie = float(argv[0]), int(argv[1]), argv[2]
bpy.ops.wm.open_mainfile(filepath=argv[3] if len(argv) > 3 else "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/corps_hbm.blend")
corps = bpy.data.objects[ak.ENTREE_NOM]
pts, m = ak.mesurer(corps)
os_ = ak.definir_squelette(pts, m)
arm = ak.construire_armature(os_)
ak.skinner(corps, arm)                       # heat + lissage global + limite 4 + normalisation (pipeline réel)
if rayon > 0:
    centres = [arm.matrix_world @ arm.data.bones[n].head_local for n in arm.data.bones.keys()
               if any(k in n for k in ("Arm", "ForeArm", "Leg"))]
    centres = [arm.matrix_world @ arm.data.bones[n].head_local for n in arm.data.bones.keys()
               if n.endswith(("Arm", "ForeArm", "Leg"))]
    zone = ak.zone_autour(corps, centres, rayon)
    ak.lisser_limiter_normaliser(corps, facteur=0.5, passes=passes, zone=zone)
    nz = len(zone)
else:
    nz = 0
corps.modifiers["Multires"].show_viewport = False
arts = [("mixamorig:LeftForeArm", (0, 1, 0)), ("mixamorig:RightForeArm", (0, 1, 0)),
        ("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:RightArm", (0, 1, 0)),
        ("mixamorig:LeftLeg", (1, 0, 0)), ("mixamorig:RightLeg", (1, 0, 0))]
r = ml.mesurer_angles(corps, arm, arts, angles=(0, 30, 60, 90, 120))
total_90 = sum(v[90] for v in r.values()); total_120 = sum(v[120] for v in r.values())
res = {"rayon": rayon, "passes": passes, "zone": nz, "replis_90_total": total_90,
       "replis_120_total": total_120, "detail": r, "poids": ak.auditer_poids(corps)}
json.dump(res, open(sortie, "w"), indent=2)
print("RES", json.dumps({"rayon": rayon, "passes": passes, "zone": nz, "90": total_90, "120": total_120}))
