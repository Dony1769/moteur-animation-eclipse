import bpy, sys, math, random, time, os

sortie = sys.argv[sys.argv.index("--") + 1]
t0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
ASSETS = os.environ.get("ASSETS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
ph = os.path.join(ASSETS, "ph")

# 1. maillages téléchargés (Poly Haven, CC0) : chargés par nom exact, sans primitives
SOURCES = {
    "falaise": ("namaqualand_cliff_01", "namaqualand_cliff_01_LOD1"),
    "roc_a": ("rock_face_01", "rock_face_01"),
    "roc_b": ("rock_face_02", "rock_face_02"),
    "sable": ("sand_rocks_small_01", "sand_rocks_small_01_LOD3"),
}
gabarits = {}
for cle, (fichier, nom) in SOURCES.items():
    with bpy.data.libraries.load(f"{ph}/{fichier}.blend", link=False) as (src, dst):
        dst.objects = [nom]
    gabarits[cle] = bpy.data.objects[nom]
    print("CHARGE", cle, nom, len(gabarits[cle].data.vertices))

# textures Poly Haven : chemins absolus vers les cartes téléchargées
for im in bpy.data.images:
    if im.filepath.startswith("//textures/"):
        im.filepath = f"{ph}/textures/" + im.filepath.split("/")[-1]
        im.reload()

# les gabarits ne sont pas dans la scène : on les retire de la collection par défaut, on pose des instances liées
for g in gabarits.values():
    if g.name in sc.collection.objects:
        sc.collection.objects.unlink(g)

def instance(gabarit, nom, pos, rot_z, echelle):
    o = bpy.data.objects.new(nom, gabarit.data)       # données partagées : pas de copie du maillage
    o.location = pos
    o.rotation_euler = (0.0, 0.0, rot_z)
    o.scale = echelle
    sc.collection.objects.link(o)
    return o

rnd = random.Random(7)
# 2. parois : deux rangées de falaises et de rochers de part et d'autre d'un passage (axe Y)
for cote, x in (("G", -9.0), ("D", 9.0)):
    for i in range(-9, 10):
        y = i * 5.0 + rnd.uniform(-0.8, 0.8)
        gab = gabarits["falaise"] if i % 3 else gabarits["roc_a"]
        hauteur = rnd.uniform(3.0, 4.2)
        rot = (0.0 if cote == "G" else math.pi) + rnd.uniform(-0.3, 0.3)
        instance(gab, f"Paroi_{cote}{i}", (x + rnd.uniform(-1.0, 1.0), y, 0.0), rot,
                 (1.8, 1.8, hauteur * 2.2 / 4.6))

# 3. sable : débris et rochers au sol, en instances
for i in range(-6, 7):
    for j in range(-12, 13):
        x = i * 3.0
        y = j * 2.6
        instance(gabarits["sable"], f"Sable_{i}_{j}", (x, y, -0.05), rnd.choice((0.0, math.pi)),
                 (1.0, 1.0, 1.0))
print("DECOR", round(time.time() - t0, 1))

# 4. éclairage : HDRI de coucher de soleil (CC0, Poly Haven)
w = bpy.data.worlds.new("Monde"); w.use_nodes = True
nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(f"{ph}/belfast_sunset_puresky_1k.exr")
nt.links.new(env.outputs["Color"], nt.nodes["Background"].inputs["Color"])
sc.world = w
bg = nt.nodes["Background"]; bg.inputs["Strength"].default_value = 1.0
sc_film = True
# lumière dorée de fin de journée : soleil bas, teinte chaude (lampe seulement, pas de géométrie)
soleil_d = bpy.data.lights.new("Soleil", type="SUN")
soleil_d.energy = 6.0
soleil_d.color = (1.0, 0.72, 0.42)
soleil = bpy.data.objects.new("Soleil", soleil_d)
soleil.rotation_euler = (math.radians(68), 0.0, math.radians(35))
sc.collection.objects.link(soleil)

# 5. caméra : 35 mm, angle bas, profondeur de champ
cam_d = bpy.data.cameras.new("Cam")
cam_d.lens = 35
cam_d.dof.use_dof = True
cam_d.dof.focus_distance = 18.0
cam_d.dof.aperture_fstop = 2.8
cam = bpy.data.objects.new("Cam", cam_d)
cam.location = (0.0, -18.0, 1.6)
cam.rotation_euler = (math.radians(80), 0.0, 0.0)
sc.collection.objects.link(cam)
sc.camera = cam




# 5b. cinématique : deux Maria (A originale gagne, B teintée), marche, course, combat, victoire
import math as _m, json, random
from mathutils import Vector
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
import clips
NB = int(os.environ.get("NB", "1440"))
M = os.path.join(ASSETS, "mixamo")
FPS = 24

def charger(fichier):
    avant = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(M, fichier), automatic_bone_orientation=True)
    return [o for o in bpy.data.objects if o not in avant]

