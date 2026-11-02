"""Passes OpenGL 3.3 du rendu NPR (moderngl).

Deux chemins, même ombrage et même contour :
  1. maillage : geometrie -> G-buffer MRT -> ombrage -> contour -> image ;
  2. 2.5D     : G-buffer déjà calculé (relief.composer) -> ombrage -> contour -> image.

G-buffer (quatre sorties MRT, RGBA32F, GL_NEAREST et GL_CLAMP_TO_EDGE) :
  albedo     : RGB ;
  normale    : xyz vue, brute (fond = 0) ;
  profondeur : r = d linéaire (fond = 0), g,b = UV de surface ;
  tangente   : xyz vue unitaire (zéro = pas de cheveux).
Les tableaux passés à dessiner_gbuffer() sont en ordre OpenGL : ligne 0 en bas.
"""
from pathlib import Path

import numpy as np
import moderngl

from .parametres import ParamsContour, ParamsOmbrage
from .rampe import rampe_par_defaut

DOSSIER_SHADERS = Path(__file__).parent / "shaders"


def _lire(nom):
    return (DOSSIER_SHADERS / nom).read_text(encoding="utf-8")


def _unitaire(v):
    v = np.asarray(v, np.float32)
    return tuple(v / np.linalg.norm(v))


def _vers_rgba(arr):
    """Tableau (H, W) ou (H, W, k <= 4) -> octets RGBA32F (complétés par 0)."""
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2:
        arr = arr[..., None]
    H, W, k = arr.shape
    out = np.zeros((H, W, 4), np.float32)
    out[..., :k] = arr
    return np.ascontiguousarray(out).tobytes()


def creer_contexte():
    """Contexte OpenGL 3.3+ hors écran. Essaie EGL puis le backend par défaut.

    Renvoie None si aucun contexte n'est disponible (les tests GL sont alors ignorés).
    """
    for backend in ("egl", None):
        try:
            if backend is None:
                return moderngl.create_standalone_context()
            return moderngl.create_standalone_context(backend=backend)
        except Exception:
            continue
    return None


def perspective(fovy_deg, aspect, pres, loin):
    """Matrice de projection (convention maths, ligne-majeure)."""
    f = 1.0 / np.tan(np.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4), np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (loin + pres) / (pres - loin)
    m[2, 3] = 2.0 * loin * pres / (pres - loin)
    m[3, 2] = -1.0
    return m


def translation(x, y, z):
    m = np.eye(4, dtype=np.float32)
    m[:3, 3] = (x, y, z)
    return m


def _octets_mat(m):
    """Matrice ligne-majeure -> octets colonne-majeure attendus par GLSL."""
    return np.ascontiguousarray(np.asarray(m, np.float32).T).tobytes()


class Maillage:
    """Maillage indexé (sommets, normales, UV, tangentes, triangles) envoyé sur le GPU."""

    def __init__(self, ctx, programme, sommets, normales, uv, tangentes, triangles):
        donnees = np.hstack([sommets, normales, uv, tangentes]).astype(np.float32)
        self.vbo = ctx.buffer(donnees.tobytes())
        self.ibo = ctx.buffer(np.asarray(triangles, np.uint32).tobytes())
        self.vao = ctx.vertex_array(
            programme,
            [(self.vbo, "3f 3f 2f 3f", "in_position", "in_normal", "in_uv", "in_tangent")],
            self.ibo,
        )


