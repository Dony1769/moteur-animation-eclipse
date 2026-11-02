"""Squelette nommé d'une vue, construit à partir des 133 points détectés (DWPose) et de corrections à la main.

Usage : python3 engine/rig2d/squelette.py <points133.json> <image_vue.png> <sortie.json> [corrections.json]

Les noms suivent le corps : épaule, coude, poignet, doigt (base du majeur), hanche, genou, cheville,
orteil, talon, cou, bassin, tête (sommet) et pointe de cape. Les points 'virtuels' (cou, bassin,
sommet de tête, pointe de cape) sont calculés ou corrigés à la main et marqués ainsi.
"""
import json
import sys

import cv2

# Indices COCO-WholeBody (133 points) : corps, pieds, mains (gauche = 91..111, droite = 112..132)
INDICES = {
    "nez": 0, "oeil_g": 1, "oeil_d": 2,
    "epaule_g": 5, "epaule_d": 6, "coude_g": 7, "coude_d": 8, "poignet_g": 9, "poignet_d": 10,
    "hanche_g": 11, "hanche_d": 12, "genou_g": 13, "genou_d": 14, "cheville_g": 15, "cheville_d": 16,
    "orteil_g": 17, "talon_g": 19, "orteil_d": 20, "talon_d": 22,
    # Doigts : base du majeur (3e articulation), pour attacher la main à l'avant-bras
    "doigt_g": 100, "doigt_d": 121,
    # Pouce et auriculaire (extrémités), utiles pour les mains plus tard
    "pouce_g": 95, "pouce_d": 116, "auriculaire_g": 111, "auriculaire_d": 132,
    # Visage (68 points, indices 23..90) : bouche, paupières, base du nez, pour les expressions et la parole
    "bouche_coin_g": 71, "bouche_coin_d": 77, "levre_haut": 74, "levre_bas": 80,
    # Paupières (coins externes et internes) et base du nez
    "paupiere_ext_g": 65, "paupiere_int_g": 68, "paupiere_ext_d": 59, "paupiere_int_d": 62,
    "nez_base": 56,
}


def charger_points(chemin):
    brut = json.load(open(chemin, encoding="utf-8"))
    return {p["i"]: (p["x"], p["y"], p["s"]) for p in brut}


def construire(points, corrections):
    squelette = {}
    for nom, i in INDICES.items():
        x, y, s = points[i]
        squelette[nom] = {"x": round(x, 1), "y": round(y, 1), "source": "dwpose", "fiabilite": round(s, 2)}
    # Points virtuels : moyennes puis corrections manuelles
    def milieu(a, b):
        return ((squelette[a]["x"] + squelette[b]["x"]) / 2, (squelette[a]["y"] + squelette[b]["y"]) / 2)
    cx, cy = milieu("epaule_g", "epaule_d")
    squelette["cou"] = {"x": cx, "y": cy - 15, "source": "virtuel"}
    bx, by = milieu("hanche_g", "hanche_d")
    squelette["bassin"] = {"x": bx, "y": by, "source": "virtuel"}
    for nom, v in corrections.items():
        squelette[nom] = {"x": v[0], "y": v[1], "source": "corrige_main"}
    return squelette


def superposer(image_bgr, squelette, chemin_sortie):
    dessin = image_bgr.copy()
    liens = [("cou", "bassin"), ("epaule_g", "coude_g"), ("coude_g", "poignet_g"), ("poignet_g", "doigt_g"),
             ("epaule_d", "coude_d"), ("coude_d", "poignet_d"), ("poignet_d", "doigt_d"),
             ("hanche_g", "genou_g"), ("genou_g", "cheville_g"), ("cheville_g", "orteil_g"),
             ("hanche_d", "genou_d"), ("genou_d", "cheville_d"), ("cheville_d", "orteil_d"),
             ("epaule_g", "epaule_d"), ("hanche_g", "hanche_d")]
    for a, b in liens:
        if a in squelette and b in squelette:
            cv2.line(dessin, (int(squelette[a]["x"]), int(squelette[a]["y"])),
                     (int(squelette[b]["x"]), int(squelette[b]["y"])), (0, 0, 255), 2)
    for nom, v in squelette.items():
        couleur = (0, 200, 0) if v["source"] == "dwpose" else (255, 0, 255)
        cv2.circle(dessin, (int(v["x"]), int(v["y"])), 5, couleur, -1)
        cv2.putText(dessin, nom, (int(v["x"]) + 6, int(v["y"]) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                    (0, 0, 0), 1)
    cv2.imwrite(chemin_sortie, dessin)


if __name__ == "__main__":
    points_json, image, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    corr = json.load(open(sys.argv[4], encoding="utf-8")) if len(sys.argv) > 4 else {}
    sq = construire(charger_points(points_json), corr)
    json.dump(sq, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    superposer(cv2.imread(image), sq, sortie.replace(".json", "_superposition.png"))
    print(len(sq), "points ->", sortie)
