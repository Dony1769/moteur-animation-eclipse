"""Génère les lieux d'un univers à partir de universes/<slug>/universe.json.

Usage :
    HF_TOKEN=... python3 tools/make_universe.py eclipse_royale              # tous les lieux « a_generer »
    HF_TOKEN=... python3 tools/make_universe.py eclipse_royale --id salle_du_trone
    python3 tools/make_universe.py eclipse_royale --dry-run                 # affiche les prompts seulement

Chaque lieu est rendu avec le préfixe de style de l'univers, un graine fixe (même décor à chaque relance)
et le format 16:9. Le manifeste est mis à jour : statut « genere » et chemin de l'image.
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hf_client  # noqa: E402

SPACE = "mcp-tools/Qwen-Image"
ENDPOINT = "/generate_image"


def seed_de(texte):
    return int(hashlib.sha256(texte.encode()).hexdigest()[:8], 16) % 2_000_000_000


def prompt_lieu(univers, lieu):
    st = univers["style"]
    return ", ".join(p for p in [st["prefixe_prompt"], lieu["prompt"], lieu.get("lumiere", "")] if p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("univers")
    ap.add_argument("--id", action="append", help="ne générer que ce lieu (répétable)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    dossier = os.path.join(BASE, "universes", a.univers)
    chemin = os.path.join(dossier, "universe.json")
    univers = json.load(open(chemin, encoding="utf-8"))

    cibles = [l for l in univers["lieux"]
              if (a.id and l["id"] in a.id) or (not a.id and l["statut"] == "a_generer")]
    if not cibles:
        print("Rien à générer.")
        return

    for lieu in cibles:
        prompt = prompt_lieu(univers, lieu)
        if a.dry_run:
            print("[%s]\n  %s\n  négatif : %s\n" % (lieu["id"], prompt, univers["style"]["a_eviter"]))
            continue
        seed = seed_de(univers["slug"] + lieu["id"])
        print("génération de %s (graine %d)..." % (lieu["id"], seed))
        res = hf_client.call(SPACE, ENDPOINT, [prompt, seed, False, univers["format_image"],
                                              univers["style"]["a_eviter"], 4.0, 16])
        url = res[0]["url"]
        import io
        import urllib.request
        from PIL import Image
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=hf_client.headers_auth()), timeout=120).read()
        sortie = os.path.join(dossier, lieu["image"] or ("locations/%s.png" % lieu["id"]))
        os.makedirs(os.path.dirname(sortie), exist_ok=True)
        Image.open(io.BytesIO(raw)).convert("RGB").save(sortie)
        lieu["statut"], lieu["image"] = "genere", os.path.relpath(sortie, dossier)
        print("  -> %s (%s)" % (sortie, res[2] if len(res) > 2 else ""))

    if not a.dry_run:
        json.dump(univers, open(chemin, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("manifeste mis à jour :", chemin)


if __name__ == "__main__":
    main()
