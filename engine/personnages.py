"""Registre des personnages du moteur. Un personnage n'est utilisé qu'après contrôle (voir APPRENTISSAGE.md, section 11).

Chaque entrée : fichier source (dossier assets/mixamo ou assets/), squelette, variantes (teinte, taille).
"""
REGISTRE = {
    "maria": {
        "source": "mixamo/Personnage_Maria.fbx",
        "squelette": "mixamo",
        "etat": "contrôlé (combat, marche, victoire)",
        "variantes": {
            "originale": {"teinte": None, "taille_m": 1.75},
            "bleue": {"teinte": (0.62, 0.8, 1.0), "taille_m": 1.75},
        },
    },
    "guerrier": {
        "source": "guerrier_rig.blend",
        "squelette": "rigify",
        "etat": "test seulement : pose de course non validée",
        "variantes": {},
    },
}


def personnage(nom, variante="originale"):
    if nom not in REGISTRE:
        raise KeyError(f"Personnage « {nom} » absent du registre : le créer et le contrôler d'abord.")
    entree = REGISTRE[nom]
    if entree["etat"].startswith("test"):
        raise ValueError(f"Personnage « {nom} » non contrôlé : utilisation refusée.")
    return entree["variantes"][variante]
