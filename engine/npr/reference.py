"""Référence CPU (numpy) des formules des shaders GLSL.

Sert à deux choses : valider les formules mathématiques (tests) et comparer
le résultat GPU pixel par pixel sur un même G-buffer (tests GL).

Conventions (identiques aux shaders) :
- espace vue : caméra à l'origine, regarde vers -Z ; profondeur linéaire d = -z > 0 ;
- G-buffer : albédo RGB, normale vue RAW (fond = 0), profondeur d (fond = 0),
  UV de surface, tangente vue unitaire (zéro = pas de cheveux) ;
- tableaux indexés [y, x] avec y = 0 en bas (ordre de lecture OpenGL) ;
- le texel (x, y) est échantillonné en uv = ((x + 0.5) / W, (y + 0.5) / H).
"""
import numpy as np

from .parametres import ParamsContour, ParamsOmbrage


def normaliser(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)


def demi_lambert(n, l):
    """N·L ramené de [-1, 1] vers [0, 1]."""
    return np.sum(n * l, axis=-1) * 0.5 + 0.5


def indice_rampe(u, n):
    """Texel sélectionné par GL_NEAREST avec GL_CLAMP_TO_EDGE."""
    return np.clip(np.floor(u * n), 0, n - 1).astype(np.int64)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def step(bord, x):
    return (x >= bord).astype(np.float32)


def echantillon_masque(masque, uv):
    """Masque 2D lu en GL_NEAREST aux UV de surface uv (H, W, 2)."""
    Hm, Wm = masque.shape
    cx = np.clip(np.floor(uv[..., 0] * Wm), 0, Wm - 1).astype(np.int64)
    cy = np.clip(np.floor(uv[..., 1] * Hm), 0, Hm - 1).astype(np.int64)
    return masque[cy, cx].astype(np.float32)


def ombrage(albedo, normale, profondeur, uv_surface, rampe_f, p: ParamsOmbrage, tan_fov,
            centre_tete, lumiere, avant_tete, masque_sphere=None, masque_ombre=None,
            tangente=None, masque_cheveux=None):
    """Passe d'ombrage. Renvoie RGBA float32 (H, W, 4) ; le fond vaut 0.

    uv_surface : UV de surface du G-buffer (H, W, 2), utilisées pour lire les masques.
    tan_fov : (tan(fovy/2) * aspect, tan(fovy/2)) ; centre_tete, lumiere, avant_tete :
    vecteurs 3D en espace vue ; lumiere et avant_tete doivent être unitaires.
    tangente, masque_cheveux : sans l'un des deux, pas de reflet de cheveux.
    """
    H, W = profondeur.shape
    ys, xs = np.mgrid[0:H, 0:W]
    ndc = np.stack([(xs + 0.5) / W * 2.0 - 1.0, (ys + 0.5) / H * 2.0 - 1.0], axis=-1)

    d = profondeur[..., None].astype(np.float32)
    pos = np.concatenate([ndc[..., 0:1] * tan_fov[0] * d,
                          ndc[..., 1:2] * tan_fov[1] * d,
                          -d], axis=-1)

    n_brut = normaliser(normale.astype(np.float32))
    n_sph = normaliser(pos - np.asarray(centre_tete, np.float32))

    w = np.ones((H, W), np.float32) if masque_sphere is None else echantillon_masque(masque_sphere, uv_surface)
    w = (w * p.poids_sphere)[..., None]
    n = normaliser(n_brut * (1.0 - w) + n_sph * w)

    L = normaliser(np.asarray(lumiere, np.float32))
    V = normaliser(-pos)

    u = demi_lambert(n, L)
    if p.masque_visage:
        Lb = normaliser(L + np.asarray(avant_tete, np.float32) * p.biais_visage)
        ndlb = demi_lambert(n, Lb)
        m = np.ones((H, W), np.float32) if masque_ombre is None else echantillon_masque(masque_ombre, uv_surface)
        u = 1.0 + (ndlb - 1.0) * m          # mix(1.0, ndlb, m)

    n_rampe = rampe_f.shape[0]
    shade = rampe_f[indice_rampe(np.clip(u, 0.0, 1.0), n_rampe)]
    col = albedo[..., :3].astype(np.float32) * shade

    ndv = np.sum(n * V, axis=-1, keepdims=True)
    ndl = np.sum(n * L, axis=-1, keepdims=True)
    fresnel = 1.0 - np.maximum(ndv, 0.0)
    rim_i = fresnel * np.maximum(ndl, 0.0)
    s = max(p.rim_douceur, 1e-4)
    rim = smoothstep(p.rim_seuil - s, p.rim_seuil + s, rim_i)
    col = col + rim * np.asarray(p.rim_couleur, np.float32)

    H_vec = normaliser(L + V)
    ndh = np.maximum(np.sum(n * H_vec, axis=-1, keepdims=True), 0.0)
    spec = step(p.spec_seuil, ndh)
    col = col + spec * np.asarray(p.spec_couleur, np.float32)

    if tangente is not None and masque_cheveux is not None:
        T = tangente.astype(np.float32)
        valide = (np.linalg.norm(T, axis=-1) > 0.5).astype(np.float32)
        mh = echantillon_masque(masque_cheveux, uv_surface) * valide
        Ts = normaliser(T + n * p.cheveux_decalage)
        th = np.sum(Ts * H_vec, axis=-1)
        sin_th = np.sqrt(np.maximum(0.0, 1.0 - th * th))
        hair = step(p.cheveux_seuil, sin_th) * mh
        col = col + hair[..., None] * np.asarray(p.cheveux_couleur, np.float32)

    col = np.clip(col, 0.0, 1.0)
    fond = profondeur <= 0.0
    out = np.concatenate([col, np.ones((H, W, 1), np.float32)], axis=-1)
    out[fond] = 0.0
    return out


