"""Validation du JSON de plan (format monteur/plan/1). Voir docs/schema_plan.md."""

TYPES_ELEMENT = {"action", "dialogue", "transition"}


def valider(plan):
    """Renvoie la liste des erreurs (vide = plan valide)."""
    erreurs = []
    if not isinstance(plan, dict):
        return ["le plan doit être un objet JSON"]
    if plan.get("format") != "monteur/plan/1":
        erreurs.append("format inconnu : %r" % plan.get("format"))
    if not isinstance(plan.get("titre"), str) or not plan.get("titre"):
        erreurs.append("titre manquant")
    if not isinstance(plan.get("transitions_debut"), list):
        erreurs.append("transitions_debut doit être une liste")
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        erreurs.append("scenes doit être une liste non vide")
        return erreurs
    ids = set()
    for s in scenes:
        sid = s.get("id")
        if not sid or sid in ids:
            erreurs.append("id de scène manquant ou en double : %r" % sid)
        ids.add(sid)
        if not s.get("lieu") and sid != "s00":
            erreurs.append("%s : lieu manquant" % sid)
        for k, e in enumerate(s.get("elements", [])):
            t = e.get("type")
            if t not in TYPES_ELEMENT:
                erreurs.append("%s[%d] : type inconnu %r" % (sid, k, t))
                continue
            if t == "dialogue":
                if not e.get("personnage"):
                    erreurs.append("%s[%d] : dialogue sans personnage" % (sid, k))
                if not e.get("texte"):
                    erreurs.append("%s[%d] : dialogue vide" % (sid, k))
                if not isinstance(e.get("parentheses"), list):
                    erreurs.append("%s[%d] : parentheses doit être une liste" % (sid, k))
            elif not e.get("texte"):
                erreurs.append("%s[%d] : %s vide" % (sid, k, t))
    return erreurs
