"""Parseur Fountain (sous-ensemble) vers un JSON de plan.

Gère : titre, en-têtes de scène (INT./EXT.), actions, personnages (ligne en MAJUSCULES),
parenthèses, dialogues, transitions (lignes en MAJUSCULES finissant par ':' ou « FADE »),
commentaires /* */ et [[ ]].

Usage : python3 engine/script/fountain.py <script.fountain> <sortie.json>
"""
import json
import re
import sys

RE_SCENE = re.compile(r"^(INT\.|EXT\.|INT\./EXT\.|EXT\./INT\.|I/E\.)\s+(.+?)(?:\s*-\s*(.+))?$")
RE_TRANSITION = re.compile(r"^[A-Z ]+(TO|IN|OUT|FADE)[A-Z ]*:?$|^FADE (IN|OUT)\.?$|^CUT TO:$")
RE_PERSONNAGE = re.compile(r"^[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ .'\-]+(\s*\(.*\))?$")
RE_PARENTHESE = re.compile(r"^\(.*\)$")


def _nettoyer(texte):
    texte = re.sub(r"/\*.*?\*/", "", texte, flags=re.S)
    texte = re.sub(r"\[\[.*?\]\]", "", texte, flags=re.S)
    return texte


def parser(texte):
    texte = _nettoyer(texte)
    lignes = [l.rstrip() for l in texte.splitlines()]
    titre = None
    scenes = []
    scene = None
    i = 0
    # métadonnées de tête
    while i < len(lignes) and re.match(r"^[A-Za-z ]+:\s*", lignes[i]):
        cle, _, val = lignes[i].partition(":")
        if cle.strip().lower() == "title":
            titre = val.strip()
        i += 1
    dernier_perso = None
    transitions_debut = []
    while i < len(lignes):
        l = lignes[i].strip()
        i += 1
        if not l:
            dernier_perso = None
            continue
        m = RE_SCENE.match(l)
        if m:
            scene = {"id": "s%02d" % (len(scenes) + 1), "type": m.group(1).rstrip("."),
                     "lieu": m.group(2).strip(), "moment": (m.group(3) or "").strip(),
                     "elements": []}
            scenes.append(scene)
            dernier_perso = None
            continue
        if RE_TRANSITION.match(l) and l.isupper():
            cible = scene["elements"] if scene is not None else transitions_debut
            cible.append({"type": "transition", "texte": l})
            dernier_perso = None
            continue
        if scene is None:
            scene = {"id": "s00", "type": "", "lieu": "", "moment": "", "elements": []}
            scenes.append(scene)
        if dernier_perso is None and RE_PERSONNAGE.match(l) and l.isupper():
            nom = re.sub(r"\s*\(.*\)$", "", l).strip()
            dernier_perso = {"type": "dialogue", "personnage": nom, "parentheses": [], "texte": []}
            scene["elements"].append(dernier_perso)
            continue
        if dernier_perso is not None:
            if RE_PARENTHESE.match(l):
                dernier_perso["parentheses"].append(l.strip("()"))
            else:
                dernier_perso["texte"].append(l)
            continue
        scene["elements"].append({"type": "action", "texte": l})
    # mise en forme finale des dialogues
    for s in scenes:
        for e in s["elements"]:
            if e["type"] == "dialogue":
                e["texte"] = " ".join(e["texte"])
    return {"format": "monteur/plan/1", "titre": titre,
            "transitions_debut": transitions_debut, "scenes": scenes}


def personnages(plan):
    noms = []
    for s in plan["scenes"]:
        for e in s["elements"]:
            if e["type"] == "dialogue" and e["personnage"] not in noms:
                noms.append(e["personnage"])
    return noms


if __name__ == "__main__":
    entree, sortie = sys.argv[1], sys.argv[2]
    with open(entree, encoding="utf-8") as f:
        plan = parser(f.read())
    from schema import valider
    erreurs = valider(plan)
    if erreurs:
        sys.exit("plan invalide : " + "; ".join(erreurs))
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print("scènes :", len(plan["scenes"]), "| personnages :", personnages(plan))
