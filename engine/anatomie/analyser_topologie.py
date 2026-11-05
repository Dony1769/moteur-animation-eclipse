"""Classification anatomique d'une armature SANS utiliser les noms des os (phase 4, étape 1).

Entrée : la sortie JSON de extraire_squelette.py (hiérarchie, têtes, queues, longueurs fiables).
Méthode :
1. Segments : chaîne d'os où chaque os n'a qu'un enfant ; une jonction (os à plusieurs enfants) ouvre de nouveaux
   segments. Le segment racine contient l'os sans parent.
2. Tronc : le segment fils de la racine dont l'extrémité est la plus haute (géométrie).
3. Jambes : fils de la racine dont l'extrémité est plus basse que le départ (descend).
4. Cou / épaules : fils du segment supérieur du tronc. Le cou est le fils le plus central (|x| minimal) ; les
   autres sont des épaules, côté gauche/droit selon le signe de x par rapport à la ligne médiane.
5. Bras : segment de l'épaule jusqu'à la première jonction (la main, à partir de laquelle les doigts commencent).
Tout ce qui ne rentre pas dans ces règles est listé dans « ambigus » au lieu d'être deviné.

Sortie : dictionnaire de régions (noms d'os réels, longueurs réelles) et liste des ambiguïtés.
La vérification par les noms est faite à part (test_analyse_topologie.py), jamais dans la classification.
"""
import json

import numpy as np


def _segments(os_par_nom):
    """Découpe l'arbre en segments (listes de noms d'os) : une jonction ferme le segment."""
    enfants = {n: o["enfants"] for n, o in os_par_nom.items()}
    racines = [n for n, o in os_par_nom.items() if o["parent"] is None]
    segments = []

    def suivre(depart):
        seg = [depart]
        courant = depart
        while len(enfants[courant]) == 1:
            courant = enfants[courant][0]
            seg.append(courant)
        segments.append(seg)
        for e in enfants[courant]:
            suivre(e)

    for r in racines:
        suivre(r)
    return segments


def analyser(json_entree):
    d = json.load(open(json_entree, encoding="utf-8"))
    os_liste = d["os"]
    par = {o["nom"]: o for o in os_liste}
    avertissements = []
    ambigus = []

    segs = _segments(par)
    if len(segs) < 2:
        raise ValueError("squelette sans structure de jonction exploitable")
    racine = segs[0][0]
    seg_racine = segs[0]  # le premier segment contient la racine seule (cas d'un bassin à plusieurs enfants)
    fils_racine = [s for s in segs if s[0] in par[racine]["enfants"]]

    def fin(seg):
        return np.array(par[seg[-1]]["queue"])

    def debut(seg):
        return np.array(par[seg[0]]["tete"])

    # Tronc = fils de la racine dont l'extrémité est la plus haute.
    if not fils_racine:
        raise ValueError("la racine n'a aucun enfant")
    tronc = max(fils_racine, key=lambda s: fin(s)[2])
    # Jambes = autres fils qui descendent (fin plus basse que le départ).
    jambes = [s for s in fils_racine if s is not tronc and fin(s)[2] < debut(s)[2]]
    autres_racine = [s for s in fils_racine if s is not tronc and s not in jambes]
    for s in autres_racine:
        ambigus.append({"segment": s, "raison": "fils de la racine ni tronc ni jambe"})

    # Jambes : deux côtés repérés par x (côté x_min / x_max). Le nom « gauche/droite » est une convention de
    # nommage ; il n'est pas déduit ici, il est seulement vérifié dans le test à partir des noms.
    if len(jambes) == 2:
        jambes = sorted(jambes, key=lambda s: debut(s)[0])
        cote_jambes = {"x_min": jambes[0], "x_max": jambes[1]}
    else:
        avertissements.append(f"{len(jambes)} jambe(s) trouvée(s) au lieu de 2")
        cote_jambes = {}

    # Sommet du tronc : dernier segment du tronc, sa fin est une jonction (cou + épaules).
    dernier = tronc[-1]
    fils_haut = par[dernier]["enfants"]
    if len(fils_haut) < 2:
        avertissements.append("le sommet du tronc n'a pas de jonction (épaules/cou non trouvés)")
    epaules = []
    cou = None
    if fils_haut:
        seg_haut = [s for s in segs if s[0] in fils_haut]
        # Le cou mène à la tête : c'est le fils dont l'extrémité est la plus haute.
        cou = max(seg_haut, key=lambda s: fin(s)[2])
        # Épaules = autres fils de deux os ou plus (épaule + bras). Un segment d'un seul os est un auxiliaire :
        # signalé, non classé.
        epaules = []
        for s in seg_haut:
            if s is cou:
                continue
            if len(s) >= 2:
                epaules.append(s)
            else:
                ambigus.append({"segment": s, "raison": "segment d'un seul os attaché au haut du tronc (auxiliaire ?)"})

    regions = {
        "racine": seg_racine,
        "tronc": tronc,
        "cou": cou,
        "jambes": cote_jambes,
        "epaules": epaules,
    }
    # Jambe = thigh / shank / pied / orteils (longueurs réelles des os fiables).
    detail = {}
    for cote, seg in cote_jambes.items():
        detail[cote] = {"segment": seg, "longueurs": [round(par[n]["longueur"], 6) for n in seg],
                        "fiable": [par[n]["longueur_fiable"] for n in seg]}
    return {
        "racine": racine,
        "regions": {k: v for k, v in regions.items()},
        "jambes_detail": detail,
        "ambigus": ambigus,
        "avertissements": avertissements,
        "unite": d["unite"],
    }


