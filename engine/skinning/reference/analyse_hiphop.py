import bpy, sys, json, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
fichier, sortie = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fichier, automatic_bone_orientation=False)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE']
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
res = {"fichier": fichier, "armatures": [a.name for a in arm], "meshes": [m.name for m in meshes]}
A = max(arm, key=lambda a: len(a.pose.bones))
def os_(nom):
    for pb in A.pose.bones:
        if pb.name.split(":")[-1] == nom: return pb
    return None
scn = bpy.context.scene
res["frames"] = [scn.frame_start, scn.frame_end]
res["nb_os"] = len(A.pose.bones)
res["noms_os"] = [b.name for b in A.pose.bones]
# segments articulés : (nom, parent_proximal, distal) -> angle entre segments
def pos(name, frame_pb_head=True):
    pb = os_(name)
    return None if pb is None else A.matrix_world @ (pb.head if frame_pb_head else pb.tail)
def ang_joint(prox, dist):
    """Angle de flexion : 180 deg = segments alignés (membre tendu). Renvoie None si os manquant."""
    a = os_(prox); b = os_(dist)
    if a is None or b is None: return None
    h = A.matrix_world @ a.head; j = A.matrix_world @ b.head; t = A.matrix_world @ b.tail
    u = (j - h).normalized(); v = (t - j).normalized()
    return math.degrees(math.acos(max(-1, min(1, -u.dot(v)))))  # 0 = tendu, >0 = flexion
articulations = {
    "coude_gauche": ("LeftArm", "LeftForeArm"),
    "coude_droit": ("RightArm", "RightForeArm"),
    "genou_gauche": ("LeftUpLeg", "LeftLeg"),
    "genou_droit": ("RightUpLeg", "RightLeg"),
}
plages = {k: [] for k in articulations}
for f in range(scn.frame_start, scn.frame_end + 1):
    scn.frame_set(f)
    for k, (p, d) in articulations.items():
        v = ang_joint(p, d)
        if v is not None: plages[k].append(180.0 - v)  # flexion : 0 = membre tendu
res["plages_flexion_deg"] = {k: ([round(min(v),1), round(max(v),1), len(v)] if v else None) for k, v in plages.items()}
# poids de peau autour du coude gauche (fichier avec maillage)
zone = []
if meshes and os_("LeftArm") is not None:
    scn.frame_set(scn.frame_start)
    coude = A.matrix_world @ os_("LeftForeArm").head
    bras = (A.matrix_world @ os_("LeftArm").head) - coude
    for m in meshes:
        gi = {g.index: g.name.split(":")[-1] for g in m.vertex_groups}
        for v in m.data.vertices:
            p = m.matrix_world @ v.co
            t = (p - coude).dot(bras.normalized())  # <0 côté bras, >0 côté avant-bras (distance signée sur l'axe)
            if abs(t) > 0.20: continue
            wa = sum(g.weight for g in v.groups if gi.get(g.group, "") == "LeftArm")
            wf = sum(g.weight for g in v.groups if gi.get(g.group, "") in ("LeftForeArm",))
            zone.append((round(t,4), round(wa,3), round(wf,3)))
    zone.sort()
    # largeur de transition : distance où le poids de l'avant-bras passe de <0,05 à >0,95
    trans = [z for z in zone if 0.05 < z[2] < 0.95]
    res["poids_coude"] = {"nb_sommets": len(zone),
        "echantillon_t_wa_wf": zone[::max(1,len(zone)//40)],
        "largeur_transition_m": (round(max(z[0] for z in trans) - min(z[0] for z in trans),4) if trans else 0)}
json.dump(res, open(sortie, "w"), indent=1, ensure_ascii=False)
print("OK", sortie)