def retirer_cubes(objs):
    for o in list(objs):
        if o.type == "MESH" and o.name.startswith("Cube"):
            bpy.data.objects.remove(o, do_unlink=True)

ANIM = {}
for nom in ("Idle", "Sword_Slash", "Hit_Reaction", "Running"):
    nouveaux = charger(nom + ".fbx")
    arm_a = [o for o in nouveaux if o.type == "ARMATURE"][0]
    act = arm_a.animation_data.action
    act.use_fake_user = True
    for fc in list(act.fcurves):
        if fc.data_path == 'pose.bones["mixamorig:Hips"].location' and fc.array_index in (0, 2):
            act.fcurves.remove(fc)
    ANIM[nom] = act
    for o in nouveaux:
        bpy.data.objects.remove(o, do_unlink=True)

def teinter(mat, couleur):
    nt = mat.node_tree
    bsdf = [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"][0]
    entree = bsdf.inputs["Base Color"]
    lien = [l for l in nt.links if l.to_socket == entree]
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[2].default_value = (couleur[0], couleur[1], couleur[2], 1.0)
    if lien:
        nt.links.new(lien[0].from_socket, mix.inputs[1])
        nt.links.remove(lien[0])
    else:
        mix.inputs[1].default_value = tuple(entree.default_value)
    nt.links.new(mix.outputs[0], entree)

# personnages : A originale (gauche, face à B), B teintée (droite)
PERSOS = {}
for cle, x0, angle, teinte in (("A", -6.0, _m.pi / 2, None), ("B", 6.0, -_m.pi / 2, (0.62, 0.8, 1.0))):
    objs = charger("Personnage_Maria.fbx")
    retirer_cubes(objs)
    arm = [o for o in objs if o.type == "ARMATURE"][0]
    maillages = [o for o in objs if o.type == "MESH"]
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    if teinte:
        for m in maillages:
            for slot in m.material_slots:
                if slot.material:
                    slot.material = slot.material.copy()
                    teinter(slot.material, teinte)
    arm.rotation_euler.z = angle
    arm.location = (x0, -9.0, 0.0)
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in maillages for c in o.bound_box]
    arm.scale = tuple(s * (1.75 / (max(zs) - min(zs))) for s in arm.scale)
    PERSOS[cle] = arm

# clips procéduraux (un seul squelette Mixamo) : marche de 4 s, victoire
ACT = {}
for cle, arm in PERSOS.items():
    ACT[(cle, "marche")] = clips.clip_pose(arm, "Marche_" + cle, 96, lambda t: clips.marche((t * 4) % 1))
ACT[("A", "victoire")] = clips.clip_pose(PERSOS["A"], "Victoire_A", 240, clips.victoire)
for arm in PERSOS.values():
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"

# déplacements : pas de marche, puis course, puis position de combat (keyframes sur l'objet)
TRAJET = {"A": [(1, -6.0), (96, -2.8), (168, -0.75), (NB, -0.75)],
          "B": [(1, 6.0), (96, 2.8), (168, 0.75), (NB, 0.75)]}
for cle, arm in PERSOS.items():
    for f, x in TRAJET[cle]:
        arm.location.x = x
        arm.keyframe_insert("location", index=0, frame=f)
    for fc in arm.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

# déroulé du combat : A et B alternent, A porte le coup final
ATTAQUES = []
t, cle_att = 180, "A"
while t < 1150:
    ATTAQUES.append((t, cle_att))
    t += 56
    cle_att = "B" if cle_att == "A" else "A"
if ATTAQUES[-1][1] != "A":
    ATTAQUES.append((1150, "A"))
    ATTAQUES = [a for a in ATTAQUES if a[0] < 1150] + [(1150, "A")]
