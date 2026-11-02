"""Actions : lecture de l'action JSON, clés avec ease, cadence tenue, ressorts amortis (cape, cheveux)."""
import json
from pathlib import Path

import numpy as np

FORMAT_ACTION = "moteur-animation/action-1"


def charger(chemin):
    a = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if a.get("format") != FORMAT_ACTION:
        raise ValueError(f"format d'action inattendu : {a.get('format')!r}")
    if a["mode"] != "deformation":
        raise ValueError("ce moteur ne lit que le mode 'deformation' pour l'instant")
    return a


def cle_valeur(cles, frame):
    """Valeur interpolée entre clés {frame, valeur} avec ease-in-out (smoothstep), tenue hors des bornes."""
    cles = sorted(cles, key=lambda c: c["frame"])
    if frame <= cles[0]["frame"]:
        return float(cles[0]["valeur"])
    if frame >= cles[-1]["frame"]:
        return float(cles[-1]["valeur"])
    for a, b in zip(cles, cles[1:]):
        if a["frame"] <= frame <= b["frame"]:
            s = (frame - a["frame"]) / (b["frame"] - a["frame"])
            s = s * s * (3 - 2 * s)
            return float(a["valeur"] + s * (b["valeur"] - a["valeur"]))
    raise AssertionError("frame non couverte")  # pragma: no cover


def pas_tenu(action):
    """Nombre de frames par dessin (cadence) : les paramètres ne changent qu'à ces instants."""
    return int(action["cadence"]["frames_par_dessin"])


def piste(action, cible, parametre):
    for p in action["pistes"]:
        if p["cible"] == cible and p["parametre"] == parametre:
            return p
    return None


def ressort(entree, raideur, amortissement, gain_px, retard_pas=0):
    """Ressort amorti discret sur une suite d'entrées (une par dessin).

    x'' = -k x - c x' + u(n - retard). k = raideur * 0.0025 ; c = amortissement ; sortie = gain_px * x.
    Le retard est en dessins : la cape réagit après le corps, comme le demande le mouvement secondaire.
    """
    k = float(raideur) * 0.0025
    c = float(amortissement)
    u = np.asarray(entree, np.float64)
    if retard_pas > 0:
        u = np.concatenate([np.zeros(retard_pas), u[:-retard_pas]]) if retard_pas < len(u) else np.zeros_like(u)
    x = v = 0.0
    sortie = np.empty(len(u))
    for n in range(len(u)):
        acc = -k * x - c * v + u[n]
        v += acc
        x += v
        sortie[n] = x
    return gain_px * sortie


def series(action):
    """Séries par dessin (une valeur par dessin, sur la durée de l'action) : yaw, respiration, cape, cheveux (px)."""
    tenue = pas_tenu(action)
    n_pas = int(np.ceil(action["duree_frames"] / tenue))
    frames = np.arange(n_pas) * tenue
    yaw_p = piste(action, "tete", "yaw_deg")
    yaw = np.array([cle_valeur(yaw_p["cles"], f) for f in frames]) if yaw_p else np.zeros(n_pas)

    resp_p = piste(action, "torso", "respiration") or piste(action, "torse", "respiration")
    resp = np.zeros(n_pas)
    if resp_p:
        resp = resp_p["amplitude"] * np.sin(2 * np.pi * frames / resp_p["periode_frames"])

    # entrée des ressorts : vitesse de rotation de la tête (fraction de 45° par dessin), donc le mouvement suit le yaw
    vitesse = np.diff(np.concatenate([[0.0], yaw])) / 45.0
    cape_p = piste(action, "cape", "mouvement_secondaire")
    cheveux_p = piste(action, "cheveux", "mouvement_secondaire")
    cape = cheveux = np.zeros(n_pas)
    if cape_p:
        cape = ressort(vitesse, cape_p["ressort"]["raideur"], cape_p["ressort"]["amortissement"],
                       gain_px=14.0, retard_pas=int(cape_p["retard_dessins"]))
    if cheveux_p:
        cheveux = ressort(vitesse, cheveux_p["ressort"]["raideur"], cheveux_p["ressort"]["amortissement"],
                          gain_px=5.0, retard_pas=int(cheveux_p["retard_dessins"]))
    return {"yaw": yaw, "respiration": resp, "cape": cape, "cheveux": cheveux, "tenue": tenue, "frames": frames}