def _voisins(a, k):
    """Les 9 échantillons 3x3 (pas k) avec bord étendu ; indice = (j+1)*3 + (i+1)."""
    H, W = a.shape[:2]
    pad = ((k, k), (k, k)) + ((0, 0),) * (a.ndim - 2)
    P = np.pad(a, pad, mode="edge")
    out = {}
    for j in (-1, 0, 1):
        for i in (-1, 0, 1):
            out[(j + 1) * 3 + (i + 1)] = P[k + j * k: k + j * k + H, k + i * k: k + i * k + W]
    return out


def contour(couleur, normale, profondeur, p: ParamsContour):
    """Passe de contour : Sobel sur normales et sur log(profondeur). RGBA (H, W, 4)."""
    k = int(p.epaisseur)
    H, W = profondeur.shape
    geo = profondeur > 0.0

    nv = _voisins(normale.astype(np.float32), k)
    gx = (nv[2] + 2 * nv[5] + nv[8]) - (nv[0] + 2 * nv[3] + nv[6])
    gy = (nv[6] + 2 * nv[7] + nv[8]) - (nv[0] + 2 * nv[1] + nv[2])
    ed_n = np.linalg.norm(gx, axis=-1) + np.linalg.norm(gy, axis=-1) > p.seuil_normale

    log_f = np.where(geo, np.log(np.maximum(profondeur, 1e-30)), np.log(p.profondeur_fond))
    lv = _voisins(log_f.astype(np.float32), k)
    gxd = (lv[2] + 2 * lv[5] + lv[8]) - (lv[0] + 2 * lv[3] + lv[6])
    gyd = (lv[6] + 2 * lv[7] + lv[8]) - (lv[0] + 2 * lv[1] + lv[2])
    ed_d = np.abs(gxd) + np.abs(gyd) > p.seuil_profondeur

    bord = (ed_n | ed_d) & geo
    out = np.concatenate([couleur[..., :3].astype(np.float32),
                          np.ones((H, W, 1), np.float32)], axis=-1)
    out[bord, :3] = np.asarray(p.couleur_trait, np.float32)
    out[~geo, :3] = np.asarray(p.couleur_fond, np.float32)
    return out
