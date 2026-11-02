"""Parseur Fountain (sous-ensemble) vers un JSON de plan.

Règles suivies (spécification officielle, https://fountain.io/syntax) :
- en-têtes de scène : INT, EXT, EST, I/E, INT./EXT, INT/EXT, EXT./INT, séparateur '.' ou espace,
  forçage par '.' en tête, numéro de scène entre '#', tiret séparant lieu et moment ;
- personnages : ligne en majuscules avec au moins une lettre, extension entre parenthèses,
  forçage par '@' en tête ;
- parenthèses dans un dialogue ; notes [[ ]] et commentaires /* */ retirés ;
- transitions forcées par '>' en tête ; métadonnée Title: en tête.

Écarts volontaires (lecture plus souple) : une ligne en majuscules finissant par ':'
(ex. « FADE IN: ») est une transition même sans « TO: ». Les lignes continuées de la
page de titre (indentées) ne sont pas lues.

Usage : python3 engine/script/fountain.py <script.fountain> <sortie.json>
"""
import json
import re
import sys

RE_ENTETE = re.compile(r"^(INT\./EXT|INT/EXT|EXT\./INT|I/E|INT|EXT|EST)(\.|\s)\s*(.+)$", re.I)
RE_NUMERO = re.compile(r"\s*#[^#]+#\s*$")
RE_TRANSITION = re.compile(r"^[A-Z0-9 .'\-/]+:$|^FADE (IN|OUT)\.?$|^CUT TO:$")
RE_PERSONNAGE = re.compile(r"^[A-ZÀ-ÖØ-Þ0-9][A-ZÀ-ÖØ-Þ0-9 .'\-]*[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9 .'\-]*(\s*\(.*\))?$")
RE_PARENTHESE = re.compile(r"^\(.*\)$")


def _nettoyer(texte):
    texte = re.sub(r"/\*.*?\*/", "", texte, flags=re.S)
    texte = re.sub(r"\[\[.*?\]\]", "", texte, flags=re.S)
    return texte


def _entete_scene(ligne):
    """Renvoie (type, lieu, moment) si la ligne est un en-tête de scène, sinon None."""
    forcee = ligne.startswith(".") and not ligne.startswith("..")
    if forcee:
        ligne = ligne[1:]
    ligne = RE_NUMERO.sub("", ligne).strip()
    m = RE_ENTETE.match(ligne)
    if not m and not forcee:
        return None
    if m:
        type_, reste = m.group(1).upper(), m.group(3)
    else:
        type_, reste = "", ligne
    lieu, _, moment = reste.partition(" - ")
    return type_, lieu.strip(), moment.strip()


def parser(texte):
    lignes = [l.rstrip() for l in _nettoyer(texte).splitlines()]
    titre = None
    scenes = []
    scene = None
    transitions_debut = []
    i = 0
    while i < len(lignes) and re.match(r"^[A-Za-z ]+:\s*", lignes[i]):
        cle, _, val = lignes[i].partition(":")
        if cle.strip().lower() == "title":
            titre = val.strip()
        i += 1
    dernier_perso = None

    def scene_courante():
        nonlocal scene
        if scene is None:
            scene = {"id": "s00", "type": "", "lieu": "", "moment": "", "elements": []}
            scenes.append(scene)
        return scene

    while i < len(lignes):
        l = lignes[i].strip()
        i += 1
        if not l:
            dernier_perso = None
            continue
        entete = _entete_scene(l)
        if entete is not None:
            type_, lieu, moment = entete
            scene = {"id": "s%02d" % (len(scenes) + 1), "type": type_, "lieu": lieu,
                     "moment": moment, "elements": []}
            scenes.append(scene)
            dernier_perso = None
            continue
        if l.startswith(">"):
            cible = scene_courante()["elements"] if scene is not None else transitions_debut
            cible.append({"type": "transition", "texte": l[1:].strip()})
            dernier_perso = None
            continue
        if dernier_perso is None and l.isupper() and RE_TRANSITION.match(l):
            cible = scene_courante()["elements"] if scene is not None else transitions_debut
            cible.append({"type": "transition", "texte": l})
            continue
        if dernier_perso is None:
            nom = None
            if l.startswith("@"):                       # personnage forcé, casse conservée
                nom = re.sub(r"\s*\(.*\)$", "", l[1:]).strip()
            elif l.isupper() and RE_PERSONNAGE.match(l):
                nom = re.sub(r"\s*\(.*\)$", "", l).strip()
            if nom:
                dernier_perso = {"type": "dialogue", "personnage": nom, "parentheses": [], "texte": []}
                scene_courante()["elements"].append(dernier_perso)
                continue
        if dernier_perso is not None:
            if RE_PARENTHESE.match(l):
                dernier_perso["parentheses"].append(l.strip("()"))
            else:
                dernier_perso["texte"].append(l)
            continue
        scene_courante()["elements"].append({"type": "action", "texte": l})
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
