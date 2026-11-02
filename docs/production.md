# Plan de production : épisode test d'environ 30 secondes, Kaël seul

Ce plan liste les dessins-clés nécessaires, plan par plan. Le moteur ne fabrique aucune pose : il séquence,
décale, zoome et compose les dessins fournis. Aucune couleur n'est ajoutée par le code.

Cadences : **sur deux** = un dessin tenu 2 frames (12 dessins/s) ; **sur trois** = un dessin tenu 3 frames (8 dessins/s).
Statut : **existant** = déjà dans le dépôt (à recaler au besoin) ; **à obtenir** = à dessiner ou à générer.
Le choix de la source est une décision de l'utilisateur (voir plus bas).

## Plans

| # | Durée | Contenu | Vue | Dessins-clés | Nb | Cadence | Statut des dessins | Effets |
|---|---|---|---|---|---|---|---|---|
| P1 | 4 s | Ouverture : Kaël immobile, respire | face | neutre ; inspiration | 2 | sur trois | neutre existant ; inspiration à obtenir | aucun |
| P2 | 4 s | Marche vers la caméra | 3/4 | cycle de marche, 8 poses, 2 cycles | 8 | sur deux | 4 existants (`marche_1` à `marche_4`, vue à vérifier) ; 4 à obtenir | aucun |
| P3 | 2 s | Gros plan : doute puis résolution | face | neutre, joie, colère | 3 | sur trois | 3 existants : neutre (face), `expr_joie.png`, `expr_colere.png` | aucun |
| P4 | 1 s | Anticipation : Kaël lève l'épée | face | préparation | 3 | sur trois | 3 à obtenir | aucun |
| P5 | 2 s | Attaque : arc de l'épée, impact | face | arc, 6 poses dont l'impact | 6 | sur deux | 6 à obtenir | flash (silhouette, 1 frame), traînée, secousse, traits de vitesse (calque fourni, à obtenir) |
| P6 | 3 s | Réaction, Kaël se redresse | face | retour, 4 poses | 4 | sur trois | 4 à obtenir | secousse amortie |
| P7 | 4 s | Plan moyen : Kaël regarde l'horizon | face puis 3/4 | 2 vues en alternance | 2 | sur trois | 2 existants (bascule nette, sans fondu) | aucun |
| P8 | 4 s | Dialogue | face | visèmes A, E, I, M, O, U | 6 | sur deux | 6 existants (`bouche_A.png` à `bouche_U.png`) | aucun |
| P9 | 4 s | Titre : dessin de référence, sans texte | 3/4 | 1 | 1 | — | 1 existant | aucun |
| P10 | 2 s | Sortie : Kaël quitte le cadre | 3/4 | réutilise les poses de marche de P2 | 0 | sur deux | 0 nouveau | aucun |
| | **30 s** | | | | | | | |

## Totaux par catégorie

| Catégorie | Nombre | Détail |
|---|---|---|
| Dessins existants (à recaler) | 17 | P1 : 1 ; P2 : 4 ; P3 : 3 ; P7 : 2 ; P8 : 6 ; P9 : 1 |
| Dessins à obtenir (dessin ou génération) | 18 | P1 : 1 ; P2 : 4 ; P4 : 3 ; P5 : 6 ; P6 : 4 |
| Calques d'effets à obtenir | 1 | traits de vitesse (P5), PNG transparent, emplacement `effets_calques/traits_vitesse.png` |
| Effets automatiques (0 dessin) | 4 | flash, traînée, secousse, coupe sèche |

Volume : 35 dessins au total, dont 18 à obtenir. Sources : `universes/eclipse_royale/characters/kael/dessins/`. Cadence la plus lourde : P2 et P5, en sur deux.

## Effets

- **Flash** : la silhouette du personnage passe en blanc sur 1 frame. Sur fond blanc, le résultat est
  un instant blanc : la silhouette disparaît. Un flash visible sur fond sombre demande un fond fourni (voir options).
- **Traînée** : flou directionnel du calque, avec son alpha d'origine. Aucun halo.
- **Secousse** : décalage amorti de la caméra, sans effet sur les dessins.
- **Traits de vitesse** : aucun trait n'est généré. À dessiner à la main (PNG transparent) et à placer dans
  `effets_calques/traits_vitesse.png`. Tant que le fichier est vide, l'effet ne fait rien.
- **Coupes** : sèches, entre tous les plans.

## Placeholder (à ne pas présenter comme une attaque)

Dans la démo 6 s (`scenes/demo_6s.json`), le plan d'attaque est **P2**, marqué `placeholder` : il utilise le dessin
de face décalé, car aucune pose d'attaque n'existe. Il teste les effets, pas le mouvement.
Dans ce plan de 30 s, le même plan d'attaque est **P5**.

## Options pour obtenir les dessins (décision de l'utilisateur)

| Option | Principe | Contraintes |
|---|---|---|
| Dessin à la main | Un dessinateur produit les poses à partir des planches de référence (sprite sheets, arcs d'épée, poses de course) | Temps de travail ; garder la même échelle, le même pied et la même palette que les dessins existants |
| Génération gratuite | ComfyUI avec un modèle anime, IP-Adapter pour garder le personnage ; ou Google Colab (GPU limité) ; ou Krita et son plugin AI Diffusion | Demande un GPU (local ou Colab) ; vérifier la licence du modèle ; les pixels générés doivent être nettoyés et recalés |
| Mélange | Génération des poses, sélection et retouche à la main | Même contraintes que la génération ; la retouche prend du temps |

Dans les trois cas, chaque dessin doit :
- avoir la même échelle et le même pied que la face existante ;
- rester dans la palette de Kaël (les couleurs visibles sont celles des dessins fournis) ;
- être découpé sur fond blanc, sans contour ajouté par le code.

## Limites connues du moteur

- Pas de rotation de tête : chaque angle est un dessin.
- Pas de profil ni de dos découpés : les plans de marche restent en 3/4 et face.
- Le mouvement secondaire (cape, cheveux) n'est pas appliqué tant que les calques ne sont pas découpés.
