# Plan de production : épisode test de 30 s, Kaël seul

Ce plan liste les dessins-clés nécessaires, plan par plan. Il sert à décider comment les obtenir :
dessins faits à la main, ou générés puis sélectionnés. Le moteur ne fabrique aucune pose : il ne fait
que séquencer, décaler, zoomer et composer les dessins fournis.

Règles du plan :
- cadence : 12 dessins/s (un dessin tenu 2 frames) pour l'action ; 8 dessins/s (3 frames) pour l'idle et les anticipations ;
- pas d'intermédiaire généré : on passe d'un dessin au suivant, ou on tient un dessin ;
- pas de rotation ni de déformation de la tête : chaque angle de tête est un dessin ;
- mouvement secondaire (cape, cheveux) seulement sur des calques découpés dans les dessins, ou dessiné ;
- effets : flash blanc, traînée (smear) et secousse de caméra, sur les pixels des dessins uniquement.

## Plans

| # | Durée | Contenu | Dessins-clés à obtenir | Nb | Cadence | Effets | Déjà disponible |
|---|---|---|---|---|---|---|---|
| P1 | 4 s | Ouverture : Kaël immobile, mi-corps, respiration | Vue face, 2 poses de torse (inspiration / expiration) | 2 | 8/s | aucun | face (oui) ; torse séparé (à faire) |
| P2 | 4 s | Marche vers la caméra, vue 3/4 | Cycle de marche 3/4, 8 dessins par cycle, 2 cycles | 8 | 12/s | aucun | 3/4 (oui, pose statique) ; poses de marche (à faire) |
| P3 | 2 s | Gros plan visage : doute, puis résolution | Expressions joie, colère, neutre | 3 | 6/s | aucun | `expr_*.png` et `bouche_*.png` (oui, à recaler) |
| P4 | 1 s | Anticipation de l'attaque : Kaël lève l'épée | Pose de préparation, 3 dessins | 3 | 8/s | aucun | aucun (à faire) |
| P5 | 2 s | Attaque : arc de l'épée, impact | Arc d'attaque, 6 dessins ; impact 2 frames | 6 | 12/s | flash 1 frame, traînée, secousse | aucun (références : arcs d'épée fournis) |
| P6 | 3 s | Réaction après l'impact, Kaël se redresse | Pose de retour, 4 dessins | 4 | 8/s | secousse amortie | aucun (à faire) |
| P7 | 4 s | Plan moyen : Kaël regarde l'horizon | Vue 3/4 et face, 2 dessins alternés | 2 | 4/s | aucun | 3/4 et face (oui) |
| P8 | 4 s | Dialogue : Kaël parle | 6 visèmes de bouche (A, E, I, M, O, U), face | 6 | 12/s | aucun | `bouche_*.png` (oui, à recaler sur la face) |
| P9 | 4 s | Plan de titre | Dessin de référence, sans texte généré | 1 | — | aucun | 3/4 (oui) |
| | 30 s | | | | | | |

Total de dessins à produire : environ 25 (P1 : 1 ; P2 : 6 sans les poses déjà prêtes ; P3 : 3 ; P4 : 3 ; P5 : 6 ; P6 : 4 ; P8 : 0 si les visèmes existent).

## Coupes

- Coupes sèches entre tous les plans (pas de fondu, pas de transition générée).
- P4 vers P5 : coupe sèche sur le geste, avec le flash sur le premier frame d'impact.

## Choses à décider par l'utilisateur

- Source des dessins à produire : dessin à la main, ou génération (ComfyUI, Colab ou Krita) puis sélection.
- Vues : sans profil ni dos découpés, les plans de marche et de combat restent en 3/4 et face.
- Calques : découper cape et cheveux dans chaque dessin pour le mouvement secondaire, ou les redessiner.
- Traits de vitesse radiaux : ils seraient dessinés par code, ce qui contredit la règle ; à dessiner à la main si voulus.