DERNIER_COUP = ATTAQUES[-1][0]
IMPACTS = [a[0] + 12 for a in ATTAQUES]            # image où le coup touche
EVENEMENTS = []                                     # (image, type de son)

# calendrier NLA : chaque personnage reçoit ses clips, sans chevauchement, avec des bandes de repos
def longueur(act):
    return int(act.frame_range[1] - act.frame_range[0]) + 1

def ajouter(piste, nom, act, debut, duree):
    L = longueur(act)
    s = piste.strips.new(nom, int(debut), act)
    if duree <= L:
        s.action_frame_end = s.action_frame_start + duree - 1
    else:
        s.repeat = _m.ceil(duree / L)
    return s

def planifier(cle):
    ev = []
    ev.append((1, ACT[(cle, "marche")], 96))
    ev.append((96, ANIM["Running"], 72))
    for debut, att in ATTAQUES:
        if att == cle:
            ev.append((debut, ANIM["Sword_Slash"], 31))
        else:
            ev.append((debut + 12, ANIM["Hit_Reaction"], 39))
    if cle == "A":
        ev.append((DERNIER_COUP + 31, ACT[("A", "victoire")], 240))
    return sorted(ev, key=lambda e: e[0])

for cle, arm in PERSOS.items():
    ad = arm.animation_data_create()
    piste = ad.nla_tracks.new()
    curseur = 1
    for debut, act, duree in planifier(cle):
        if debut > curseur:
            s = ajouter(piste, "Repos", ANIM["Idle"], curseur, debut - curseur)
            curseur = int(s.frame_end) + 1
        debut = max(debut, curseur)
        s = ajouter(piste, act.name, act, debut, duree)
        curseur = int(s.frame_end) + 1
    if curseur <= NB:
        ajouter(piste, "Repos_fin", ANIM["Idle"], curseur, NB + 1 - curseur)
    ad.action = None

# B tombe en arrière après le dernier coup (rotation autour de l'axe latéral, pieds au sol)
B = PERSOS["B"]
B.rotation_mode = "XYZ"
for f, ang in ((DERNIER_COUP + 40, 0.0), (DERNIER_COUP + 80, -_m.pi / 2)):
    B.rotation_euler.x = ang
    B.keyframe_insert("rotation_euler", index=0, frame=f)
# hauteur image par image : le point le plus bas du maillage reste exactement au sol
def _point_bas(arm):
    dg = bpy.context.evaluated_depsgraph_get()
    zs = []
    for o in [x for x in bpy.data.objects if x.type == "MESH" and x.parent is arm or (x.type == "MESH" and x.find_armature() is arm)]:
        ev = o.evaluated_get(dg)
        zs += [(ev.matrix_world @ Vector(c)).z for c in ev.bound_box]
    return min(zs)

for f in range(DERNIER_COUP + 40, DERNIER_COUP + 81, 2):
    sc.frame_set(f)
    B.location.z = 0.0                      # repartir de zéro à chaque image : pas d'accumulation
    bpy.context.view_layer.update()
    B.location.z = -_point_bas(B)           # point le plus bas exactement à z = 0
    B.keyframe_insert("location", index=2, frame=f)
sc.frame_set(1)

# effets : débris de sable en arc à chaque impact (gabarit Poly Haven, pas de primitive)
rnd2 = random.Random(11)
for h in IMPACTS:
    for k in range(6):
        v = Vector((rnd2.uniform(-0.04, 0.04), rnd2.uniform(-0.02, 0.02), rnd2.uniform(0.02, 0.06)))
        p0 = Vector((0.0, -9.0, 1.2))
        d = instance(gabarits["sable"], f"Debris_{h}_{k}", tuple(p0), rnd2.uniform(0, 6.28), (0.05, 0.05, 0.05))
        d.scale = (0.0, 0.0, 0.0)
        d.keyframe_insert("scale", frame=h - 1)
        for n in range(14):
            pos = p0 + v * n + Vector((0.0, 0.0, -0.0009 * n * n))
            d.location = tuple(pos)
            d.keyframe_insert("location", frame=h + n)
            d.scale = (0.05, 0.05, 0.05) if n < 13 else (0.0, 0.0, 0.0)
            d.keyframe_insert("scale", frame=h + n)

