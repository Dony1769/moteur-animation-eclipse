"""Planificateur de budget de calcul pour un épisode (CPU ou GPU Kaggle).

Usage : python3 budget/plan.py --duree 480 --fps 12 --profil cpu [--budget 5400]
Choisit le réglage le plus élevé (définition, puis échantillons) qui tient le budget. Si rien ne tient, ne
lance rien et l'écrit dans docs/budget.md.
"""
import argparse
import pathlib

# temps par image mesurés (secondes), décor corrigé, débruitage OpenImageDenoise
MESURES = {
    "cpu": [
        # (largeur, hauteur, échantillons, secondes par image)
        (1280, 540, 16, 39.2),
        (960, 405, 8, 13.0),
        (640, 270, 8, 6.1),
        (640, 270, 4, 4.0),
    ],
    # pas encore mesuré : rempli quand l'utilisateur colle les résultats du notebook Kaggle
    # Colab T4 (OptiX), run du notebook du 3 novembre 2026, décor seul ; inclut le démarrage de Blender à chaque réglage
    "gpu-colab": [(1280, 540, 16, 19.6), (960, 405, 8, 11.5), (640, 270, 8, 5.3), (640, 270, 4, 5.3)],
}

REGLAGES_PAR_PRIORITE = sorted(MESURES["cpu"], key=lambda r: (r[0] * r[1], r[2]), reverse=True)


def plan(duree_s, fps, profil, budget_s=5400):
    images = int(round(duree_s * fps))
    mesures = MESURES.get(profil, [])
    if not mesures:
        return {"ok": False, "raison": f"aucune mesure pour le profil « {profil} »", "images": images}
    lignes = []
    retenu = None
    for largeur, hauteur, spp, par_image in sorted(mesures, key=lambda r: (r[0] * r[1], r[2]), reverse=True):
        total = par_image * images
        lignes.append({"reglage": f"{largeur}x{hauteur} {spp} ech.", "par_image_s": par_image,
                       "total_s": round(total), "tient": total <= budget_s})
        if retenu is None and total <= budget_s:
            retenu = lignes[-1]
    return {"ok": retenu is not None, "images": images, "retenu": retenu, "lignes": lignes}


def ecrire_budget(resultats):
    chemin = pathlib.Path(__file__).resolve().parent.parent / "docs" / "budget.md"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("a") as f:
        f.write("\n## Résultat du planificateur\n")
        for titre, r in resultats:
            f.write(f"\n### {titre}\n")
            f.write(f"- images : {r['images']}\n")
            if not r["ok"] and r.get("retenu") is None and "raison" in r:
                f.write(f"- rien ne lance : {r['raison']}\n")
                continue
            for l in r["lignes"]:
                f.write(f"- {l['reglage']} : {l['par_image_s']} s/image, total {l['total_s']} s, "
                        f"{'tient' if l['tient'] else 'dépasse'} le budget\n")
            if r["ok"]:
                f.write(f"- réglage retenu : {r['retenu']['reglage']}\n")
            else:
                f.write("- aucun réglage ne tient : rien n'est lancé\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--duree", type=float, required=True)
    p.add_argument("--fps", type=int, choices=(12, 24), required=True)
    p.add_argument("--profil", choices=sorted(MESURES), default="cpu")
    p.add_argument("--budget", type=float, default=5400)
    a = p.parse_args()
    r = plan(a.duree, a.fps, a.profil, a.budget)
    print(f"images {r['images']}")
    for l in r.get("lignes", []):
        print(f"{l['reglage']} : {l['par_image_s']} s/image, total {l['total_s']} s, "
              f"{'tient' if l['tient'] else 'dépasse'}")
    if r["ok"]:
        print("RETENU", r["retenu"]["reglage"])
    else:
        print("RIEN_NE_TIENT : aucun lancement")
    return r


if __name__ == "__main__":
    main()
