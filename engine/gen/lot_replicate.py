"""Génère un lot de dessins clés de Kaël avec Flux Kontext Pro (Replicate), à partir d'une référence approuvée.

Usage : REPLICATE_API_TOKEN=... python3 engine/gen/lot_replicate.py <dossier_sortie> [--seulement nom1,nom2]
La clé n'est jamais écrite dans un fichier. Chaque image est enregistrée avec son prompt dans manifest.json.
"""
import base64
import json
import os
import sys
import time
import urllib.request

MODELE = "black-forest-labs/flux-kontext-pro"
REFERENCE = "universes/eclipse_royale/characters/kael/vues/face_g.png"
BASE = ("Same anime character as the reference image: same hair, blue eyes, navy cape with high collar, "
        "navy tunic, brown belt, white sleeves, black trousers, brown boots, same proportions and style. "
        "Clean black ink line art, cel shading with hard shadows, plain white background, no text.")

TRAVERSEE = "Full-body three-quarter view, "
JOBS = [
    # Marche : quatre temps d'un cycle
    ("marche_1_contact_g", TRAVERSEE + "walking, left leg forward with heel striking the ground, right leg behind, arms swinging naturally, cape flowing slightly.", "2:3", None),
    ("marche_2_passage", TRAVERSEE + "walking, legs passing each other mid-stride, weight on the right leg, cape swinging.", "2:3", None),
    ("marche_3_contact_d", TRAVERSEE + "walking, right leg forward with heel striking the ground, left leg behind, cape flowing.", "2:3", None),
    ("marche_4_passage", TRAVERSEE + "walking, legs passing each other mid-stride, weight on the left leg.", "2:3", None),
    # Répétition du temps 1 avec une autre graine : mesure la dérive du personnage
    ("marche_1_repetition", TRAVERSEE + "walking, left leg forward with heel striking the ground, right leg behind, arms swinging naturally, cape flowing slightly.", "2:3", 7),
    # Bouches (gros plan tête, même visage)
    ("bouche_A", "Close-up head and shoulders, front view. The character says the vowel A: mouth open wide. Keep eyes, hair and collar identical.", "1:1", None),
    ("bouche_I", "Close-up head and shoulders, front view. The character says the vowel I: lips spread, teeth slightly showing. Keep eyes, hair and collar identical.", "1:1", None),
    ("bouche_O", "Close-up head and shoulders, front view. The character says the vowel O: lips rounded in a small circle. Keep eyes, hair and collar identical.", "1:1", None),
    ("bouche_U", "Close-up head and shoulders, front view. The character says the vowel U: lips pushed forward, small opening. Keep eyes, hair and collar identical.", "1:1", None),
    ("bouche_E", "Close-up head and shoulders, front view. The character says the vowel E: mouth half open, lips relaxed. Keep eyes, hair and collar identical.", "1:1", None),
    ("bouche_M", "Close-up head and shoulders, front view. The character says M, B or P: lips closed, neutral. Keep eyes, hair and collar identical.", "1:1", None),
    # Expressions (gros plan tête)
    ("expr_joie", "Close-up head and shoulders, front view. Happy expression: soft smile, eyes slightly closed. Keep hair and collar identical.", "1:1", None),
    ("expr_colere", "Close-up head and shoulders, front view. Angry expression: eyebrows lowered and pulled together, jaw tight. Keep hair and collar identical.", "1:1", None),
    ("expr_tristesse", "Close-up head and shoulders, front view. Sad expression: eyes lowered, mouth turned down. Keep hair and collar identical.", "1:1", None),
    ("expr_surprise", "Close-up head and shoulders, front view. Surprised expression: eyes wide open, eyebrows raised, mouth slightly open. Keep hair and collar identical.", "1:1", None),
]


def entetes(tok):
    return {"Authorization": "Bearer " + tok, "Content-Type": "application/json",
            "User-Agent": "curl/8.5.0", "Accept": "application/json"}


def get(url, tok):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=entetes(tok)), timeout=120))


def lancer(nom, prompt, ratio, graine, image_b64, tok):
    corps = {"input": {"prompt": prompt, "input_image": "data:image/png;base64," + image_b64,
                       "aspect_ratio": ratio, "output_format": "png", "safety_tolerance": 2}}
    if graine is not None:
        corps["input"]["seed"] = graine
    req = urllib.request.Request("https://api.replicate.com/v1/models/%s/predictions" % MODELE,
                                 data=json.dumps(corps).encode(), headers=entetes(tok), method="POST")
    for tentative in range(30):
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            print("limite de débit, nouvelle tentative pour", nom, flush=True)
            time.sleep(12)
    raise RuntimeError("trop de 429 pour " + nom)


def main():
    tok = os.environ["REPLICATE_API_TOKEN"]
    dossier = sys.argv[1]
    seulement = None
    if "--seulement" in sys.argv:
        seulement = sys.argv[sys.argv.index("--seulement") + 1].split(",")
    os.makedirs(dossier, exist_ok=True)
    image_b64 = base64.b64encode(open(REFERENCE, "rb").read()).decode()
    travaux = [j for j in JOBS if not seulement or j[0] in seulement]
    en_cours = {}
    for nom, prompt, ratio, graine in travaux:
        p = lancer(nom, BASE + " " + prompt, ratio, graine, image_b64, tok)
        en_cours[nom] = {"url": p["urls"]["get"], "prompt": BASE + " " + prompt, "ratio": ratio, "graine": graine}
        print("lancé", nom, flush=True)
    manifeste = {}
    for _ in range(200):
        encore = [n for n in en_cours if n not in manifeste]
        if not encore:
            break
        for nom in encore:
            p = get(en_cours[nom]["url"], tok)
            if p["status"] in ("succeeded", "failed", "canceled"):
                info = dict(en_cours[nom], statut=p["status"], erreur=p.get("error"))
                if p["status"] == "succeeded":
                    sortie = p["output"] if isinstance(p["output"], str) else p["output"][0]
                    data = urllib.request.urlopen(urllib.request.Request(sortie, headers={"User-Agent": "curl/8.5.0"}), timeout=120).read()
                    chemin = os.path.join(dossier, nom + ".png")
                    open(chemin, "wb").write(data)
                    info["fichier"] = chemin
                    print("ok", nom, len(data), flush=True)
                else:
                    print("échec", nom, p.get("error"), flush=True)
                del info["url"]
                manifeste[nom] = info
        time.sleep(4)
    json.dump(manifeste, open(os.path.join(dossier, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("terminé :", sum(1 for m in manifeste.values() if m["statut"] == "succeeded"), "/", len(travaux), "réussis")


if __name__ == "__main__":
    main()
