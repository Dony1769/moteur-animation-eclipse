"""Client commun pour les Spaces Gradio Hugging Face.

Le jeton n'est jamais écrit dans un fichier : il vient de la variable d'environnement HF_TOKEN.
Hôte du Space : propriétaire-nom en minuscules, avec / et _ remplacés par -.
"""
import json
import os
import urllib.request


def headers_auth(json_body=True):
    h = {"Content-Type": "application/json"} if json_body else {}
    tok = os.environ.get("HF_TOKEN")
    if tok:
        h["Authorization"] = "Bearer " + tok
    return h


def hote(space):
    return "https://%s.hf.space" % space.replace("/", "-").replace("_", "-").lower()


def call(space, endpoint, data, timeout=300):
    """Appelle un endpoint Gradio et renvoie la liste des sorties (payload « complete »)."""
    base = hote(space) + "/gradio_api/call" + endpoint
    req = urllib.request.Request(base, data=json.dumps({"data": data}).encode(), headers=headers_auth())
    eid = json.load(urllib.request.urlopen(req, timeout=60))["event_id"]
    with urllib.request.urlopen(urllib.request.Request(base + "/" + eid, headers=headers_auth(False)), timeout=timeout) as r:
        event = None
        for raw in r:
            line = raw.decode().strip()
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                payload = json.loads(line[5:].strip())
                if event == "complete":
                    return payload
                if event == "error":
                    raise RuntimeError("Erreur du Space %s : %s" % (space, payload))
    raise RuntimeError("Pas de réponse complète du Space %s" % space)
