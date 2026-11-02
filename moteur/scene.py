"""Scène Blender : réinitialisation, caméra et réglages de rendu (exécuté dans Blender)."""
import bpy


def reinitialiser():
    """Repart d'une scène vide (sans objets ni données orphelines)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def configurer(scene, rendu):
    """Applique la résolution, le nombre d'images et le moteur de rendu."""
    scene.render.resolution_x = rendu.largeur
    scene.render.resolution_y = rendu.hauteur
    scene.render.fps = rendu.fps
    scene.frame_start = 1
    scene.frame_end = rendu.nb_images
    scene.render.engine = rendu.moteur_rendu
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    return scene


def ajouter_camera(scene, position=(0.0, -6.0, 1.5)):
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = position
    cam.rotation_euler = (1.5708, 0.0, 0.0)
    scene.camera = cam
    return cam
