"""Adaptateur de génération : appelle Ara 3D Gen (MIT) pour produire un personnage FBX.

Ara est une dépendance EXTERNE, isolée, non copiée dans le moteur :
 - dépôt : variable d'environnement ARA_REPO (défaut : clone de travail) ;
 - sortie : dossier donné, avec un fichier de provenance (commit du dépôt, licence, preset, date) ;
 - licences : code MIT (© 2026 Josh Ola et contributeurs) ; données de personnage CC0 (MakeHuman) ;
   clips de mouvement issus de CMU : aucun clip n'est utilisé ici (export statique seulement).
Le FBX produit est ensuite traité par le même importeur que les personnages externes (diagnostic.py).
Usage : python3 engine/generation/ara_adapter.py "Athletic woman" SORTIE_DIR
"""
import json, os, subprocess, sys, time

ARA_REPO = os.environ.get("ARA_REPO", "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/ara3dgen/repo")


def _commit(repo):
    try:
        return subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=20).stdout.strip() or "inconnu"
    except Exception:
        return "inconnu"


def generer(preset, sortie_dir, formats="fbx"):
    """Génère un personnage Ara ; renvoie le chemin du FBX et écrit la provenance. Lève une erreur si échec."""
    if not os.path.isdir(ARA_REPO):
        raise RuntimeError(f"dépôt Ara introuvable : {ARA_REPO} (définir ARA_REPO ou cloner olatunde85/3d-gen)")
    os.makedirs(sortie_dir, exist_ok=True)
    t0 = time.time()
    r = subprocess.run(["npx", "tsx", "scripts/export-cli.ts", "--preset", preset, "--out", sortie_dir, "--formats", formats],
                       cwd=ARA_REPO, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError("échec de l'export Ara : " + (r.stderr or r.stdout)[-800:])
    nom = preset.replace(" ", "_")
    fbx = os.path.join(sortie_dir, nom + ".fbx")
    if not os.path.isfile(fbx):
        raise RuntimeError(f"FBX attendu absent : {fbx}")
    prov = {"generateur": "Ara 3D Gen", "depot": "olatunde85/3d-gen", "commit": _commit(ARA_REPO),
            "licence_code": "MIT", "licence_donnees": "CC0 (MakeHuman)", "preset": preset,
            "duree_s": round(time.time() - t0, 2), "fichier": fbx, "sortie_stdout": r.stdout[-400:]}
    json.dump(prov, open(os.path.join(sortie_dir, "provenance.json"), "w"), indent=2, ensure_ascii=False)
    return fbx


if __name__ == "__main__":
    print(generer(sys.argv[1], sys.argv[2]))
