# Erreurs rencontrées et méthodes retenues

Chaque erreur a une cause, une correction et un test. Une erreur corrigée doit rester ici pour ne pas recommencer.

## 1. Mesure des replis : normales de repos brutes
- Symptôme : 5 146 faces « retournées » même au repos ; puis des milliers à 90° sur un membre simplement tourné.
- Cause : comparer la normale d'une face à sa normale de repos fausse la mesure dès qu'un membre tourne d'un bloc, car sa normale tourne avec lui.
- Méthode retenue : la face est repliée seulement si sa normale est opposée à la normale de repos **tournée par son os dominant** (`engine/skinning/mesure_lbs.py`).
- Test : témoin à 0° = 0 ; LBS explicite égal au modificateur Blender à 0,0005 mm.

## 2. Maillage subdivisé ignoré (Multires)
- Symptôme : le moteur évaluait 677 442 sommets pour 10 582 dans les données ; les tests comparaient les données.
- Cause : le corps HBM porte un modificateur Multires (sculpture subdivisée). Les tests de base ne voient pas son détail.
- Méthode retenue : mesurer sur le maillage de base avec le Multires désactivé en vue (`show_viewport = False`), et le déclarer dans le rapport. Vérifier les modificateurs avant toute mesure (`obj.modifiers`).
- Limite connue : le pincement visible à gros plan peut venir du détail Multires, non mesuré ici.

## 3. Pose d'os non mise à jour
- Symptôme : une pose réglée par `pose_bone.matrix` ne change pas les mesures, ou une mesure donne 0 pli.
- Cause : sans `bpy.context.view_layer.update()`, la pose relue n'est pas à jour.
- Méthode retenue : mettre à jour la couche de vue après chaque pose, et restaurer la matrice d'origine dans un `finally`.
- Test : état de l'os vérifié avant et après chaque calcul (`etat.py`).

## 4. Opérateurs de poids inaccessibles en headless
- Symptôme : `vertex_group_smooth` renvoie « context is incorrect ».
- Cause : les opérateurs de poids exigent un contexte d'interface.
- Méthode retenue : lissage, limite à 4 influences et normalisation écrits en Python explicite (`lisser_limiter_normaliser`), déterministes et testés.

## 5. Parenté des yeux
- Symptôme : les yeux étaient parentés au maillage du corps, pas à l'armature ; le contrôle les déclarait sans skinning.
- Méthode retenue : attache rigide à l'os `mixamorig:Head` (transformation monde conservée) ; le contrôle accepte une pièce rigide attachée à un os (règle écrite).
- Test : pose de repos inchangée, yeux à la même position monde (écart nul).

