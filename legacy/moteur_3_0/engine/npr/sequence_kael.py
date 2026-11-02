"""Séquence de test du personnage réel de Kaël : aller-retour de tête et mesure du scintillement.

La tête fait un balayage monotone de +0,4 à -0,4 rad, sans demi-tour. Chaque image est rendue deux
fois : avec l'encre fine (encre.py) puis avec le contour Sobel d'origine. Un pixel « scintille » si sa
luminance fait deux inversions de sens rapprochées (écart d'au plus deux images, variations
significatives). Sans demi-tour de la tête, un mouvement continu n'en produit pas : une inversion
rapide est donc un clignotement du rendu. (Un aller-retour aurait mêlé les demi-tours au scintillement.)

Usage : python3 engine/npr/sequence_kael.py <dossier_sortie> [nombre_d_images]
Sorties : <dossier>/encre/*.png, <dossier>/sobel/*.png, <dossier>/encre.mp4, <dossier>/sobel.mp4,
<dossier>/metriques.json.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import demo_personnage as DP  # noqa: E402
from npr.chargeur import charger_vue  # noqa: E402
from npr.encre import ParamsEncre  # noqa: E402
from npr.rendu import creer_contexte  # noqa: E402

AMPLITUDE = 0.4              # rad : même plage que la planche
SEUIL_VARIATION = 0.12       # variation de luminance (0..1) jugée significative
ECART_MAX = 2                # inversion rapide : deux variations significatives à au plus deux images d'écart
INVERSIONS_MIN = 2           # un pixel scintille à partir de deux inversions rapides
SEUIL_SOMBRE = 0.25          # pixels « traits » : sombres dans au moins une image
FPS = 12


def inclinaisons(n):
    """Inclinaison de tête (rad) de chaque image : balayage monotone de +A à -A, sans demi-tour."""
    return np.linspace(AMPLITUDE, -AMPLITUDE, n)


def luminance(img_rgb):
    """Luminance 0..1 (H, W) d'une image RGB uint8 ou float."""
    a = np.asarray(img_rgb, np.float32)
    if a.max() > 1.0:
        a = a / 255.0
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def scintillement(lums, seuil=SEUIL_VARIATION, ecart_max=ECART_MAX, inversions_min=INVERSIONS_MIN):
    """Masque (H, W) bool des pixels qui scintillent. lums : (N, H, W) luminance 0..1, par image.

    Pour chaque pixel, on ne retient que les variations d'une image à la suivante d'au moins `seuil`.
    Une inversion rapide : deux variations significatives de sens contraire, séparées d'au plus
    `ecart_max` images. Un pixel scintille s'il en a au moins `inversions_min`.
    """
    lums = np.asarray(lums, np.float32)
    if lums.ndim != 3 or lums.shape[0] < 2:
        raise ValueError("il faut une séquence (N >= 2, H, W)")
    dernier = np.zeros(lums.shape[1:], np.int8)
    t_dernier = np.full(lums.shape[1:], -10 ** 6, np.int64)
    rapides = np.zeros(lums.shape[1:], np.int32)
    for t in range(lums.shape[0] - 1):
        dt = lums[t + 1] - lums[t]
        s = np.where(dt >= seuil, 1, np.where(dt <= -seuil, -1, 0)).astype(np.int8)
        nz = s != 0
        inversion = nz & (dernier != 0) & (s != dernier) & ((t - t_dernier) <= ecart_max)
        rapides += inversion
        dernier = np.where(nz, s, dernier)
        t_dernier = np.where(nz, t, t_dernier)
    return rapides >= inversions_min


def mesurer(lums):
    """Nombres à rapporter : pixels sombres, pixels qui scintillent parmi eux, et leur fraction."""
    sombres = (lums < SEUIL_SOMBRE).any(axis=0)
    scint = scintillement(lums) & sombres
    n_sombres = int(sombres.sum())
    n_scint = int(scint.sum())
    return {
        "pixels_sombres": n_sombres,
        "pixels_scintillants": n_scint,
        "fraction_scintillante": round(n_scint / max(n_sombres, 1), 5),
    }


def encoder(dossier, sortie):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", str(dossier / "%03d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(sortie)], check=True)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    sortie = Path(argv[1])
    n = int(argv[2]) if len(argv) > 2 else 25
    sortie.mkdir(parents=True, exist_ok=True)
    ctx = creer_contexte()
    if ctx is None:
        print("Aucun contexte OpenGL disponible.")
        return 1
    print("OpenGL :", ctx.info["GL_RENDERER"])
    vue = charger_vue(DP.KAEL / DP.FICHIERS[0.0])
    calques, _ = DP.construire_vue(vue)
    resultats = {}
    for nom, encre in (("encre", ParamsEncre()), ("sobel", None)):
        dossier = sortie / nom
        dossier.mkdir(parents=True, exist_ok=True)
        images = []
        for i, tilt in enumerate(inclinaisons(n)):
            img = DP.rendre(ctx, vue, calques, float(tilt), encre=encre)
            cv2.imwrite(str(dossier / f"{i:03d}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            images.append(luminance(img))
        lums = np.stack(images)
        resultats[nom] = mesurer(lums)
        encoder(dossier, sortie / f"{nom}.mp4")
        print(nom, resultats[nom])
    (sortie / "metriques.json").write_text(json.dumps(resultats, indent=2, ensure_ascii=False))
    print("séquence :", sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
