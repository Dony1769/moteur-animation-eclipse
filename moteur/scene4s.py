"""Scène de 4 secondes (jalons 4 à 8), exécutée dans Blender.

Contenu :
- personnage MB-Lab (moteur/personnage.py) rendu en aplats à deux tons + tracés Freestyle (contours) ;
- mouvement en code par angles d'articulations : course (0-1,5 s), saut (1,5-2,5 s), coup (2,5-3 s),
  retour (3-4 s), doigts pliés pendant la course et le coup ;
- caméra : secousse amortie après le coup ; flash une image (silhouette blanche) sur l'image du coup ;
- traits de vitesse : fines bandes derrière le personnage pendant la course, dont les contours sont tracés ;
- décor : sol et buissons procéduraux, dont les bords sont tracés.

Aucune image importée. Aucun dessin à la main. Les formes du décor ne sont visibles que par leurs tracés
(le corps et le décor sont masqués pour le rendu couleur, sauf les aplats à deux tons).
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector

from moteur import costume, personnage, sabre

FPS = 24
NB_IMAGES = 96          # 4 s
GRAINE = 7


# ---------- mouvement ----------

def _os(arm, nom):
    return arm.pose.bones.get(nom)


def _cle(pb, frame, rot=None, loc=None):
    if pb is None:
        return
    pb.rotation_mode = "XYZ"
    if rot is not None:
        pb.rotation_euler = rot
        pb.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert("location", frame=frame)


def _doigts(arm, cote, angle, frame):
    for d in personnage.CHAINES_DOIGTS:
        for i in (1, 2, 3):
            _cle(_os(arm, f"{d}{i:02d}_{cote}"), frame, rot=(angle, 0.0, 0.0))


def poser_repos(arm):
    """Repos : bras le long du corps (les épaules sont en T dans le rig, on les abaisse de 1,0 rad),
    coudes et doigts détendus. Sens validés sur des rendus de contrôle : pour le bras droit, rotation
    Z positive abaisse le bras ; la flexion du coude est positive (avant-bras vers l'avant)."""
    for nom in ("upperarm_R", "lowerarm_R", "upperarm_L", "lowerarm_L", "spine01", "spine02"):
        pb = _os(arm, nom)
        if pb is not None:
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (0.0, 0.0, 0.0)
    _os(arm, "upperarm_R").rotation_euler = (0.0, 0.0, 1.0)
    _os(arm, "upperarm_L").rotation_euler = (0.0, 0.0, -1.0)


def animer(arm, racine):
    """Pose les clés des 96 images. racine = objet armature (déplacement global).

    Sens des angles (validés par rendus de contrôle) : épaule X positif = bras vers l'avant ;
    coude X positif = avant-bras vers l'avant ; doigts X positif = flexion (poing)."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    poser_repos(arm)
    for f in range(1, NB_IMAGES + 1):
        t = (f - 1) / FPS
        if t < 1.5:
            # course : cycle de 0,75 s, bras pliés vers l'avant, poing serré
            ph = 2 * math.pi * (f - 1) / 18.0
            s, c = math.sin(ph), math.cos(ph)
            _cle(_os(arm, "thigh_R"), f, rot=(0.5 * s, 0.0, 0.0))
            _cle(_os(arm, "thigh_L"), f, rot=(-0.5 * s, 0.0, 0.0))
            _cle(_os(arm, "calf_R"), f, rot=(0.8 * max(0.0, -s), 0.0, 0.0))
            _cle(_os(arm, "calf_L"), f, rot=(0.8 * max(0.0, s), 0.0, 0.0))
            _cle(_os(arm, "upperarm_R"), f, rot=(0.5 * s, 0.0, 1.0))
            _cle(_os(arm, "upperarm_L"), f, rot=(-0.5 * s, 0.0, -1.0))
            _cle(_os(arm, "lowerarm_R"), f, rot=(1.0, 0.0, 0.0))
            _cle(_os(arm, "lowerarm_L"), f, rot=(1.0, 0.0, 0.0))
            _cle(_os(arm, "spine01"), f, rot=(0.12, 0.0, 0.0))
            _doigts(arm, "R", 1.1, f)
            _doigts(arm, "L", 1.1, f)
        elif t < 2.5:
            # saut : jambes et bras repliés, hauteur sinusoïdale
            k = (t - 1.5) / 1.0
            hauteur = 0.22 * math.sin(math.pi * k)
            racine.location.z = hauteur
            racine.keyframe_insert("location", index=2, frame=f)
            # jambes repliées vers l'avant (cuisse) et le tibia relevé vers l'arrière
            _cle(_os(arm, "thigh_R"), f, rot=(-0.6 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "thigh_L"), f, rot=(-0.6 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "calf_R"), f, rot=(1.1 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "calf_L"), f, rot=(1.1 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "upperarm_R"), f, rot=(1.2 * math.sin(math.pi * k), 0.0, 1.0))
            _cle(_os(arm, "upperarm_L"), f, rot=(1.2 * math.sin(math.pi * k), 0.0, -1.0))
            _cle(_os(arm, "lowerarm_R"), f, rot=(0.8, 0.0, 0.0))
            _cle(_os(arm, "lowerarm_L"), f, rot=(0.8, 0.0, 0.0))
            _doigts(arm, "R", 0.6, f)
            _doigts(arm, "L", 0.6, f)
        elif t < 3.0:
            # coup : le bras droit (tenant l'épée) part vers l'avant, poing serré, avant-bras tendu
            k = (t - 2.5) / 0.5
            racine.location.z = 0.0
            racine.keyframe_insert("location", index=2, frame=f)
            _cle(_os(arm, "upperarm_R"), f, rot=(1.5 * k, 0.0, 1.0 - 0.3 * k))
            _cle(_os(arm, "lowerarm_R"), f, rot=(0.4 + 0.5 * k, 0.0, 0.0))
            _cle(_os(arm, "spine01"), f, rot=(0.25 * k, 0.0, 0.0))
            _doigts(arm, "R", 1.2, f)
        else:
            # retour à la posture de repos
            k = min(1.0, (t - 3.0) / 0.6)
            _cle(_os(arm, "upperarm_R"), f, rot=(1.5 * (1 - k), 0.0, 1.0 * (0.7 + 0.3 * (1 - k))))
            _cle(_os(arm, "lowerarm_R"), f, rot=(0.9 * (1 - k), 0.0, 0.0))
            _cle(_os(arm, "spine01"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "spine02"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "thigh_R"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "thigh_L"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "calf_R"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "calf_L"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "upperarm_L"), f, rot=(0.0, 0.0, -1.0))
            _cle(_os(arm, "lowerarm_L"), f, rot=(0.0, 0.0, 0.0))
            _doigts(arm, "R", 0.0, f)
            _doigts(arm, "L", 0.0, f)
    bpy.ops.object.mode_set(mode="OBJECT")


def deplacer(racine):
    """Déplacement de l'ensemble : course latérale (axe Y, de droite à gauche de l'écran) pendant 1,5 s."""
    for f in range(1, NB_IMAGES + 1):
        t = (f - 1) / FPS
        y = -0.6 * min(t, 1.5)                 # course latérale, sur l'écran
        racine.location.y = y
        racine.keyframe_insert("location", index=1, frame=f)


# ---------- décor ----------

def decor(graine=GRAINE):
    """Sol et buissons procéduraux. Les bords du sol sont hors cadre."""
    rnd = random.Random(graine)
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    sol = bpy.context.active_object
    sol.name = "Sol"
    sol.data.name = "SolMaillage"
    for i in range(7):
        x = rnd.uniform(-5.0, 5.0)
        y = rnd.uniform(1.5, 4.5)
        r = rnd.uniform(0.35, 0.7)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=r, location=(x, y, r * 0.8))
        bpy.ops.object.shade_smooth()
        bush = bpy.context.active_object
        bush.name = f"Buisson{i}"
        bush.scale = (1.0, 1.0, 0.8)
    return sol


# ---------- matériaux : deux tons + masque ----------

def _mat_deux_tons(nom, clair, ombre, emission=False):
    """Aplats à deux tons : ombre dure, deux couleurs seulement."""
    mat = bpy.data.materials.new(nom)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[0].color = (*ombre, 1.0)
    ramp.color_ramp.elements[1].color = (*clair, 1.0)
    nt.links.new(diff.outputs[0], ramp.inputs[0])
    if emission:
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        nt.links.new(em.outputs[0], out.inputs[0])
    else:
        emis = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(ramp.outputs[0], emis.inputs[0])
        nt.links.new(emis.outputs[0], out.inputs[0])
    return mat


def appliquer_materiaux(corps, sol):
    sol.data.materials.clear()
    sol.data.materials.append(_mat_deux_tons("SolDeuxTons", (0.62, 0.70, 0.58), (0.38, 0.45, 0.36)))
    for o in bpy.data.objects:
        if o.name.startswith("Buisson"):
            o.data.materials.clear()
            o.data.materials.append(_mat_deux_tons("BuissonDeuxTons", (0.45, 0.62, 0.40), (0.24, 0.36, 0.22)))


# ---------- tracés Freestyle ----------

def tracés(scene):
    """Active les tracés Freestyle : contours, arêtes vives et bords ; épaisseur variable."""
    scene.render.use_freestyle = True
    vl = scene.view_layers[0]
    vl.use_freestyle = True
    vl.freestyle_settings.crease_angle = math.radians(35)
    style = bpy.data.linestyles.new("Traits")
    style.thickness = 2.5
    style.color = (0.05, 0.05, 0.08)
    style.use_chaining = True
    style.use_same_object = True
    for ancien in list(vl.freestyle_settings.linesets):
        vl.freestyle_settings.linesets.remove(ancien)   # jeux de tracés par défaut sans style
    ls = vl.freestyle_settings.linesets.new("traits")
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.linestyle = style
    return ls


# ---------- caméra et effets ----------

def camera(scene, objet_cible):
    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (4.6, 0.0, 1.15)
    cam.rotation_euler = (math.radians(90), 0.0, math.radians(90))   # regarde -X, vue de profil
    cam_data.lens = 42
    scene.camera = cam
    return cam


def secousse(cam, frame_depart=72, amplitude=0.07, amortissement=0.35):
    """Caméra : suit la course sur l'axe Y (moitié du déplacement), puis secousse amortie après le coup."""
    base = cam.location.copy()
    for f in range(1, NB_IMAGES + 1):
        t = (f - 1) / FPS
        suivi = -0.3 * min(t, 1.5)
        n = f - frame_depart
        dy = 0.0
        if n >= 0:
            dy = amplitude * math.exp(-amortissement * n) * (1 if n % 2 == 0 else -1)
        cam.location = (base.x, base.y + suivi + dy, base.z)
        cam.keyframe_insert("location", frame=f)
    cam.location = base