# sons : pas, sabre, impacts, chute (calés sur les images)
for f in list(range(12, 168, 12)) + list(range(96, 168, 9)):
    EVENEMENTS.append((f, "pas"))
for debut, att in ATTAQUES:
    EVENEMENTS.append((debut + 6, "sabre"))
for h in IMPACTS:
    EVENEMENTS.append((h, "impact"))
EVENEMENTS.append((DERNIER_COUP + 44, "chute"))
os.makedirs(sortie, exist_ok=True)
with open(os.path.join(sortie, "evenements.json"), "w") as fichier:
    json.dump(EVENEMENTS, fichier)

# caméra : plans liés aux marqueurs, secousse aux impacts
RIG = bpy.data.objects.new("CamRig", None)
sc.collection.objects.link(RIG)
PLANS = [
    (1,    "PlanLarge",   (0.0, -14.0, 2.2), 84, 0,    35, 12.0, 2.8),
    (241,  "PlanMoyen",   (0.0, -12.5, 1.4), 90, 0,    35,  9.0, 2.8),
    (481,  "PlanProfilA", (-0.9, -11.6, 1.35), 90, 0,  50,  2.6, 2.0),
    (640,  "ContreJour",  (0.0, -12.0, 0.35), 96, 0,   35,  9.0, 2.8),
    (841,  "PlanProfilB", (0.8, -11.6, 1.35), 90, 0,   50,  2.6, 2.0),
    (1081, "PlanLarge2",  (0.0, -14.0, 3.0), 76, 0,    35, 12.0, 2.8),
    (1181, "PlanVictoire", (0.0, -14.0, 2.4), 84, 0,   35, 12.0, 2.8),
]
marqueurs = []
for frame, nom, pos, rot_x, rot_z, lentille, mise_au_point, ouverture in PLANS:
    c_d = bpy.data.cameras.new("Cam_" + nom)
    c_d.lens = lentille
    c_d.dof.use_dof = True
    c_d.dof.focus_distance = mise_au_point
    c_d.dof.aperture_fstop = ouverture
    c = bpy.data.objects.new("Cam_" + nom, c_d)
    sc.collection.objects.link(c)
    c.parent = RIG
    c.location = pos
    c.rotation_euler = (_m.radians(rot_x), 0.0, _m.radians(rot_z))
    m = sc.timeline_markers.new(nom, frame=frame)
    m.camera = c
    marqueurs.append(c)
sc.camera = marqueurs[0]
for f in range(1, NB + 1):
    k = 0.0
    for t_imp in IMPACTS:
        if 0 <= f - t_imp < 8:
            k += 0.05 * (1 - (f - t_imp) / 8.0) * _m.sin((f - t_imp) * 2.5)
    RIG.location = (k, 0.0, k * 0.5)
    RIG.keyframe_insert("location", frame=f)

sc.frame_start, sc.frame_end = int(os.environ.get("F0", "1")), int(os.environ.get("F1", str(NB)))
sc.frame_set(1)
# 6. rendu : Cycles CPU, débruitage, 3 rebonds, sans caustiques, 1280x540
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU" if os.environ.get("DEVICE", "CPU") == "CPU" else "GPU"
if sc.cycles.device == "GPU":
    # essaie le backend demandé (OPTIX par défaut), puis CUDA ; n'active que les GPU, jamais le CPU
    prefs = bpy.context.preferences.addons["cycles"].preferences
    gpu = []
    for backend in (os.environ.get("BACKEND", "OPTIX"), "CUDA"):
        prefs.compute_device_type = backend
        prefs.get_devices()
        gpu = [d for d in prefs.devices if d.type != "CPU"]
        if gpu:
            break
    for d in prefs.devices:
        d.use = d.type != "CPU"
    sc.cycles.device = "GPU" if gpu else "CPU"
    print("RENDU", sc.cycles.device, prefs.compute_device_type if gpu else "-", [d.name for d in gpu])
sc.cycles.samples = int(os.environ.get("SPP", "2"))
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 3
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("RX", "960")), int(os.environ.get("RY", "405"))
sc.render.film_transparent = False
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "AgX"
sc.render.filepath = f"{sortie}/frame_"
t1 = time.time()
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = 0.5
bpy.ops.render.render(animation=True)
print("TEMPS_RENDU_IMAGE", round(time.time() - t1, 1))
print("COMBAT2_DONE", round(time.time() - t0, 1))