if __name__ == "__main__":
    import sys
    r = analyser(sys.argv[1])
    print(json.dumps({k: v for k, v in r.items() if k != "regions"}, ensure_ascii=False, indent=1))
    for k, v in r["regions"].items():
        if isinstance(v, dict):
            print(k, {c: s for c, s in v.items()})
        else:
            print(k, v if v is None else v[:6])


def representation(json_entree, npz_entree):
    """Représentation anatomique exploitable (sans noms dans la logique) : articulations, longueurs réelles,
    os dominants par région et mesures d'échelle. Les valeurs absentes sont mises à None et listées."""
    r = analyser(json_entree)
    d = json.load(open(json_entree, encoding="utf-8"))
    z = np.load(npz_entree)
    sommets, poids, noms = z["sommets"], z["poids"], [str(n) for n in z["noms_os"]]
    par = {o["nom"]: o for o in d["os"]}
    manquant = []

    def tete(n):
        return np.array(par[n]["tete"])

    def tronc_articulations():
        return [s[0] for s in r["regions"]["tronc"]]

    # Articulations : tête du premier os de chaque segment (point de pivot réel de la chaîne).
    jambes = r["regions"]["jambes"]
    articulations = {}
    for cote, seg in jambes.items():
        articulations[f"hanche_{cote}"] = tete(seg[0]).tolist()
        articulations[f"genou_{cote}"] = tete(seg[1]).tolist() if len(seg) > 1 else None
        articulations[f"cheville_{cote}"] = tete(seg[2]).tolist() if len(seg) > 2 else None
        if len(seg) < 3:
            manquant.append(f"articulation de cheville {cote} absente")
    articulations["racine"] = tete(r["racine"]).tolist()

    # Longueurs réelles (fiables seulement) : cuisse, jambe, tronc, cou.
    def longueur(n):
        o = par[n]
        return o["longueur"] if o["longueur_fiable"] else None

    mesures = {}
    xmin, xmax = jambes.get("x_min"), jambes.get("x_max")
    if xmin and xmax:
        mesures["largeur_hanches"] = float(np.linalg.norm(tete(xmin[0]) - tete(xmax[0])))
        mesures["cuisse"] = {c: longueur(s[0]) for c, s in jambes.items()}
        mesures["jambe"] = {c: longueur(s[1]) if len(s) > 1 else None for c, s in jambes.items()}
    mesures["tronc_bassin_au_cou"] = float(np.sum([longueur(n) or 0 for n in r["regions"]["tronc"]])) \
        if all(longueur(n) is not None for n in r["regions"]["tronc"]) else None
    if mesures["tronc_bassin_au_cou"] is None:
        manquant.append("longueur du tronc non fiable (os terminal dans le tronc)")

    # Os dominant par sommet (argmax des poids) -> région par appartenance au segment.
    seg_de = {r["racine"]: "bassin"}
    for cote, seg in jambes.items():
        for n in seg:
            seg_de[n] = f"jambe_{cote}"
    for n in r["regions"]["tronc"]:
        seg_de[n] = "tronc"
    for n in (r["regions"]["cou"] or []):
        seg_de[n] = "cou_tete"
    bras = sorted(r["regions"]["epaules"], key=lambda s: tete(s[0])[0])
    for k, s in enumerate(bras):
        for n in s:
            seg_de[n] = f"bras_{'x_min' if k == 0 else 'x_max'}"
    if poids.shape[0]:
        dom = poids.argmax(axis=1)
        valide = poids.sum(axis=1) > 0
        region_os = np.array([seg_de.get(noms[i], "non_classe") for i in range(len(noms))])
        region_sommet = np.where(valide, region_os[dom], "sans_poids")
        comptes = {k: int((region_sommet == k).sum()) for k in np.unique(region_sommet)}
    else:
        comptes = {}
        manquant.append("pas de poids : régions de sommets non calculées")

    return {
        "nb_os_total": d["nb_os"],
        "nb_os_avec_poids": int((poids.sum(axis=0) > 0).sum()) if poids.size else 0,
        "articulations_m": articulations,
        "mesures_m": mesures,
        "regions": {k: ([n for n in v] if isinstance(v, list) else v) for k, v in r["regions"].items()
                    if k != "jambes"},
        "jambes_cote": {c: s for c, s in jambes.items()},
        "vertices_par_region_dominante": comptes,
        "ambigus": r["ambigus"],
        "absent_ou_ambigu": manquant + r["avertissements"],
        "unite": r["unite"],
    }
