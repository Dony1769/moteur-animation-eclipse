"""Animation par capture de mouvement CMU (domaine public, base de données CMU Graphics Lab), retargetée
sur le rig MB-Lab. Exécuté dans Blender.

Méthode : pour chaque os du rig cible, on copie la rotation monde que l'os source applique à partir de son
repos (delta), et on la compose avec le repos de l'os cible. Les longueurs sont mises à l'échelle sur la
cuisse. Le déplacement horizontal de la racine est ignoré (course sur place) ; seule la hauteur du bassin
est reprise. Les coups et sauts viennent de clips réels.

Clips utilisés (index CMU) :
- course : sujet 9, essai 1 (09_01)
- saut en avant : sujet 13, essai 11 (13_11), phase aérienne vers l'image 250
- coup d'épée : sujet 2, essai 9 (02_09)
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

from moteur import personnage

DOSSIER = "/home/claude/moteur3d/mocap"

# os CMU -> os MB-Lab
ASSOC = {
    "Hips": "pelvis",
    "LowerBack": "spine01", "Spine": "spine02", "Spine1": "spine03",
    "Neck": "neck", "Head": "head",
    "LeftShoulder": "clavicle_L", "LeftArm": "upperarm_L", "LeftForeArm": "lowerarm_L", "LeftHand": "hand_L",
    "RightShoulder": "clavicle_R", "RightArm": "upperarm_R", "RightForeArm": "lowerarm_R", "RightHand": "hand_R",
    "LeftUpLeg": "thigh_L", "LeftLeg": "calf_L", "LeftFoot": "foot_L", "LeftToeBase": "toes_L",
    "RightUpLeg": "thigh_R", "RightLeg": "calf_R", "RightFoot": "foot_R", "RightToeBase": "toes_R",
}
DST2SRC = {v: k for k, v in ASSOC.items()}

# ordre parent -> enfant (requis pour que chaque os suive son parent)
ORDRE = [
    "pelvis", "spine01", "spine02", "spine03", "neck", "head",
    "clavicle_L", "upperarm_L", "lowerarm_L", "hand_L",
    "clavicle_R", "upperarm_R", "lowerarm_R", "hand_R",
    "thigh_L", "calf_L", "foot_L", "toes_L",
    "thigh_R", "calf_R", "foot_R", "toes_R",
]

# segments de la scène : (image scène début, image scène fin, fichier, image CMU début, images CMU par image scène)
# CMU : 120 images/s ; scène : 24 images/s, donc 5 images CMU par image scène = vitesse réelle
SEGMENTS = [
    (1, 36, "run/09_01.bvh", 1, 5),          # course 1,5 s (boucle sur le cycle)
    (37, 60, "jump/13_11.bvh", 191, 5),      # saut 1 s
    (61, 72, "sword/02_09.bvh", 401, 5),     # coup 0,5 s
]
FIN_RETOUR = 96                               # retour au repos sur les images 73 à 96


def _importer(fichier):
    avant = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(
        filepath=f"{DOSSIER}/{fichier}", axis_forward="-Z", axis_up="Y", global_scale=1.0,
        frame_start=1, use_fps_scale=False, update_scene_fps=False, update_scene_duration=False,
        use_cyclic=False, rotate_mode="NATIVE",
    )
    nouveaux = [o for o in bpy.data.objects if o not in avant and o.type == "ARMATURE"]
    return nouveaux[0]


def _alignement(cmu):
    """Matrice qui oriente le squelette source vers -Y (avant de Kaël). Retourne (A, latéral)."""
    b = cmu.data.bones
    avant = b["LeftToeBase"].head_local - b["LeftFoot"].head_local
    avant.z = 0.0
    A = avant.normalized().rotation_difference(Vector((0.0, -1.0, 0.0))).to_matrix()
    lateral = A @ (b["LeftUpLeg"].head_local - b["RightUpLeg"].head_local)
    return A, lateral


BRAS = ("clavicle_L", "upperarm_L", "lowerarm_L", "hand_L", "clavicle_R", "upperarm_R", "lowerarm_R", "hand_R")


def _pendre_bras(arm):
    """Rotation de repos des bras : fait pendre les bras le long du corps (la T-pose de MB-Lab les tient à
    l'horizontale). Renvoie {os: matrice 3x3} à appliquer au repos de chaque os du bras. Le signe est choisi
    par test : l'upperarm doit pointer vers le bas (-Z) après rotation."""
    cibles = {}
    for cote in ("L", "R"):
        os_ = arm.data.bones[f"upperarm_{cote}"]
        d = (os_.tail_local - os_.head_local).normalized()
        meilleur = None
        for signe in (1.0, -1.0):
            C = Matrix.Rotation(signe * _angle_bas(d), 3, "Y")
            erreur = (C @ d - Vector((0.0, 0.0, -1.0))).length
            if meilleur is None or erreur < meilleur[0]:
                meilleur = (erreur, C)
        # léger écart vers l'extérieur (0,2 rad) : sinon les bras sont dans l'ombre du tronc en profil
        exterieur = -1.0 if cote == "R" else 1.0
        meilleur_ecart = None
        for signe in (1.0, -1.0):
            E = Matrix.Rotation(signe * 0.2, 3, "Y") @ meilleur[1]
            v = E @ d
            score = v.x * exterieur
            if meilleur_ecart is None or score > meilleur_ecart[0]:
                meilleur_ecart = (score, E)
        meilleur = (meilleur[0], meilleur_ecart[1])
        cibles[f"upperarm_{cote}"] = meilleur[1]
        cibles[f"lowerarm_{cote}"] = meilleur[1]
        cibles[f"hand_{cote}"] = meilleur[1]
        cibles[f"clavicle_{cote}"] = meilleur[1]
        print("BRAS", cote, "erreur", round(meilleur[0], 3))
    return cibles


def _angle_bas(d):
    """Angle (rad) entre l'axe -Z et la direction d projetée sur le plan XZ."""
    return math.atan2(d.x, -d.z)


def _pose_image(cmu, arm, A, Ai, echelle, image, ref, rep, bassin_neutre):
    """Pose le rig cible sur l'image CMU `image` (1-based). Renvoie {os: (quaternion, position)}.
    ref : pose de référence de la source (image neutre) ; rep : rotations de repos des bras."""
    bpy.context.scene.frame_set(image)
    vl = bpy.context.view_layer
    vl.update()
    res = {}
    dz = (A @ (cmu.pose.bones["Hips"].matrix.translation - bassin_neutre)).z * echelle
    for dst in ORDRE:
        src = DST2SRC[dst]
        pb = arm.pose.bones[dst]
        pb.rotation_mode = "QUATERNION"
        P = cmu.pose.bones[src].matrix.to_3x3()
        P0 = ref[src]
        D = A @ P @ P0.inverted() @ Ai
        Rd = arm.data.bones[dst].matrix_local.to_3x3()
        if dst in rep:
            Rd = rep[dst] @ Rd
        M = D @ Rd
        if dst == "pelvis":
            tete = arm.data.bones["pelvis"].head_local + Vector((0.0, 0.0, dz))
        else:
            tete = pb.matrix.translation.copy()
        pb.matrix = Matrix.Translation(tete) @ M.to_4x4()
        vl.update()
        res[dst] = (pb.rotation_quaternion.copy(), pb.location.copy())
    return res


def _lisser(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def animer(arm, echelle_jambe=None):
    """Anime le rig MB-Lab avec les clips CMU. Retourne la liste des images clés posées."""
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FIN_RETOUR
    resultats = {}          # image scène -> {os: (q, loc)}
    rep = _pendre_bras(arm)
    for debut, fin, fichier, image0, pas in SEGMENTS:
        cmu = _importer(fichier)
        A, lateral = _alignement(cmu)
        if lateral.x < 0:
            raise RuntimeError(f"{fichier}: gauche et droite inversées après alignement ({lateral})")
        Ai = A.inverted()
        echelle = arm.data.bones["thigh_L"].length / cmu.data.bones["LeftUpLeg"].length
        nb_images = int(cmu.animation_data.action.frame_range[1]) if cmu.animation_data else 149
        # référence : pose neutre de la source (image 1), où les bras sont le long du corps
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        ref = {src: cmu.pose.bones[src].matrix.to_3x3().copy() for src in ASSOC}
        bassin_neutre = cmu.pose.bones["Hips"].matrix.translation.copy()
        for f in range(debut, fin + 1):
            image = image0 + ((f - debut) * pas) % nb_images
            resultats[f] = _pose_image(cmu, arm, A, Ai, echelle, image, ref, rep, bassin_neutre)
        # supprime le squelette source avant le clip suivant
        bpy.data.objects.remove(cmu, do_unlink=True)
        print("CLIP", fichier, "lateral", tuple(round(x, 2) for x in lateral), "echelle", round(echelle, 3))
    # entrée depuis le repos : images 1 à 8
    repos = {dst: resultats[1][dst] for dst in ORDRE}   # pose neutre (bras le long du corps)
    for f in range(1, 9):
        w = _lisser((f - 1) / 8.0)
        resultats[f] = {
            dst: (repos[dst][0].slerp(resultats[f][dst][0], w), repos[dst][1].lerp(resultats[f][dst][1], w))
            for dst in ORDRE
        }
    # retour au repos : images 73 à 96
    dernier = resultats[72]
    for f in range(73, FIN_RETOUR + 1):
        w = _lisser((f - 72) / (FIN_RETOUR - 72))
        resultats[f] = {
            dst: (dernier[dst][0].slerp(repos[dst][0], w), dernier[dst][1].lerp(repos[dst][1], w))
            for dst in ORDRE
        }
    # images clés sur le rig cible
    for f in range(1, FIN_RETOUR + 1):
        for dst in ORDRE:
            pb = arm.pose.bones[dst]
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = resultats[f][dst][0]
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if dst == "pelvis":
                pb.location = resultats[f][dst][1]
                pb.keyframe_insert("location", frame=f)
    return resultats


def doigts(arm, cote, angle_par_image):
    """Poings : flexion des doigts (X positif = flexion), valeur par image."""
    from moteur.scene4s import _cle, _os  # import local : évite le cycle au chargement
    for f, angle in angle_par_image.items():
        for d in personnage.CHAINES_DOIGTS:
            for i in (1, 2, 3):
                _cle(_os(arm, f"{d}{i:02d}_{cote}"), f, rot=(angle, 0.0, 0.0))
