# Schéma du plan (format `monteur/plan/1`)

Le parseur `engine/script/fountain.py` transforme un script Fountain en JSON de plan.
Le validateur `engine/script/schema.py` (`valider(plan)`) renvoie la liste des erreurs ; liste vide = plan valide.

## Structure

```json
{
  "format": "monteur/plan/1",
  "titre": "Éclipse Royale - Épisode test",
  "transitions_debut": [{"type": "transition", "texte": "FADE IN:"}],
  "scenes": [
    {
      "id": "s01",
      "type": "EXT",
      "lieu": "COL DE PIERRE",
      "moment": "AUBE",
      "elements": [
        {"type": "action", "texte": "Le vent siffle..."},
        {"type": "dialogue", "personnage": "KAEL", "parentheses": ["bas"], "texte": "La nuit n'a pas encore fini."},
        {"type": "transition", "texte": "CUT TO:"}
      ]
    }
  ]
}
```

## Règles

| Champ | Règle |
|---|---|
| `format` | Toujours `monteur/plan/1`. |
| `titre` | Non vide (métadonnée `Title:` du script). |
| `transitions_debut` | Transitions écrites avant la première scène (ex. `FADE IN:`). |
| `scenes[].id` | Unique, de la forme `sNN`. Une scène `s00` ne sert qu'aux éléments sans en-tête. |
| `scenes[].type` | `INT`, `EXT`, `INT./EXT.` ou `EXT./INT.` (vide pour `s00`). |
| `scenes[].lieu` | Obligatoire sauf `s00`. |
| `scenes[].moment` | Facultatif (ex. `AUBE`, `PLUS TARD`). |
| `elements[].type` | `action`, `dialogue` ou `transition`. |
| `dialogue.personnage` | Obligatoire, nom en majuscules sans parenthèses. |
| `dialogue.parentheses` | Liste (peut être vide). |
| `dialogue.texte` | Obligatoire, lignes de la réplique réunies par un espace. |
| `action.texte`, `transition.texte` | Obligatoires. |

## Non géré (pour l'instant)

Notes `[[ ]]` et commentaires `/* */` sont retirés. Pas de double dialogue, pas de dialogue en retour de ligne après parenthèses multiples, pas de sections `=`, pas de synopsis `=`. Les éléments inconnus restent des `action`.
