# Propagation de SQ sur géométries synthétiques à poids contrôlés

Objet : vérifier si SQ déplace des sommets à 100 % d'influence d'un seul os à cause de leurs voisins, et déterminer
si ce mécanisme explique l'amplification de l'entrejambe masculin. Aucun critère modifié, référence inchangée,
aucun candidat sélectionné.

Fichiers : `engine/validation/skinning/investigation_synthetique.py` (configurations, contrôles, profils),
`investigation_synthetique_complement.py` (120° et densité), `investigation_moyenne_rotations.py` (moyenne arithmétique
contre polaire, par angle). Sorties : `resultats.json`, `complement.json`, `moyenne_rotations.json` dans ce dossier.

## Conclusion (réponses aux six questions)

1. **Propagation normale de la formulation ?** Oui, au sens mathématique. Le système SQ est la solution d'une énergie
   globale : une arête impose une cible R_ab (r_a − r_b), et seul λ ancre chaque sommet à sa position LBS. Rien dans
   l'énergie n'impose qu'un sommet à poids pur reste rigide. Un sommet pur se déplace donc dès que ses voisins
   demandent une cible différente. Ce n'est pas une erreur d'implémentation (section 1).
2. **Problématique avec certaines distributions ?** Oui. Elle croît avec l'écart d'angle entre os voisins (section 3)
   et atteint 0,34 h à 120° sur une interface brutale. Une interface progressive la réduit légèrement (0,155 contre
   0,195 à 60°).
3. **Amplifiée par les triangles courts ou la densité ?** En unités d'arête, oui : le déplacement passe de 0,085 h à
   0,31 h quand le maillage passe de 11 à 41 points par côté. Mais en valeur absolue il reste constant (≈ 0,018 m).
   C'est un effet d'échelle géométrique, non une erreur de discrétisation. Les mailles mixtes n'ajoutent rien
   au-delà de cet effet (section 4).
4. **Mauvaise formulation ou défaut d'implémentation ?** Implémentation vérifiée (section 1). Le problème vient de
   la formulation, sous deux aspects distincts : (a) absence de terme de rigidité pour les régions à poids pur ;
   (b) moyenne arithmétique R_ab = (R_a + R_b)/2, qui n'est pas une rotation et comprime les triangles à grand angle.
   Ces deux aspects sont séparés en section 5.
5. **Explique-t-elle l'amplification de l'entrejambe ?** **Non démontré.** Le même mécanisme qualitatif est présent
   (croissance avec l'écart d'angle, portée contrôlée par λ), et le profil réel est 1,5 fois plus fort qu'en
   synthétique à 120° (section 6). Mais les 24 défauts sont à poids mixte, pas à poids pur. Le cas synthétique le
   plus proche, l'interface progressive, montre que SQ n'amplifie pas le maximum (1,00 contre 1,11 pour LBS). La
   propagation seule ne suffit donc pas à expliquer l'amplification mesurée (+0,12 sur le maximum).

## 1. Contrôles de cohérence du solveur

| Contrôle | Résultat |
|---|---|
| Un seul os (w = 1 partout) : SQ − LBS | 3,3e-15 m |
| Deux os à même rotation : SQ − LBS | 3,3e-15 m (rigidité exacte) |
| Somme des lignes de la matrice M − λ | 3,6e-16 (pas de condition de bord cachée) |
| Valeur propre minimale de M | = λ exactement (grilles 11, 21, 41 ; λ = 0,01, 0,1, 1) |
| Déplacement moyen SQ − LBS (conservation du centre) | 1e-15 m dans toutes les configurations |

Lecture : la matrice a la structure attendue, sans conditions de bord fixes. La constante est le seul mode non
amorti, et seul λ l'ancre. Le centre de masse est conservé exactement. Aucune erreur d'implémentation n'apparaît.

## 2. Mesure de retournement corrigée

Une première mesure comptait comme retournées les normales opposées au repos. Une rotation rigide de 120° d'un
feuillet plan inverse précisément la normale : 400 faux retournements en LBS, qui est rigide. La mesure a été
corrigée : la normale déformée est comparée à la normale au repos tournée par le repère rigide local (polaire de la
moyenne de Mv sur le triangle). Après correction, **0 retournement** pour LBS comme pour SQ dans toutes les
configurations (entrée 193).

## 3. Propagation vers les sommets à poids pur

Interface : sommets dont un voisin a des poids différents. Profil : déplacement SQ − LBS en unités de longueur
d'arête moyenne h, médiane par distance de graphe à l'interface. Grille 21 × 21, λ = 0,1, sauf mention contraire.

| Configuration | Écart d'angle entre os | d = 0 | d = 1 | d = 2 | d = 4 | d = 6 |
|---|---|---|---|---|---|---|
| Un os seul | 0° | 0 | 0 | 0 | 0 | 0 |
| Brutal, cuisse D fixe | 30° | 0,101 | 0,081 | 0,065 | 0,042 | 0,028 |
| Brutal, opposés ±30° | 60° | 0,195 | 0,156 | 0,125 | 0,081 | 0,054 |
| Brutal, opposés ±60° | 120° | 0,338 | 0,271 | 0,217 | 0,140 | 0,094 |
| Progressif, opposés ±30° | 60° | 0,155 | 0,126 | 0,103 | 0,072 | 0,056 |

Lecture : la propagation croît avec l'écart d'angle entre os voisins et s'annule quand il est nul. Elle est présente
aux sommets à 100 % d'un seul os, qui sont rigides en LBS. Pour un sommet pur, elle vient donc des voisins.

## 4. Densité, taille des triangles et ancrage λ

**Densité (interface brutale, opposés ±30°, λ = 0,1)**