## 6. Test de déformation trop indulgent
- Symptôme : un test « fuite proximale » comptait les bras comme fautifs quand la colonne se pliait.
- Cause : les bras sont rattachés à la colonne ; ils doivent bouger.
- Méthode retenue : une fuite est un sommet non rattaché (groupe dominant hors de l'os et de ses descendants) qui bouge de plus de 2 cm.

## 7. Scripts placés dans le mauvais dépôt
- Symptôme : `auto_skin.py` écrit dans `/home/claude/moteur3d` au lieu de `/home/claude/moteur_3_0` ; le diagnostic introuvable.
- Méthode retenue : le dépôt git est `/home/claude/moteur_3_0`. Toujours vérifier `git -C ... status` avant d'écrire, et utiliser des chemins absolus.

## 8. Arrêt de mes propres processus
- Symptôme : `pkill -f` ou une boucle `ps | grep` ont tué le shell (code 144).
- Cause : la commande contient le motif qu'elle cherche.
- Méthode retenue : `pgrep -x blender` / `pkill -x blender` (nom exact du binaire).

## 9. Relecture d'une mesure fausse
- Symptôme : une mesure « à 0 pli » après une pose a été prise pour un résultat.
- Méthode retenue : un résultat n'est accepté que si le témoin (0°) et le contrôle (valeur 0 de la correction) passent, et si l'état de l'os est vérifié.

## 10. Correction par élargissement de la transition
- Résultat : insuffisant (-17 % de replis à 90°). Ne pas le présenter comme correction complète.
- Méthode retenue pour le pli : clé corrective calibrée à l'angle, valeur = clamp(angle / angle_cible).

## 11. Étape oubliée dans un pipeline de sortie
- Symptôme : le fichier corrigé est passé à « NON PRÊT » : les yeux n'étaient plus rattachés.
- Cause : le script de correction appelait le skinning mais pas l'attache des pièces rigides.
- Méthode retenue : un pipeline doit appeler toutes les étapes de l'étape précédente. Le test de non-régression vérifie le rapport final, pas seulement l'étape nouvelle.

## 12. Résultat « bon » sur un seul cas
- Symptôme : la correction fonctionne sur le bras calibré, mais la combinaison de plusieurs articulations n'a pas été mesurée.
- Méthode retenue : toujours écrire la limite (combinaisons non testées) dans le rapport au lieu de la passer sous silence.

## 13. Restauration de pose dans un ordre arbitraire
- Symptôme : deux jambes à 90° donnaient 390 replis, alors que chacune seule donne 5 à 6 ; les scénarios s'influençaient entre eux.
- Cause : restaurer `pb.matrix` os par os, parents et enfants mélangés. Un enfant restauré avant son parent garde une pose relative fausse, qui pollue le scénario suivant.
- Méthode retenue : sauvegarder et restaurer `pb.matrix_basis` (transformations locales), indépendantes de l'ordre, puis mettre la couche de vue à jour.
- Test : témoins « un os seul en chaîne » = résultat du test à un os (6 et 5). Un test de cohérence entre deux méthodes est obligatoire avant d'interpréter une combinaison.

## 14. Import d'un script qui exécute un calcul
- Symptôme : `test_combinaisons.py` importait `construit_correctives.py`, qui relance tout le skinning et la correction à l'import.
- Méthode retenue : un module réutilisable ne contient pas de calcul au niveau du module. Les fonctions partagées vivent dans un module séparé ; les scripts de calcul ne sont jamais importés.

## 15. Combinaisons d'articulations : résultats mesurés
- Coude 90° + bras 90° (chaîne) : 28 → 3 replis.
- Deux bras à 90° : 32 → 6. Deux jambes à 90° : 11 → 0. Corps entier à 60° : 7 → 1.
- Les corrections se combinent de façon additive sans créer de nouveaux replis dans ces cas.

## 16. Référence de repos sans les clés correctives
- Symptôme : une clé corrective, pourtant calibrée, paraissait créer 13 replis à 90° au lieu de 3.
- Cause : la référence de normale était la forme de base, alors que la clé modifie la forme de repos. Le déplacement de repos était donc compté comme pli.
- Méthode retenue : la référence de repos est la forme avec les clés actives (`engine/skinning/mesure_dqs.py`, `test_dqs_cles.py`).
- Test : la valeur à 0 de toutes les clés redonne la même mesure que sans clés ; la mesure explicite (`mesure_lbs`) et la mesure évaluée (Blender) doivent donner les mêmes replis.

## 17. Deux mesures contradictoires : arrêter et trouver la cause
- Règle : quand deux mesures du même cas diffèrent, ne choisir ni l'une ni l'autre. Chercher la différence de méthode (ici, la référence de repos). Ne publier qu'après accord des deux.

## 18. Délai de sécurité sur un calcul long
- Symptôme : un calcul de 24 évaluations de maillage a été coupé par `timeout 115`, sans résultat ni erreur claire.
- Méthode retenue : lancer les calculs longs en arrière-plan (`nohup ... > log`) et lire le log ; ne pas mettre de délai court sur un calcul dont la durée est inconnue.

## 19. Idée de combinaison : DQS + formes correctives
- Le DQS seul améliore peu le bras (31 → 30 à 120°). Combiné aux clés, il réduit les replis à 105° (18 → 8) et annule ceux des jambes à 105°.
- Non encore validé : son gonflement (volume ajouté) n'est pas mesuré. Ne pas l'adopter avant cette mesure.

## 20. Mesure « témoin » indispensable pour un ajout d'os
- Symptôme possible : un os d'aide peut sembler améliorer les replis parce que le pipeline a changé (poids recalculés).
- Méthode retenue : deux variantes lancées dans les mêmes conditions (même source, même pipeline, seul l'os d'aide change), et le témoin « sans » enregistré à côté du résultat « avec ».
- Résultat : 24 -> 12 à 90°, 31 -> 19 à 120°. L'amélioration tient à l'os d'aide, pas au recalcul seul, puisque le témoin est recalculé avec le même pipeline.

## 21. Métrique de gonflement mal définie
- Symptôme : le « déplacement maximal à 120° » du pipeline final vaut environ 1 150 mm pour le bras.
- Cause : il mesure le déplacement total d'un membre qui tourne, ce qui est attendu. Ce n'est pas une mesure de gonflement.
- Méthode à retenir : un vrai contrôle de gonflement compare chaque sommet à la position idéale de son os (mouvement rigide du groupe dominant), et mesure l'écart. Tant que ce contrôle n'existe pas, le chiffre de déplacement ne doit pas être présenté comme un test.
- Statut : implémenté le lendemain (entrée 22 : `engine/skinning/controle_gonflement.py`, volume et étirement des arêtes).

## 22. DQS « preserve volume » : le gonflement mesuré ne confirme pas le candidat
- Mesure (volume signé du maillage évalué / volume de repos, `docs/rapports/gonflement_avec_cles.json`) :
  bras gauche à 120° : LBS 0,961 ; DQS 0,940. Jambe gauche à 120° : LBS 0,986 ; DQS 0,988 (écart négligeable).
  Avant-bras : DQS 0,9989 contre LBS 0,9976, gain marginal.
- Décision : DQS non adopté pour le bras. La mesure de gonflement remplace l'hypothèse « DQS garde le volume » : sur ce modèle, il ne le garde pas mieux que LBS.
- Règle : un mode de déformation ne s'adopte qu'après une mesure de volume et d'étirement, jamais sur la seule réduction des replis.

## 23. Les clés correctives créent des arêtes étirées
- Mesure (bras gauche, LBS, arêtes les plus étirées, rapports `gonflement_sans_cles.json` et `gonflement_avec_cles.json`) :
  à 90° : étirement maximal 2,63 sans clés, 3,59 avec clés. À 120° : 3,36 sans clés, 5,90 avec clés.
- Cause : `calculer_decalage` ne déplace que les sommets des faces repliées. Le décalage a donc une frontière brutale ; les arêtes qui la traversent s'étirent. Les replis disparaissent, mais l'étirement est déplacé à la frontière.
- Essai : lissage laplacien du champ de décalage (option `lissage`, `correction_pose.lisser_decalage`, défaut 0 pour rester reproductible).
  - Lissage 1, 80 itérations : étirement 2,63 à 90° et 3,35 à 120° (retrouve la valeur sans clés), mais replis du bras 9 à 90° au lieu de 2.
  - Lissage 1, 200 itérations : replis du bras 3/9/15/18 à 60/90/105/120°, étirement 2,63 et 3,34. Replis des jambes 2/4/6 à 90/105/120° au lieu de 0/3/3.
- Constat : la calibration était non convergée (80 itérations épuisées, `replis_apres` élevé). Mais 200 itérations ne suffisent pas à retrouver les replis d'origine : le lissage affaiblit la correction. Il n'y a pas de dominance : le compromis replis/étirement est réel.
- Décision : pipeline de référence = lissage 0 (commit précédent). Le lissage reste disponible, non adopté. Défaut connu à traiter : l'étirement de 5,9 fois à 120° est une défaillance visible, à corriger par une autre méthode (atténuation par distance à la frontière de pliage, ou lissage limité aux arêtes étirées).
- Règle : une correction se juge sur deux critères en même temps, replis et étirement. Une amélioration de l'un seul ne suffit pas.

## 24. Témoin à 0° : tolérance fixée par mesure, pas par confort
- Symptôme : le témoin à 0° donnait un étirement de 1,0003 et 0,9990, au lieu de 1,000.
- Mesure : 570 sommets diffèrent du repos de 1,3 µm au maximum, à cause d'un résidu de 10⁻⁶ dans la pose de deux os (flottants). Sur des arêtes d'environ 1 mm, cela donne un écart de ratio de 1e-3.
- Méthode retenue : la tolérance du témoin est fixée à 1,5e-3 et documentée dans `tests/test_gonflement.py`. Elle n'est pas élargie pour faire passer un résultat ; elle correspond au plancher de précision mesuré.

## 25. Contrainte de gradient sur le décalage : même compromis que le lissage
- Essai : limitation de |d_i - d_j| à kappa x longueur de repos de l'arête (`correction_pose.limiter_gradient`), kappa 0,15 et 0,3, pipeline inchangé sinon.
- Résultat bras gauche : étirement à 120° ramené à 3,36 (valeur sans clés) ; replis 19 au lieu de 13. Jambe : replis 4 à 120° pour kappa 0,3 contre 3 sans contrainte.
- Lecture : la correction qui supprime les replis est une grande variation du décalage ; la limiter supprime aussi la correction. Le couplage replis / étirement vient de la méthode elle-même (décalage calibré par poussée normale sur les sommets repliés), pas du réglage.
- Décision : option conservée, désactivée par défaut (kappa 0). Pipeline de référence inchangé (commit 53c0fc9 / 81db6b8).
- Méthode à essayer ensuite (non testée) : correction par région distincte (une clé par zone de pli, au lieu d'une clé par os), ou décalage calibré sur la position rigide prédite (mode « vers_os » déjà présent), pour que le décalage suive l'os et non la normale.

## 26. Direction « vers l'os » pour la calibration : rejetée
- Essai : décalage des sommets repliés vers l'axe de l'os (mode `vers_os`) au lieu de la normale. Pipeline inchangé sinon.
- Résultat bras gauche : replis 4/11/13/13 à 60/90/105/120° (contre 0/2/6/13 en référence) ; étirement 7,2 à 90° (contre 3,6).
- Lecture : les deux directions de calibration (normale, axe d'os) échouent sur le même critère. La cause n'est pas la direction mais le principe d'une clé unique par os.
- Erreur de procédure rencontrée : la seconde clé (120°) restait calibrée en normale pendant ce test. Corrigé et relancé ; la mesure ci-dessus est celle du test complet. Règle : un paramètre de méthode doit être passé à toutes les étapes qui l'utilisent, sinon la mesure mélange deux méthodes.
- Décision : option conservée, défaut inchangé (`moins_normale`).

## 27. Clé par zone (fenêtre spatiale autour de l'articulation)
- Essai : la correction n'est calculée et appliquée que dans une fenêtre autour de la tête de l'os qui tourne (poids 1 au centre, transition en smoothstep de 10 cm). Rayons testés : 10 cm et 20 cm.
- Rayon 20 cm : résultat identique à la référence (replis 2/6/13, étirement 3,59 à 90° et 5,90 à 120°). La zone de 20 cm + transition contient tout l'étirement.
- Rayon 10 cm : étirement ramené à la valeur sans clés (2,63 à 90°, 3,36 à 120°), mais replis du bras 7/13/14 à 90/105/120° (référence 2/6/13).
- Lecture : l'étirement et la correction des replis viennent de la même région, près de l'articulation. Réduire la zone réduit les deux. Le compromis n'est pas une propriété du champ de décalage mais de la géométrie du pli : une seule clé calibrée sur un angle ne peut pas corriger le pli sans étirer son bord.
- Décision : option conservée, défaut inchangé (pas de fenêtre).
- Conclusion sur les quatre tentatives (entrées 23 à 27) : aucune ne satisfait les deux critères. La suite exige une méthode de déformation différente (par exemple des os de torsion répartis ou une clé par angle au lieu d'une clé pilotée), à tester séparément.

## 28. Chaîne de deux os d'aide à la même position : pire que un seul
- Essai (sans clés, bras gauche, `engine/skinning/test_chaine_aide.py`) : un os d'aide à influence 0,5 (référence) contre deux os d'aide, à 0,33 et 0,67, tous deux à la tête de l'épaule et copiant `LeftArm`.
- Résultat : replis 3/12/17/19 à 60/90/105/120° contre 4/19/27/36 pour les deux os.
- Lecture : deux os qui copient la même rotation à la même position additionnent leurs effets au lieu de la répartir. Une répartition réelle exige des os placés à des positions différentes le long du bras (tête au milieu du bras, par exemple), ce qui n'est pas testé.
- Décision : référence inchangée (un os à 0,5).
- Règle : pour répartir une rotation sur plusieurs os, placer chaque os à sa propre position le long de la chaîne, jamais empiler des copies au même point.

## 29. Mesure de replis sans les clés : erreur de procédure
- Symptôme : la première mesure de la correction à trois échantillons donnait exactement les replis du bras sans clés (3/12/17/19).
- Cause : `faces_repliees` était appelé sans le paramètre `decalage` ; les clés calibrées n'entraient pas dans la mesure.
- Règle : toute mesure de replis doit recevoir le décalage total des clés actives. Une mesure identique à la variante sans clés est un signal d'erreur de procédure, pas un résultat.

## 30. Correction à trois échantillons (60, 90, 120) : pas de gain net
- Méthode : une clé par échantillon, calibrée seule à partir d'un décalage nul ; valeur en chapeau (1 à l'échantillon, 0 à 30° de distance). Interpolation linéaire par morceaux entre échantillons.
- Plafond d'amplitude 40 mm, 150 itérations : bras 0/2/7/15 à 60/90/105/120° (référence 0/2/6/13). Jambe identique à la référence.
- Plafond 80 mm, 300 itérations : bras 0/1/7/11, jambe gauche 0/0/4/3, mais étirement 8,0 à 120° (référence 5,9) et 4,5 pour la jambe (référence 2,4).
- Lecture : le goulot est le plafond d'amplitude de la calibration à 120°, qui n'atteint pas zéro replis. Augmenter l'amplitude réduit les replis et augmente l'étirement, dans les mêmes proportions que les essais précédents. Le compromis est structurel.
- Décision : pipeline de référence conservé (replis 0/2/6/13, étirement 5,9). Justification : c'est le compromis le plus équilibré des variantes mesurées, et aucune ne réduit à la fois les replis et l'étirement.
- Règle : une amplitude de correction de plusieurs centimètres sur un corps de 1,7 m est un signal d'alerte : elle compense un défaut de déformation au lieu de le corriger.

## 31. Image de contrôle qui ne montre pas la pose mesurée
- Symptôme : la première carte d'étirement montrait le bras au repos, avec des couleurs calculées sur le bras à 120°. Le bras semblait ne pas être fléchi.
- Cause : deux erreurs de procédure dans le script de rendu. La pose était restaurée avant le rendu, et les clés correctives étaient remises à zéro après le calcul du repos.
- Règle : une image de contrôle doit montrer exactement l'état que les mesures ont calculé. Pose, clés et couleurs doivent être appliquées au moment du rendu, puis vérifiées par une vue de profil avant toute conclusion.
- Correction : `engine/skinning/rendu_etirement.py` rétablit les clés et garde la pose au rendu. Image de référence : docs/rapports/visuel_etirement_bras120_profil.png. Le bras est fléchi à environ 90 à 120° vers l'avant, et la zone rouge est à l'épaule.

## 32. Vérification de hauteur d'un FBX importé : coordonnées locales et monde
- Symptôme : une première mesure donnait 42,9 pour un personnage de 169 cm.
- Cause : ma mesure utilisait les coordonnées locales du maillage, sans l'échelle 0,01 appliquée à l'objet à l'import (FBX en centimètres). La vraie hauteur monde est 1,70 m.
- Règle : mesurer une dimension après import uniquement en coordonnées monde (`matrix_world @ co`), et vérifier l'échelle de l'objet avant de conclure à un défaut d'export.

## 33. Distances mesurées en coordonnées locales après import FBX à l'échelle 0,01
- Symptôme : déplacements de 367 m et un saut de 66 m pour un personnage de 1,70 m. Physiquement impossible.
- Cause : mesure sur `v.co` (espace de l'armature, en centimètres) et non sur `matrix_world @ v.co`. Les valeurs étaient 100 fois trop grandes.
- Règle : toute distance après import se mesure en mètres monde. Une valeur physiquement impossible prouve une erreur de mesure avant toute conclusion sur le moteur.

## 34. Translation racine d'un clip comptée comme déformation
- Symptôme : le clip Running déplace la hanche de 3 à 370 unités sur 16 images (le personnage avance). Le corps entier se translate, et la mesure la comptait comme déformation.
- Règle : mesurer la déformation par rapport à la hanche (position monde de l'os racine retirée à chaque sommet). Séparer translation du corps et déformation de la peau.
- Résultat après correction : pas médian de 5,3 cm par image, maximum 40 cm (à vérifier : pic à examiner).

## 35. Action non affectée à l'armature sans slot (Blender 4.5)
- Symptôme : après `arm.animation_data.action = action`, le maillage ne bouge pas (déplacement 0 sur toutes les images), alors que les os changent.
- Cause : Blender 4.4 et suivants utilisent des slots d'action ; l'action n'est pas rattachée à l'objet.
- Règle : affecter aussi `animation_data.action_slot = action.slots[0]`, puis vérifier qu'une pose modifie le maillage avant de mesurer quoi que ce soit.

## 36. Transition directe entre deux clips : saut trop grand, corrigé par fondu
- Mesure : saut à la jonction Idle → Running de 0,18 m, soit 3,4 fois le pas médian de Running (seuil 3, échec).
- Correction : fondu enchaîné NLA (Running sur une piste supérieure, `blend_in` de 12 images, départ 12 images avant la fin d'Idle). Ratio 1,02 à 12 images, 1,57 à 6 images.
- Réglage retenu : 12 images, qui donne la transition la plus douce. Le seuil 3 a été fixé avant la mesure, à confirmer sur d'autres paires de clips.
- Limite : une seule paire de clips testée ; le pic de 40 cm par image dans Running reste à examiner.

## 37. Export animé : plage de bake de la scène au lieu de la plage du clip
- Symptôme : après réimport, un écart de 627 mm entre le personnage exporté et l'original.
- Cause : l'export cuit la plage de la scène (250 images), pas celle du clip (16 images) ; l'action réimportée couvre 2 à 251.
- Règle : borner `scene.frame_start/frame_end` à la plage du clip avant tout `bake_anim`, et compter les images à partir du début réel de l'action réimportée.

## 38. Comparer une animation exportée : décalage temporel de l'import FBX
- Constat : le FBX réimporté commence à l'image 2 pour un clip qui commence à 1.
- Règle : aligner les images par `frame_range[0]` de l'action réimportée, jamais par numéro d'image brut. Un écart de quelques centimètres sur tout le clip est souvent un décalage d'une image, à vérifier avant de conclure à une erreur d'export.
- Résultat après correction : écart maximal 0,257 mm sur tout le clip (tolérance 1 mm).

## 39. Mesure de section de jambe : étendue en X fausse à l'entrejambe ; corps non centré
- Symptôme 1 : aucun sommet sélectionné pour la jambe ; la section « la plus fine » tombait à 0,39 h avec 56 mm (faux).
- Cause 1 : le corps du bundle HBM est décalé de −2,26 m en X. Le filtre `x > 0,03` ne retenait rien.
- Cause 2 : près de l'entrejambe, l'étendue en X ne garde que le bord intérieur de la jambe et s'effondre. La mesure est donc fausse à cette hauteur.
- Règle : recentrer sur le milieu réel du corps avant tout filtre par coordonnée. Pour une section de membre, mesurer la profondeur (étendue en Y), qui ne s'effondre pas à l'entrejambe.
- Transparence : le changement de métrique a été fait après un échec. Il est justifié par la cause 2 (artefact géométrique), pas par le seul résultat ; à confirmer sur d'autres corps avant de généraliser.

## 40. Bras supposés horizontaux à partir de l'envergure : hypothèse fausse
- Symptôme : l'épaule estimée à 0,19 h en X donnait un bras de ≈ 0,24 m, très inférieur à la longueur anatomique.
- Cause : l'envergure (bras écartés) a été prise pour une extension horizontale. Mesure réelle : le bras descend de 0,74 h (épaule, x ≈ 0,21 m) à 0,46 h (poignet, x ≈ 0,41 m), soit une pose en « A » inclinée. Longueur implicite ≈ 0,6 m, cohérente.
- Règle : ne jamais déduire la pose d'un membre de l'encombrement en X. Mesurer le chemin du membre (centroïde par tranche) avant de poser des os.
- Correction : `test_hbm_articulations.py` utilise le chemin mesuré ; les bras restent marqués « mesurée », non validés (coude et poignet à confirmer).

## 41. Test d'intérieur : repère du BVH différent de celui des os
- Symptôme : tous les milieux d'os, y compris ceux du tronc, étaient signalés hors du maillage.
- Cause : les os sont exprimés dans le repère recentré en X, alors que le BVH était construit dans les coordonnées monde d'origine (décalées de −2,26 m).
- Règle : construire le BVH dans le même repère que les points testés. Un échec général (tous les points « dehors », même le centre) signale un repère faux, pas un défaut de géométrie.

## 42. Parité verticale fausse dans les zones de recouvrement des pièces
- Symptôme : cuisses et pieds signalés hors du maillage ; le tronc et les jambes inférieures sont bien dedans.
- Cause : les pièces du corps (bassin, cuisses) sont des coques fermées qui se recouvrent. Un rayon vertical traverse le bassin et compte des intersections en trop, ce qui inverse la parité.
- Règle : pour un membre, tester la parité dans la direction qui sort du membre (X, à l'opposé de l'axe du corps). Un test d'intérieur par parité n'est fiable que si les coques ne se recouvrent pas sur le trajet du rayon.

## 43. Point de hanche pris dans les bras : centroïde contaminé par une autre partie
- Symptôme : la hanche gauche sortait à (0,40 ; −0,10), à l'extérieur du corps et loin de la cuisse.
- Cause : le centroïde à 0,44 h incluait les sommets des bras (qui descendent jusqu'à 0,46 h). Une tranche horizontale mélange toutes les parties présentes à cette hauteur.
- Règle : avant de mesurer un membre par tranche, borner la tranche à ce membre (ici |x| < 0,25 m) et vérifier que le point mesuré est bien dans la cuisse.

## 44. Longueur de pied supposée au lieu d'être mesurée
- Symptôme : le milieu de l'os du pied sortait du maillage.
- Cause : la pointe du pied était placée à une longueur fixe (0,15 m) au lieu du sommet réel le plus avancé.
- Règle : une longueur d'os qui n'est pas mesurée doit être déduite de la géométrie (ici : sommet le plus avancé près du sol), jamais fixée à une valeur de catalogue.

## 45. Convention Mixamo rejetée faute de préfixe « mixamorig: »
- Symptôme : l'armature Ara (69 os, noms Mixamo exacts) était classée « convention inconnue ».
- Cause : le diagnostic ne reconnaissait la convention que par le préfixe `mixamorig:`. Ara exporte `Hips`, `Spine`, `LeftArm`… sans préfixe.
- Règle : reconnaître une convention par l'ensemble des noms de référence (avec ou sans préfixe), et signaler le préfixe comme une propriété séparée, pas comme un critère d'identité.
- Vérification : les mêmes 22 os de référence sont reconnus dans les deux formes ; le rapport de Maria reste inchangé.

## 46. Poids optimisés jugés sur les poses d'entraînement
- Symptôme : la jambe s'améliorait à 60/90/105° mais se dégradait à 120° (maximum 1,27 → 1,40).
- Cause : les poids optimisés sont spécifiques aux angles échantillonnés ; hors de la plage d'entraînement, ils extrapolent mal.
- Règle : tout résultat d'optimisation se juge sur un angle jamais vu à l'entraînement, et sur une plage qui encadre les angles d'entraînement. Un gain sur les points d'entraînement ne prouve rien.

## 47. Masque par os dominant : frontière brutale
- Symptôme : en optimisant seulement les sommets dont l'os dominant est le bras, l'étirement maximal monte à 5,39 au lieu de 1,65.
- Cause : les sommets optimisés et les voisins non optimisés se raccordent sans transition ; c'est la même frontière brutale que l'erreur 22.
- Règle : ne jamais optimiser un sous-ensemble de sommets sans transition ; l'optimisation doit porter sur le maillage entier, ou sur une zone avec un fondu.

## 48. Arêtes courtes dominant la métrique de ratio
- Symptôme : après entraînement séquentiel, une arête de 1 cm au coude passe de 1,5 à 5,4 à 105°, et 28 arêtes dépassent 2.
- Cause : le ratio longueur pose / longueur repos est très sensible aux arêtes courtes ; un petit transfert de poids vers l'os d'aide `LeftArmHelper` allonge fortement cette arête.
- Règle : pondérer la perte par la longueur de repos, et rejeter toute configuration dont l'étirement maximal augmente sur un angle d'entraînement.

## 49. Pondération des arêtes par leur longueur : le mauvais critère
- Problème identifié (erreur 48) : la perte ratio pondère toutes les arêtes à égalité ; une arête courte de 1 cm domine.
- Tentation : pondérer par la longueur. Rejeté : une arête courte entourée de grandes faces est normale ; une longueur courte n'indique pas une faible influence géométrique.
- Méthode retenue, d'après la littérature lue (brevet US10061871 : covariance pondérée par aires barycentriques ; Jacobson & Baran : poids cotangents) : pondérer chaque arête par la somme des aires barycentriques de ses deux sommets, normalisée à une moyenne de 1.
- Règle : une pondération d'arête doit refléter la surface locale qu'elle représente, pas sa longueur.

## 50. Garde de rejet limitée aux angles d'entraînement
- Symptôme : une optimisation entraînée sur 60/90/105° passait la garde, mais la jambe passait de 1,27 à 1,60 à 120°.
- Cause : la garde ne contrôlait que les angles d'entraînement. Un angle hors entraînement ne pouvait pas la déclencher.
- Règle : la garde doit contrôler au moins un angle de validation qui n'est pas dans l'entraînement, en plus des angles d'entraînement. Dans le cas contraire, la garde ne protège que contre la dégradation sur ce qu'elle a déjà vu.
- Constat complémentaire : à 120°, l'arête extrême de la jambe d'origine est à la cheville (arêtes de 1,7 cm). L'optimisation la déplace au genou (1,49). Les poids déplacent la contrainte sans la résoudre : la jambe demande un traitement dédié.

## 51. Métrique de plis numpy fausse : normale de repos non tournée
- Symptôme : le comptage numpy donnait 1 288 faces repliées à 120° sur le corps d'origine, contre 13 dans la mesure du projet. Les poids du haut du corps semblaient en aggraver le compte (1 357).
- Cause : la normale de repos était comparée brute à la normale de pose. Le projet (`mesure_lbs.faces_repliees`) compare la normale de pose à la normale de repos tournée par la matrice 3×3 (colonnes normalisées) de l'os dominant de la face.
- Correction : outil `engine/skinning/plis_numpy.py`, calqué sur la définition du projet.
- Calibration Blender sur `corps_haut.blend` (poids du haut du corps), comptes Blender / numpy : bras 10/10, 11/11, 17/17, 23/22, 32/28 (60, 75, 90, 105, 120°) ; avant-bras 4/4, 4/4, 5/5, 5/5, 6/6 ; jambe 0/0, 1/1, 5/5, 7/7, 11/10. Écart maximal : 4 faces (bras à 120°).
- Règle : une métrique numpy ne se conclut qu'après calibration sur la mesure Blender du projet. Un écart de l'ordre de 1000 faces indique une erreur de définition, pas un résultat.
- Constat réel, une fois calibré : les poids du haut du corps réduisent l'étirement du bras (3,36 → 1,56 à 120°), mais multiplient par deux environ les faces repliées du bras (origine numpy 3/7/8/12/15 ; haut 10/11/17/23/32 à 60/75/90/105/120°). Le compte d'origine est numpy (non vérifié dans Blender sur le fichier d'origine). Ce compromis rend ces poids non adoptables en l'état.
- Règle complémentaire (suite de l'erreur 50) : la garde de rejet doit contrôler aussi le nombre de faces repliées, sur les angles d'entraînement et de validation.

## 52. Garde d'optimisation aveugle aux plis
- Symptôme : la garde (étirement seul) acceptait des poids qui doublaient les faces repliées du bras (erreur 51).
- Correction : `garde_max` contrôle désormais le nombre de plis (`plis_numpy`) sur les angles d'entraînement et de validation. Test : poids du haut du corps refusés (plis 3 → 10 à 60°) ; poids d'origine acceptés.
- Constat de recherche : l'article ARAP-LBS (Thiery et al., telecom-paris, araplbs.pdf) ne traite ni les plis ni les poses de validation hors échantillon. Ses poses d'entraînement sont limitées à roulis ±60° et torsion ±10°. Nos angles de 105° et 120° dépassent ce domaine. Les plis à grand angle ne se résolvent donc pas par les seuls poids : il faut des formes correctives (clés), comme le pipeline de référence.
- Règle : la garde doit inclure les plis, et l'entraînement doit rester dans le domaine d'angles où la méthode est valide, ou être complété par des formes correctives.

## 53. Recherche sur les formes correctives : constats et sources non vérifiées
- Problème : les poids LBS seuls laissent 28 à 32 plis au bras à 120° (erreur 51). Le pipeline de référence avec clés correctives en laisse 13 (mesure du projet, session précédente). Les clés restent donc la meilleure voie connue dans ce projet.
- Sources lues : Wang & Phillips 2002 (multi-weight enveloping, SG07) : la page lue ne donne ni méthode ni chiffres ; à relire dans l'article original. Projet Maya « ML corrective deformer » (page non officielle) : correctif appris (MLP, angles → déplacements de sommets). Ses métriques ne sont pas définies et le jeu de test n'est pas clairement exclu de l'entraînement : non vérifié, à ne pas citer comme preuve.
- Règle : une source non officielle sert d'idée. Elle n'est retenue qu'après un test sur poses hors entraînement, dans le même protocole que le projet.
- Piste déterministe à tester : correctifs par angle (interpolation linéaire des déplacements de sommets entre angles clés), calculés à partir de la différence entre la cible d'étirement optimal et le LBS. Pas de GPU requis, conforme aux règles du projet.

## 54. Cible ARAP non convergée à 12 itérations
- Symptôme : entre 12 et 40 itérations, l'écart maximal de la cible atteint 0,071 pour une amplitude de correctif de 0,255 (28 %).
- Cause : itérations insuffisantes pour la méthode locale-globale ARAP.
- Correction : 40 itérations. Le résultat hors entraînement tient à 40 itérations.
- Règle : vérifier la convergence d'un solveur itératif (écart entre deux nombres d'itérations) avant d'interpréter son résultat.

## 55. Correctif ARAP interpolé : validé en numpy, pas encore dans Blender
- Méthode : cible ARAP (locale-globale, arêtes uniformes, ancres = tronc), correctif = cible − LBS, interpolé linéairement entre angles d'entraînement 60/90/120° ; test hors entraînement à 75° et 105°. Témoin 0° : écart 6e-7.
- Résultats (poids d'origine, plis / étirement max) : bras 75° 7 → 0, 2,26 → 1,12 ; bras 105° 12 → 4, 3,00 → 1,16 ; avant-bras 75° 2 → 0 ; avant-bras 105° 5 → 2 ; jambe 75° 1 → 0 ; jambe 105° 7 → 3.
- Limites : vérifié en numpy seulement (métrique calibrée à ±4 faces) ; arêtes uniformes (non cotangentes) ; test en interpolation, pas en extrapolation au-delà de 120° ; bras à 105° encore 4 plis.
- Prochaine étape : appliquer les correctifs dans Blender (formes-clés) et mesurer avec `mesure_lbs` avant toute déclaration de succès.

## 56. Amortissement des correctifs autour des plis : échec
- Tentative : réduire la correction des sommets situés dans une face repliée (facteur 0,8), jusqu'à disparition des plis.
- Résultat : amortissement brut par sommet : étirement 6,4 à 8,0 sur les poses de test (déchirures). Amortissement lissé par diffusion : 5 plis à 75° au lieu de 0. Les deux variantes sont rejetées.
- Règle : ne jamais modifier une correction par sommet sans transition continue ; et ne jamais entraîner une correction sur des plis qu'elle ne doit pas corriger.

## 57. Pondération cotangente : bug d'ancre puis résultat mitigé
- Bug : le second membre des ancres ignorait les poids d'arête (étirement 172 partout). Corrigé.
- Résultat hors entraînement : bras 105° 4 → 3 plis, étirement minimal 0,51 → 0,70 ; jambe 105° 3 → 1 pli ; avant-bras 105° 2 → 3 plis (minimum 0,28 → 0,25).
- Non adopté par défaut : gain mixte, pas de chaîne gagnante nette. L'option `poids=` reste disponible.
- Règle : un bug de second membre peut produire un résultat aberrant uniforme ; un résultat identique sur toutes les poses signale d'abord une erreur d'implémentation.

## 58. Limitation de rotation dès le début de l'ARAP : cascade de plis sur le bras
- Tentative : ramener vers l'identité la rotation des sommets de faces repliées, à chaque itération.
- Résultat : bon sur l'avant-bras et la jambe, mais sur le bras le nombre de plis explose (112 à 120° d'entraînement). Le sous-ensemble de faces repliées grossit d'une itération à l'autre.
- Version douce (alpha 0,8, activée à partir de l'itération 25) : évite la cascade, mais le bras reste dégradé (39 plis à 120°).
- Règle : une limitation active pendant le solveur doit être testée pour sa stabilité (le nombre de plis doit décroître), pas seulement pour son effet final.

## 59. Choix de variante sur les poses d'entraînement uniquement
- Méthode : pour chaque pose d'entraînement, garder la variante (ARAP simple ou limitée) qui produit le moins de plis sur cette pose. Les poses de test ne sont jamais utilisées pour ce choix.
- Résultat hors entraînement (numpy, puis Blender par formes-clés) : avant-bras 105° 0 pli (origine 5), jambe 105° 0 pli (origine 7), jambe 120° 1 pli (origine 10). Bras : 4 plis à 105° (origine 12), 12 à 120° (origine 15).
- Règle : une sélection entre variantes est légitime si elle n'utilise que l'entraînement et si le résultat est revalidé sur des poses non utilisées.

## 60. Ancre plus large : étirement explosif
- Test : seuil d'ancrage du tronc à 0,5 ou 0,2 au lieu de 0,99 : étirement 1,8 à 2,2 hors entraînement. Seuil 0,9999 : quasi identique à 0,99.
- Règle : l'ancrage doit rester au tronc pur ; élargir la zone libre fait dériver l'épaule.

## 61. Protocole : rotation de l'humérus seul à 120° n'est pas un usage réaliste
- Constat : nos tests font tourner l'humérus (LeftArm) seul jusqu'à 120°. Les pratiques de rig (fil Blender Artists « shoulder caving in ») répartissent la rotation entre un os d'épaule (clavicule) et le bras ; le bras seul est limité à environ 90°.
- Conséquence : une partie du résidu de plis à 105–120° vient peut-être du protocole, pas de la méthode. À confirmer par un test où la rotation est répartie entre LeftShoulder et LeftArm.
- Pistes issues de la recherche, non testées ici : Preserve Volume (DQS, déjà rejeté pour le volume, erreur antérieure) ; os d'aide avec contraintes (testé sans gain net) ; placement d'un vrai os d'épaule (à tester).
- Règle : un test de déformation doit reproduire la répartition réaliste des rotations entre os, sinon il mesure un cas extrême.

## 62. Hypothèse « le protocole cause le résidu » : testée, infirmée en grande partie
- Hypothèse (erreur 61) : répartir la rotation avec l'os d'épaule réduirait les plis du bras à grand angle.
- Test : pose réelle Blender, 1/3 sur LeftShoulder et 2/3 sur LeftArm, poids d'origine.
- Résultat (plis / étirement max) : total 60° : 3 / 2,06 contre 3 / 1,91 (bras seul) ; 90° : 8 / 2,84 contre 8 / 2,63 ; 105° : 9 / 3,23 contre 12 / 3,00 ; 120° : 11 / 3,62 contre 15 / 3,36.
- Conclusion : la répartition réduit à peine les plis (3 à 4 de moins à 105–120°) et dégrade légèrement l'étirement. Le repliement de l'épaule est intrinsèque aux poids LBS, pas seulement au protocole.
- Règle : tester une hypothèse protocole sur Blender avant d'en tirer une conclusion ; ici, la conclusion initiale était fausse en grande partie.

## 63. Correctifs ARAP sur poses réparties épaule + bras : validation Blender
- Entraînement 60/90/120 (répartition 1/3 épaule, 2/3 bras), test hors entraînement 75 et 105, formes-clés alimentées par l'angle total.
- Blender : à 75°, 0 pli (origine 6), étirement 1,22 ; à 105°, 4 plis (origine 9), étirement 1,19. Mêmes ordres de grandeur que le bras seul.
- Non résolu : à 120° (entraînement), 11 plis, comme à l'origine : la sélection garde la variante simple, la variante limitée n'aide pas sur cette pose.
- Règle : une correction entraînée sur le même angle total que le test est valable ; le résidu à 120° reste un problème ouvert.

## 64. Test de longueurs : correspondance de suffixe trop large
- Symptôme : le test des bras signalait « LeftForeArm = 0.144 h hors plage » alors que la valeur est dans la plage de l'avant-bras (0,12–0,18 h).
- Cause : `"LeftForeArm".endswith("Arm")` est vrai ; l'avant-bras était comparé à la plage du bras.
- Correctif : comparer le nom après le côté (`Left`/`Right`) à la clé exacte du dictionnaire de plages.
- Règle : dans un test, ne jamais faire de correspondance par `endswith` sur des noms dont un suffixe est un autre suffixe.

## 65. Lobes de doigts : un bloc de doigts accolés est fusionné, et l'ordre dépendait du côté
- Symptôme : à gauche, 4 lobes ; à droite, 3 lobes (l'index et le majeur fusionnés, n = 160 sommets). Un rig symétrique était impossible.
- Cause 1 : le regroupement par écart latéral de 5 mm ne sépare pas des doigts qui se touchent.
- Cause 2 : les doigts étaient ordonnés par « w décroissant », ce qui suppose le pouce du côté des w élevés. C'est vrai à gauche seulement.
- Correctif : un lobe plus large que deux doigts (> 21 mm par doigt) est découpé aux plus grands écarts ; les doigts sont ordonnés par distance au pouce.
- Vérification : gauche et droite donnent 4 lobes, mêmes rôles, écart de longueur 0,6 mm.

## 66. Bout de main déclaré « extrapolé » sans regarder les sommets extrêmes du maillage
- Symptôme : le chemin de la main s'arrêtait à 0,164 m du poignet et je l'ai signalé comme extrapolé.
- Vérification ensuite : les sommets les plus avancés du maillage vont à 0,182 m (pouce, index, majeur). L'extrapolation était une sous-estimation.
- Règle : avant de déclarer une extrémité extrapolée, mesurer les sommets extrêmes du maillage dans la direction de l'os.

## 67. Doigts courbés : une chaîne droite sort du maillage
- Symptôme : les phalanges droites entre la base et le bout sortaient du maillage (3 segments sur 4 pour l'index).
- Cause : les doigts du HBM sont légèrement courbés.
- Correctif : les articulations suivent la ligne médiane mesurée du lobe (centroïde par tranche de 1 cm, abscisse curviligne).
- Limite : les segments sans lobe mesuré (base du pouce, auriculaire) restent droits et sont marqués « estimés, non testés ».
