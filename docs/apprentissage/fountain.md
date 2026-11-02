# Note d'apprentissage : scénario au format Fountain

**Source lue :** https://fountain.io/syntax (lecture du 1er novembre 2026).

## Ce que j'ai retenu

- Fountain est un format texte brut : un scénario se lit sans logiciel et se versionne dans git.
- La structure se devine à la forme des lignes, séparées par des lignes vides :
  - **en-tête de scène** : `INT.`, `EXT.`, `EST.`, `I/E`, etc., puis le lieu, un tiret, le moment (ex. `EXT. COL DE PIERRE - AUBE`) ;
  - **action** : toute ligne qui n'a pas d'autre forme ;
  - **personnage** : ligne entièrement en majuscules, précédée d'une ligne vide, avec au moins une lettre ; une extension entre parenthèses est permise (`(O. S.)`) ;
  - **parenthèses** : indication de jeu juste sous le nom du personnage ;
  - **dialogue** : les lignes qui suivent le nom ;
  - **transition** : ligne en majuscules qui finit par `TO:` (ex. `CUT TO:`).
- Forçages : `.` devant une ligne = en-tête forcé ; `@` devant un nom = personnage forcé ; `>` = transition forcée.
- Les notes `[[ ]]` et les commentaires `/* */` ne sont pas montrés au lecteur. Mon parseur les retire.
- Les métadonnées de tête (`Title:`, `Author:`) sont facultatives, en tout début de fichier.

## Ce que j'applique dans le monteur

- Le parseur produit un JSON de plan (`docs/schema_plan.md`), validé par `engine/script/schema.py`.
- Les transitions forcées avant la première scène vont dans `transitions_debut`.

## Écarts avec le standard

- Mon parseur accepte aussi `FADE IN:` comme transition alors que le standard ne reconnaît que `TO:`. C'est plus souple, et c'est noté dans le schéma.
- `FADE OUT.` est lu comme transition ; le standard le lit comme action. Pour un monteur, le sens est le même, mais l'écart est volontaire.

## Pour plus tard

- Lire les lignes continuées de la page de titre (indentées de 3 espaces ou plus).
- Gérer les doubles dialogues, qui demandent deux colonnes dans le plan.

## Sources à consulter pour M5

- Format de sortie du parseur : le schéma interne est le nôtre, pas celui de Fountain.