def flash(corps, frame=72):
    """Silhouette blanche sur une seule image : copie du corps à matériau émissif, visible à cette image seule."""
    copie = corps.copy()
    copie.name = "FlashCorps"
    bpy.context.scene.collection.objects.link(copie)
    copie.parent = corps.parent
    blanc = _mat_deux_tons("FlashBlanc", (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), emission=True)
    copie.data = corps.data
    for slot in copie.material_slots:
        slot.link = "OBJECT"
        slot.material = blanc
    for f in range(1, NB_IMAGES + 1):
        copie.hide_render = f != frame
        copie.keyframe_insert("hide_render", frame=f)
        corps.hide_render = f == frame
        corps.keyframe_insert("hide_render", frame=f)
    return copie


def traits_vitesse(scene, nb=6, graine=GRAINE):
    """Traits de vitesse : rubans effilés derrière la course (côté +Y), visibles pendant 1,5 s."""
    rnd = random.Random(graine)
    traits = []
    for i in range(nb):
        y0 = rnd.uniform(0.35, 0.7)
        z = rnd.uniform(0.35, 1.45)
        longueur = rnd.uniform(0.5, 0.9)
        largeur = rnd.uniform(0.012, 0.022)
        bm = bmesh.new()
        n = 8
        gauche, droite = [], []
        for k in range(n + 1):
            s = k / n
            y = y0 + longueur * s
            zz = z + 0.03 * math.sin(math.pi * s)
            w = largeur * (1.0 - s) ** 0.8
            gauche.append(bm.verts.new((0.0, y, zz + w)))
            droite.append(bm.verts.new((0.0, y, zz - w)))
        bm.verts.ensure_lookup_table()
        for k in range(n):
            bm.faces.new((gauche[k], gauche[k + 1], droite[k + 1], droite[k]))
        mesh = bpy.data.meshes.new(f"TraitVitesse{i}")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"TraitVitesse{i}", mesh)
        scene.collection.objects.link(obj)
        obj.data.materials.append(costume._mat("TraitNoir", (0.05, 0.05, 0.08), (0.02, 0.02, 0.03)))
        for f in range(1, NB_IMAGES + 1):
            obj.hide_render = not (f <= 36)
            obj.keyframe_insert("hide_render", frame=f)
        traits.append(obj)
    return traits


# ---------- assemblage ----------

def construire(scene):
    scene.frame_start = 1
    scene.frame_end = NB_IMAGES
    scene.render.fps = FPS
    corps, arm = personnage.creer()
    costume.appliquer_costume(corps)
    costume.ajouter_cheveux(arm)
    costume.ajouter_yeux(arm)
    sabre.creer(arm)
    racine = bpy.data.objects.new("Racine", None)
    scene.collection.objects.link(racine)
    corps.parent = racine
    arm.parent = racine
    sol = decor()
    appliquer_materiaux(corps, sol)
    animer(arm, racine)
    deplacer(racine)
    cam = camera(scene, corps)
    secousse(cam)
    flash(corps)
    traits_vitesse(scene)
    tracés(scene)
    return corps, arm, cam
