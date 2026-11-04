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