| Grille | h (m) | Déplacement à d = 0, en h | Déplacement à d = 0, absolu (m) |
|---|---|---|---|
| 11 | 0,226 | 0,085 | 0,0192 |
| 21 | 0,113 | 0,155 | 0,0176 |
| 41 | 0,057 | 0,314 | 0,0178 |

En unités d'arête, la propagation est multipliée par 3,7 de la grille 11 à la grille 41. En valeur absolue elle reste
constante. Plus les arêtes sont courtes, plus la même erreur absolue pèse en unités d'arête (entrée 192).

**Mailles de deux tailles** : mélange progressif 0,189 h, contre 0,155 h en maillage uniforme. En absolu : 0,018 m
contre 0,0175 m. Le mélange de tailles n'ajoute donc pas d'effet propre au-delà de l'échelle.

**Ancrage λ (brutal, opposés ±30°)**

| λ | d = 0 | d = 6 | Portée estimée (arêtes) |
|---|---|---|---|
| 0,01 | 0,208 | 0,163 | ≈ 20 |
| 0,1 | 0,195 | 0,054 | ≈ 4,5 |
| 1,0 | 0,147 | 0,002 | ≈ 1,4 |

La portée varie approximativement comme λ^(−1/2) : le rapport entre λ = 0,1 et λ = 1 est proche de √10. Une valeur
plus faible de λ étend la propagation. Ce n'est pas un réglage à choisir : c'est la conséquence de la formulation.

## 5. Deux mécanismes distincts : propagation et compression par moyenne arithmétique

Test : même géométrie, même poids, seul R_ab change (moyenne arithmétique contre polaire de la moyenne). Il s'agit d'un
diagnostic, la variante polaire n'est pas un candidat.

| Angle (grille 21) | Aire min (arithmétique) | Aire min (polaire) | Propagation d = 0, arithmétique | Propagation d = 0, polaire |
|---|---|---|---|---|
| 60° | 0,868 | 0,964 | 0,195 h | 0,202 h |
| 120° | **0,509** | 0,898 | 0,338 h | 0,391 h |

Lecture : la moyenne arithmétique comprime fortement les triangles à grand angle (aire 0,51 à 120°), et la polaire
supprime presque entièrement cette compression. Mais la polaire **augmente** la propagation (0,34 h → 0,39 h). Les
deux phénomènes sont donc distincts : la compression vient du rétrécissement de R_ab ; la propagation vient de
l'écart de rotation entre voisins, que la polaire ne retire pas (entrée 194).

## 6. Comparaison avec l'entrejambe réel (configuration t = 0, cuisse droite seule)

| d | Réel (h = 0,0081 m) | Synthétique, 120°, brutal, λ = 0,1 |
|---|---|---|
| 0 | 0,508 | 0,338 |
| 1 | 0,376 | 0,271 |
| 2 | 0,316 | 0,217 |
| 3 | 0,292 | 0,174 |
| 4 | 0,242 | 0,140 |

Lecture : même forme (décroissance régulière, rapport d4/d0 de 0,48 contre 0,41), même ordre de grandeur, un facteur
1,5 à 1,7 en plus côté réel. Le maillage réel est irrégulier et le nombre de sommets par distance est faible (8 à 10).
Le rapprochement est donc qualitatif : il ne prouve pas l'égalité des mécanismes.

Points de différence :
- Les 24 défauts du patch initial sont à poids **mixte**. Le test sur sommets purs (t = 0) ne reproduit pas leur
  situation.
- Le cas synthétique à poids progressif, le plus proche des défauts, n'amplifie pas le maximum : SQ 1,00 contre
  LBS 1,11 à 60°. L'amplification réelle (+0,12 sur le maximum) n'est donc pas expliquée par la propagation seule.
- Les défauts réels ont un étirement LBS déjà à 2,47, causé par les poids de l'entrejambe (sensibilité mesurée au
  balayage de poids), que les configurations synthétiques ne reproduisent pas.

## 7. Facteurs distingués

| Facteur | Nature | Dépend de | Effet mesuré |
|---|---|---|---|
| Propagation vers sommets purs | Formulation (absence de terme de rigidité pur) | écart d'angle entre voisins, λ | 0,10 à 0,34 h selon l'angle ; portée ∝ λ^(−1/2) |
| Compression par moyenne arithmétique | Formulation (R_ab non orthogonal) | angle entre os | aire 0,51 à 120° ; supprimée par la polaire |
| Effet de densité | Échelle | taille des arêtes | constant en absolu (≈ 0,018 m), croît en h |
| Sensibilité de LBS aux poids | Propriété de LBS, préexistante | poids de l'entrejambe | maximum LBS jusqu'à 10 avec redistribution |

## 8. Ce qui reste incertain

- Le poids relatif de la propagation et de la compression dans l'amplification réelle n'est pas déterminé.
- La géométrie réelle n'a pas été reproduite à l'identique (patch isolé non fait, car SQ est global).
- Les configurations synthétiques sont planes ; la courbure et la géométrie 3D de l'entrejambe ne sont pas modélisées.
- Aucune poses indépendantes, morphologie féminine ou Maria n'ont été testées : aucun candidat n'est proposé.

## 9. Décision

Aucune cause unique n'est démontrée pour l'amplification de l'entrejambe. La propagation est un mécanisme réel de la
formulation SQ, mesuré et caractérisé. La compression par moyenne arithmétique est un mécanisme distinct. Aucun ne
suffit, à lui seul, à expliquer l'amplification réelle. La suite logique est de tester une géométrie intermédiaire
(poids mixtes, angle réel, maillage réel) pour séparer les deux effets sur le cas de l'entrejambe. Aucune méthode
n'est encore choisie.