class RenduNPR:
    """Chaîne NPR sur des cibles hors écran de taille fixe."""

    def __init__(self, ctx, largeur, hauteur, rampe_u8=None, ombrage=None, contour=None):
        self.ctx = ctx
        self.largeur = largeur
        self.hauteur = hauteur
        self.p_ombrage = ombrage or ParamsOmbrage()
        self.p_contour = contour or ParamsContour()
        dims = (largeur, hauteur)

        def cible(composantes=4, dtype="f4"):
            t = ctx.texture(dims, composantes, dtype=dtype)
            t.filter = (moderngl.NEAREST, moderngl.NEAREST)
            t.repeat_x = False      # CLAMP_TO_EDGE : le Sobel lit au-delà du bord, comme la référence
            t.repeat_y = False
            return t

        self.t_albedo = cible()
        self.t_normale = cible()
        self.t_profondeur = cible()
        self.t_tangente = cible()
        self.t_ombrage = cible()
        self.t_final = cible(4, "f1")
        self.tampon_z = ctx.depth_renderbuffer(dims)
        self.fbo_geo = ctx.framebuffer(
            color_attachments=[self.t_albedo, self.t_normale, self.t_profondeur, self.t_tangente],
            depth_attachment=self.tampon_z,
        )
        self.fbo_ombrage = ctx.framebuffer(color_attachments=[self.t_ombrage])
        self.fbo_final = ctx.framebuffer(color_attachments=[self.t_final])

        rampe_u8 = rampe_par_defaut() if rampe_u8 is None else rampe_u8
        self.t_rampe = ctx.texture(
            (rampe_u8.shape[0], 1), 3,
            data=np.ascontiguousarray(rampe_u8, np.uint8).tobytes(), dtype="f1",
        )
        self.t_rampe.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.t_rampe.repeat_x = False
        self.t_rampe.repeat_y = False

        self.albedo_defaut = ctx.texture((1, 1), 4, data=b"\xff" * 4, dtype="f1")
        self.albedo_defaut.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.albedo_defaut.repeat_x = False
        self.albedo_defaut.repeat_y = False
        self.masque_defaut = self._texture_masque(np.ones((1, 1), np.float32))   # valeur 1
        self.masque_zero = self._texture_masque(np.zeros((1, 1), np.float32))    # valeur 0
        self.t_masque_sphere = self.masque_defaut
        self.t_masque_ombre = self.masque_defaut
        self.t_masque_cheveux = self.masque_zero       # pas de reflet tant qu'on n'en définit pas

        self.prog_geo = ctx.program(vertex_shader=_lire("geometrie.vert"),
                                    fragment_shader=_lire("geometrie.frag"))
        self.prog_ombrage = ctx.program(vertex_shader=_lire("plein_ecran.vert"),
                                        fragment_shader=_lire("ombrage.frag"))
        self.prog_contour = ctx.program(vertex_shader=_lire("plein_ecran.vert"),
                                        fragment_shader=_lire("contour.frag"))

        quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], np.float32).tobytes())
        self.vao_ombrage = ctx.vertex_array(self.prog_ombrage, [(quad, "2f", "in_position")])
        self.vao_contour = ctx.vertex_array(self.prog_contour, [(quad, "2f", "in_position")])

    # ---- textures et masques -------------------------------------------------

    def _texture_masque(self, masque):
        h, w = masque.shape
        t = self.ctx.texture((w, h), 1,
                             data=np.ascontiguousarray(masque, np.float32).tobytes(), dtype="f4")
        t.filter = (moderngl.NEAREST, moderngl.NEAREST)
        t.repeat_x = False
        t.repeat_y = False
        return t

    def texture_rgb(self, rgb):
        """Texture d'albédo RGB (hauteur, largeur, 3), lue en UV."""
        h, w = rgb.shape[:2]
        t = self.ctx.texture((w, h), 3,
                             data=np.ascontiguousarray(rgb, np.float32).tobytes(), dtype="f4")
        t.filter = (moderngl.NEAREST, moderngl.NEAREST)
        t.repeat_x = False
        t.repeat_y = False
        return t

    def definir_masques(self, masque_sphere=None, masque_ombre=None):
        """Masques UV ou écran (tableaux [v, u] de floats 0..1). None = valeur 1 partout.

        masque_sphere : 1 = normale sphérique, 0 = normale réelle (autour du nez).
        masque_ombre  : 1 = l'ombre de la rampe est autorisée (si masque_visage est actif).
        """
        self.t_masque_sphere = self.masque_defaut if masque_sphere is None else self._texture_masque(masque_sphere)
        self.t_masque_ombre = self.masque_defaut if masque_ombre is None else self._texture_masque(masque_ombre)

    def definir_masque_cheveux(self, masque=None):
        """Masque des cheveux (tableau [v, u], 0..1). None = aucun reflet de cheveux."""
        self.t_masque_cheveux = self.masque_zero if masque is None else self._texture_masque(masque)

    # ---- passes ------------------------------------------------------------

    def _ombrer(self, tan_fov, centre_tete_vue, lumiere_vue, avant_tete_vue):
        """Passe d'ombrage : lit le G-buffer, écrit t_ombrage (RGBA32F)."""
        ctx = self.ctx
        ctx.disable(moderngl.DEPTH_TEST)
        self.fbo_ombrage.use()
        self.fbo_ombrage.clear(0.0, 0.0, 0.0, 0.0)
        self.t_albedo.use(location=0)
        self.t_normale.use(location=1)
        self.t_profondeur.use(location=2)
        self.t_rampe.use(location=3)
        self.t_masque_sphere.use(location=4)
        self.t_masque_ombre.use(location=5)
        self.t_tangente.use(location=6)
        self.t_masque_cheveux.use(location=7)
        u = self.prog_ombrage
        for nom, unite in (("gAlbedo", 0), ("gNormal", 1), ("gDepth", 2), ("toonRampTex", 3),
                           ("masqueSphere", 4), ("masqueOmbre", 5), ("gTangente", 6),
                           ("masqueCheveux", 7)):
            u[nom].value = unite
        p = self.p_ombrage
        u["tanFov"].value = tuple(float(x) for x in tan_fov)
        u["headCenter"].value = tuple(float(x) for x in centre_tete_vue)
        u["lightDir"].value = _unitaire(lumiere_vue)
        u["headForward"].value = _unitaire(avant_tete_vue)
        u["sphereWeight"].value = float(p.poids_sphere)
        u["faceMaskEnabled"].value = 1.0 if p.masque_visage else 0.0
        u["faceBias"].value = float(p.biais_visage)
        u["rimThreshold"].value = float(p.rim_seuil)
        u["rimSmoothness"].value = float(p.rim_douceur)
        u["rimColor"].value = tuple(float(x) for x in p.rim_couleur)
        u["specularThreshold"].value = float(p.spec_seuil)
        u["specularColor"].value = tuple(float(x) for x in p.spec_couleur)
        u["hairShift"].value = float(p.cheveux_decalage)
        u["hairThreshold"].value = float(p.cheveux_seuil)
        u["hairColor"].value = tuple(float(x) for x in p.cheveux_couleur)
        self.vao_ombrage.render(moderngl.TRIANGLE_STRIP)

    def _passe_contour(self, fbo, pc, t_couleur, t_normale, t_profondeur):
        """Passe contour : fbo <- Sobel(normales, log profondeur) appliqué à t_couleur."""
        fbo.use()
        fbo.clear(0.0, 0.0, 0.0, 1.0)
        t_couleur.use(location=0)
        t_normale.use(location=1)
        t_profondeur.use(location=2)
        c = self.prog_contour
        c["couleur"].value = 0
        c["gNormal"].value = 1
        c["gDepth"].value = 2
        c["texelSize"].value = (1.0 / self.largeur, 1.0 / self.hauteur)
        c["epaisseur"].value = int(pc.epaisseur)
        c["normalThreshold"].value = float(pc.seuil_normale)
        c["depthThreshold"].value = float(pc.seuil_profondeur)
        c["farLog"].value = float(np.log(pc.profondeur_fond))
        c["outlineColor"].value = tuple(float(x) for x in pc.couleur_trait)
        c["backgroundColor"].value = tuple(float(x) for x in pc.couleur_fond)
        self.vao_contour.render(moderngl.TRIANGLE_STRIP)

    def dessiner(self, maillage, *, modele_vue, projection, centre_tete_vue, lumiere_vue,
                 avant_tete_vue, tan_fov, couleur_albedo=(1.0, 1.0, 1.0), albedo=None):
        """Chemin maillage : géométrie -> G-buffer -> ombrage -> contour. Lire avec image_finale()."""
        self.fbo_geo.use()
        self.fbo_geo.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.prog_geo["modelView"].write(_octets_mat(modele_vue))
        self.prog_geo["projection"].write(_octets_mat(projection))
        self.prog_geo["albedoColor"].value = tuple(float(x) for x in couleur_albedo)
        self.prog_geo["albedoTex"].value = 0
        (albedo or self.albedo_defaut).use(location=0)
        maillage.vao.render()

        self._ombrer(tan_fov, centre_tete_vue, lumiere_vue, avant_tete_vue)
        self._passe_contour(self.fbo_final, self.p_contour,
                            self.t_ombrage, self.t_normale, self.t_profondeur)

    def dessiner_gbuffer(self, gbuf, *, tan_fov, centre_tete_vue, lumiere_vue, avant_tete_vue):
        """Chemin 2.5D : G-buffer déjà calculé (dict de relief.composer) -> ombrage -> contour.

        Les masques doivent être définis avant l'appel (definir_masques, definir_masque_cheveux),
        sur la même grille que l'écran, en ordre OpenGL.
        """
        self.t_albedo.write(_vers_rgba(gbuf["albedo"][..., :3]))
        self.t_normale.write(_vers_rgba(gbuf["normale"]))
        prof = np.stack([gbuf["profondeur"], gbuf["uv"][..., 0], gbuf["uv"][..., 1]], axis=-1)
        self.t_profondeur.write(_vers_rgba(prof))
        self.t_tangente.write(_vers_rgba(gbuf["tangente"]))

        self._ombrer(tan_fov, centre_tete_vue, lumiere_vue, avant_tete_vue)
        self._passe_contour(self.fbo_final, self.p_contour,
                            self.t_ombrage, self.t_normale, self.t_profondeur)

    def contour_sur(self, couleur, normale, profondeur, p_contour=None):
        """Passe contour seule sur un G-buffer fourni (tableaux [y, x], ligne 0 en bas).

        Renvoie RGBA float32 (H, W, 4), ligne 0 en bas.
        """
        ctx = self.ctx
        H, W = self.hauteur, self.largeur

        def tex4(arr):
            t = ctx.texture((W, H), 4, data=np.ascontiguousarray(arr, np.float32).tobytes(), dtype="f4")
            t.filter = (moderngl.NEAREST, moderngl.NEAREST)
            t.repeat_x = False
            t.repeat_y = False
            return t

        c = np.zeros((H, W, 4), np.float32)
        c[..., :3] = couleur[..., :3]
        c[..., 3] = 1.0
        n = np.zeros((H, W, 4), np.float32)
        n[..., :3] = normale[..., :3]
        p = np.zeros((H, W, 4), np.float32)
        p[..., 0] = profondeur
        p[..., 3] = 1.0
        t_c, t_n, t_p = tex4(c), tex4(n), tex4(p)
        t_out = ctx.texture((W, H), 4, dtype="f4")
        fbo = ctx.framebuffer(color_attachments=[t_out])
        self._passe_contour(fbo, p_contour or self.p_contour, t_c, t_n, t_p)
        out = np.frombuffer(t_out.read(), np.float32).reshape(H, W, 4).copy()
        for ressource in (t_c, t_n, t_p, t_out, fbo):
            ressource.release()
        return out

    # ---- lecture -----------------------------------------------------------

    def lire_gbuffer(self):
        """G-buffer après dessiner() ou dessiner_gbuffer(), en ordre OpenGL (ligne 0 en bas)."""
        H, W = self.hauteur, self.largeur

        def lire(t):
            return np.frombuffer(t.read(), dtype=np.float32).reshape(H, W, 4)

        prof = lire(self.t_profondeur)
        return {
            "albedo": lire(self.t_albedo)[..., :3].copy(),
            "normale": lire(self.t_normale)[..., :3].copy(),
            "profondeur": prof[..., 0].copy(),
            "uv": prof[..., 1:3].copy(),
            "tangente": lire(self.t_tangente)[..., :3].copy(),
        }

    def lire_ombrage(self):
        """Sortie de la passe d'ombrage avant contour, RGBA float, ligne 0 en bas."""
        return np.frombuffer(self.t_ombrage.read(), np.float32).reshape(self.hauteur, self.largeur, 4)

    def image_finale(self):
        """Image RGBA 8 bits, ligne 0 en haut (prête pour PNG)."""
        arr = np.frombuffer(self.t_final.read(), np.uint8).reshape(self.hauteur, self.largeur, 4)
        return arr[::-1].copy()

    def liberer(self):
        for ressource in (self.t_albedo, self.t_normale, self.t_profondeur, self.t_tangente,
                          self.t_ombrage, self.t_final, self.tampon_z, self.fbo_geo,
                          self.fbo_ombrage, self.fbo_final, self.t_rampe, self.albedo_defaut,
                          self.masque_defaut, self.masque_zero):
            ressource.release()
