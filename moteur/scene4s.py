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

import bpy
from mathutils import Vector

from moteur import personnage

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


def animer(arm, racine):
    """Pose les clés des 96 images. racine = objet armature (déplacement global)."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for f in range(1, NB_IMAGES + 1):
        t = (f - 1) / FPS                       # secondes
        # --- course 0 à 1,5 s : cycle de 0,75 s (18 images) ---
        if t < 1.5:
            ph = 2 * math.pi * (f - 1) / 18.0
            s, c = math.sin(ph), math.cos(ph)
            _cle(_os(arm, "thigh_R"), f, rot=(0.55 * s, 0.0, 0.0))
            _cle(_os(arm, "thigh_L"), f, rot=(-0.55 * s, 0.0, 0.0))
            _cle(_os(arm, "calf_R"), f, rot=(-0.9 * max(0.0, -s), 0.0, 0.0))
            _cle(_os(arm, "calf_L"), f, rot=(-0.9 * max(0.0, s), 0.0, 0.0))
            _cle(_os(arm, "upperarm_R"), f, rot=(-0.6 * s, 0.0, 0.0))
            _cle(_os(arm, "upperarm_L"), f, rot=(0.6 * s, 0.0, 0.0))
            _cle(_os(arm, "lowerarm_R"), f, rot=(-0.7, 0.0, 0.0))
            _cle(_os(arm, "lowerarm_L"), f, rot=(-0.7, 0.0, 0.0))
            _cle(_os(arm, "spine01"), f, rot=(0.12, 0.0, 0.0))
            _doigts(arm, "R", 0.9 * (0.5 + 0.5 * s), f)
            _doigts(arm, "L", 0.9 * (0.5 - 0.5 * s), f)
        # --- saut 1,5 à 2,5 s ---
        elif t < 2.5:
            k = (t - 1.5) / 1.0
            hauteur = 0.45 * math.sin(math.pi * k)
            racine.location.z = hauteur
            racine.keyframe_insert("location", index=2, frame=f)
            _cle(_os(arm, "thigh_R"), f, rot=(-0.9 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "thigh_L"), f, rot=(-0.9 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "calf_R"), f, rot=(-1.0 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "calf_L"), f, rot=(-1.0 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "upperarm_R"), f, rot=(-2.4 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "upperarm_L"), f, rot=(-2.4 * math.sin(math.pi * k), 0.0, 0.0))
            _doigts(arm, "R", 0.2, f)
            _doigts(arm, "L", 0.2, f)
        # --- coup 2,5 à 3 s : l'épée (main droite) fend l'air ---
        elif t < 3.0:
            k = (t - 2.5) / 0.5
            _cle(_os(arm, "upperarm_R"), f, rot=(-2.6 + 3.8 * k, 0.0, 0.0))
            _cle(_os(arm, "lowerarm_R"), f, rot=(-0.4 - 0.6 * math.sin(math.pi * k), 0.0, 0.0))
            _cle(_os(arm, "spine01"), f, rot=(0.0, 0.0, -0.2 * k))
            _cle(_os(arm, "spine02"), f, rot=(0.0, 0.0, 0.25 * k))
            _doigts(arm, "R", 1.0 - 0.5 * k, f)
        # --- retour 3 à 4 s : posture de repos ---
        else:
            k = min(1.0, (t - 3.0) / 0.6)
            _cle(_os(arm, "upperarm_R"), f, rot=(1.2 * (1 - k), 0.0, 0.0))
            _cle(_os(arm, "lowerarm_R"), f, rot=(-0.2 * (1 - k), 0.0, 0.0))
            _cle(_os(arm, "spine02"), f, rot=(0.0, 0.0, 0.0))
            _doigts(arm, "R", 0.0, f)
            _doigts(arm, "L", 0.0, f)
            _cle(_os(arm, "thigh_R"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "thigh_L"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "calf_R"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "calf_L"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "upperarm_L"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "lowerarm_L"), f, rot=(0.0, 0.0, 0.0))
            _cle(_os(arm, "spine01"), f, rot=(0.0, 0.0, 0.0))
    bpy.ops.object.mode_set(mode="OBJECT")


def deplacer(racine):
    """Déplacement de l'ensemble : course vers la gauche de l'écran pendant la course."""
    for f in range(1, NB_IMAGES + 1):
        t = (f - 1) / FPS
        x = 0.0
        if t < 1.5:
            x = -0.5 * t
        else:
            x = -0.75
        racine.location = (x, 0.0, racine.location.z)
        racine.keyframe_insert("location", index=0, frame=f)


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
    corps.data.materials.clear()
    corps.data.materials.append(_mat_deux_tons("PeauDeuxTons", (0.93, 0.78, 0.66), (0.42, 0.30, 0.26)))
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
    cam.location = (4.6, 0.0, 0.95)
    cam.rotation_euler = (math.radians(90), 0.0, math.radians(90))   # regarde -X, vue de profil
    cam_data.lens = 50
    scene.camera = cam
    return cam


def secousse(cam, frame_depart=72, amplitude=0.07, amortissement=0.35):
    """Secousse amortie après le coup (sur l'axe Y, alternance de signe)."""
    base = cam.location.copy()
    for f in range(1, NB_IMAGES + 1):
        n = f - frame_depart
        dy = 0.0
        if n >= 0:
            dy = amplitude * math.exp(-amortissement * n) * (1 if n % 2 == 0 else -1)
        cam.location = (base.x, base.y + dy, base.z)
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
    copie.material_slots[0].link = "OBJECT"
    copie.material_slots[0].material = blanc
    for f in range(1, NB_IMAGES + 1):
        copie.hide_render = f != frame
        copie.keyframe_insert("hide_render", frame=f)
        corps.hide_render = f == frame
        corps.keyframe_insert("hide_render", frame=f)
    return copie


# ---------- assemblage ----------

def construire(scene):
    scene.frame_start = 1
    scene.frame_end = NB_IMAGES
    scene.render.fps = FPS
    corps, arm = personnage.creer()
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
    tracés(scene)
    return corps, arm, cam
