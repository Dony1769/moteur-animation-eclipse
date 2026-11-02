"""Routeur de génération : essaie les fournisseurs dans l'ordre et bascule au suivant
seulement quand le fournisseur refuse pour crédit épuisé ou quota atteint.

Chaque fournisseur est facturé sur le compte dont la clé est fournie. Les clés viennent de
l'environnement (jamais écrites dans un fichier) :
  REPLICATE_API_TOKEN, STABILITY_API_KEY, IDEOGRAM_API_KEY, OPENAI_API_KEY

Usage (module) : from routeur import generer ; png, fournisseur = generer(prompt, ratio, ref_png_bytes)
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
import uuid

UA = "curl/8.5.0"


class CreditEpuise(Exception):
    pass


class ErreurFournisseur(Exception):
    pass


def _requete(url, headers, data=None, methode=None, timeout=300):
    h = {"User-Agent": UA, **headers}
    for tentative in range(4):
        req = urllib.request.Request(url, data=data, headers=h, method=methode)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:
            corps = e.read()
            texte = corps.decode("utf-8", "replace").lower()
            # Limite de débit : on attend et on réessaie, sans basculer de fournisseur
            if e.code == 429 and "throttl" in texte and tentative < 3:
                time.sleep(15)
                continue
            if e.code == 402 or (e.code == 429 and not "throttl" in texte) or any(
                    m in texte for m in ("insufficient", "credit", "balance", "quota", "billing")):
                raise CreditEpuise("%s %s" % (e.code, texte[:200]))
            raise ErreurFournisseur("%s %s" % (e.code, texte[:300]))
    raise ErreurFournisseur("limite de débit persistante")


def _multipart(champs, fichiers):
    frontiere = uuid.uuid4().hex
    corps = b""
    for nom, val in champs.items():
        corps += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (frontiere, nom, val)).encode()
    for nom, (fichier, contenu, mime) in fichiers.items():
        corps += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                  % (frontiere, nom, fichier, mime)).encode() + contenu + b"\r\n"
    corps += ("--%s--\r\n" % frontiere).encode()
    return corps, "multipart/form-data; boundary=" + frontiere


# ----- fournisseurs -----

def replicate(prompt, ratio, ref):
    tok = os.environ["REPLICATE_API_TOKEN"]
    h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
    corps = {"input": {"prompt": prompt, "input_image": "data:image/png;base64," + base64.b64encode(ref).decode(),
                       "aspect_ratio": ratio, "output_format": "png", "safety_tolerance": 2}}
    _, data, _ = _requete("https://api.replicate.com/v1/models/black-forest-labs/flux-kontext-pro/predictions",
                          h, json.dumps(corps).encode(), "POST", 120)
    p = json.loads(data)
    url = p["urls"]["get"]
    for _ in range(200):
        _, d, _ = _requete(url, {"Authorization": "Bearer " + tok}, timeout=60)
        p = json.loads(d)
        if p["status"] == "succeeded":
            sortie = p["output"] if isinstance(p["output"], str) else p["output"][0]
            return _requete(sortie, {}, timeout=120)[1]
        if p["status"] in ("failed", "canceled"):
            raise ErreurFournisseur(str(p.get("error")))
        time.sleep(3)
    raise ErreurFournisseur("délai dépassé")


def stability(prompt, ratio, ref):
    cle = os.environ["STABILITY_API_KEY"]
    champs = {"prompt": prompt, "mode": "image-to-image", "strength": "0.30", "output_format": "png",
              "model": "sd3.5-large-turbo"}
    corps, mime = _multipart(champs, {"image": ("ref.png", ref, "image/png")})
    _, data, _ = _requete("https://api.stability.ai/v2beta/stable-image/generate/sd3",
                          {"Authorization": "Bearer " + cle, "Accept": "image/*", "Content-Type": mime},
                          corps, "POST", 300)
    return data


def ideogram(prompt, ratio, ref):
    cle = os.environ["IDEOGRAM_API_KEY"]
    ratios = {"2:3": "2x3", "1:1": "1x1", "16:9": "16x9"}
    champs = {"prompt": prompt, "aspect_ratio": ratios.get(ratio, "1x1"), "image_weight": "60",
              "rendering_speed": "DEFAULT"}
    corps, mime = _multipart(champs, {"image": ("ref.png", ref, "image/png")})
    _, data, _ = _requete("https://api.ideogram.ai/v1/ideogram-v3/remix",
                          {"Api-Key": cle, "Content-Type": mime}, corps, "POST", 300)
    url = json.loads(data)["data"][0]["url"]
    return _requete(url, {}, timeout=120)[1]


def openai(prompt, ratio, ref):
    cle = os.environ["OPENAI_API_KEY"]
    taille = {"2:3": "1024x1536", "1:1": "1024x1024"}.get(ratio, "1024x1024")
    champs = {"model": "gpt-image-1", "prompt": prompt, "size": taille, "quality": "medium"}
    corps, mime = _multipart(champs, {"image[]": ("ref.png", ref, "image/png")})
    _, data, _ = _requete("https://api.openai.com/v1/images/edits",
                          {"Authorization": "Bearer " + cle, "Content-Type": mime}, corps, "POST", 300)
    return base64.b64decode(json.loads(data)["data"][0]["b64_json"])


# Ordre de basculement, avec la variable d'environnement qui active chaque fournisseur
FOURNISSEURS = [
    ("replicate", "REPLICATE_API_TOKEN", replicate),
    ("stability", "STABILITY_API_KEY", stability),
    ("ideogram", "IDEOGRAM_API_KEY", ideogram),
    ("openai", "OPENAI_API_KEY", openai),
]


def generer(prompt, ratio, ref, journal=None):
    """Renvoie (octets PNG, nom du fournisseur). Bascule au suivant seulement sur crédit épuisé."""
    for nom, variable, fonction in FOURNISSEURS:
        if not os.environ.get(variable):
            continue
        try:
            png = fonction(prompt, ratio, ref)
            if journal is not None:
                journal.append({"fournisseur": nom, "statut": "ok"})
            return png, nom
        except CreditEpuise as e:
            if journal is not None:
                journal.append({"fournisseur": nom, "statut": "credit_epuise", "detail": str(e)[:160]})
            continue
    raise RuntimeError("Aucun fournisseur disponible : tous sont sans crédit ou non configurés.")
