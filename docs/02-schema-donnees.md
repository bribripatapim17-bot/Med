# QuizMed : schéma de données (livrable 2/6)

Source de vérité du format : [`schemas/content.schema.json`](../schemas/content.schema.json) (JSON Schema 2020-12, version `1.0.0`). Ce document l'explique et décrit en plus les données utilisateur (SwiftData) et les règles de calcul.

## 1. Principes

- **Deux mondes séparés.** Le *contenu* (JSON produit par le pipeline) est immuable côté app. Les *données utilisateur* (SwiftData) ne le référencent que par des **ids texte** : aucune relation SwiftData vers le contenu, donc une mise à jour du contenu ne casse pas la progression.
- **Ids stables et préfixés** : `y_` année, `ue_`, `mod_`, `ch_`, `n_` notion, `src_` source, `bee_`, `q_`, `sh_`/`shi_` fiche/item, `mn_`. Attribués une fois par le pipeline, jamais recalculés.
- **Positions** (`bbox`) : `[x, y, largeur, hauteur]` normalisés de 0 à 1 sur la page, origine en haut à gauche. Indépendant de la résolution.
- **Deux étapes** : `generated` (ce que j'écris ; `id`, `hash`, `widgetFriendly`, `verification`, `sourceHash` facultatifs) et `built` (ce que l'app lit ; ces champs deviennent obligatoires). Le champ `x-builtRequired` du schéma les liste.
- **Compatibilité** : `schemaVersion` `1.x` (une évolution majeure = refus d'ouvrir ce contenu). `contentVersion` `AAAA.MM.JJ-n` identifie chaque build.

## 2. Contenu (JSON)

### 2.1 Fichiers

```
Content/
├─ manifest.json            version, date, kind (demo|real), sha256 de chaque fichier, chiffres
├─ taxonomy.json            Année > UE > Module > Chapitre > Notion
├─ sources.json             fichiers de cours (nom, chemin, sha256, nb de pages, couche texte)
├─ bees.json                abeilles : position, méthode, rattachement, ambiguïtés
├─ questions-index.json     une ligne par question (chargement rapide : question du jour, filtres)
├─ chapters/<ch_id>/
│    questions.json   sheet.json   mnemonics.json
└─ pages/<src_id>/
     p012.webp              page entière (pages citées uniquement)
     p012_<hash>.webp       capture recadrée d'un schéma, tableau ou formule
```

### 2.2 Hiérarchie

| Niveau | Entité | Champs clés |
|---|---|---|
| Année | `Year` | `code` (`PASS_LAS`, `DFGSM2`, `DEMO`), `label` |
| UE / matière | `UE` | `code`, `title`, `semester` (`S1`/`S2`) |
| Module | `Module` | `title` |
| Chapitre | `Chapter` | `sourceIds`, `beeCount`, `tier` (`incontournable` si au moins 2 abeilles rattachées) |
| Notion | `Notion` | `priority` (vrai si une abeille rattachée), `beeIds`, `refs` (source, page, section) |

### 2.3 Question

| Champ | Règle |
|---|---|
| `type` | `qcm` (réponses multiples), `qcu`, `tf` (vrai/faux), `clinical` (cas clinique, avec `vignette`) |
| `answerMode` | `multiple` pour `qcm` ; `single` pour `qcu` et `tf` ; libre pour `clinical` |
| `difficulty` | `1`, `2` ou `3` |
| `priority` / `beeIds` | vrai pour **toute** question d'une notion abeille (badge sur la question et la correction) |
| `propositions` | 2 à 5 ; ids `A`…`E` consécutifs (`V`, `F` pour `tf`) ; chacune porte `correct`, `explanation`, `sourceRefs` (au moins une) |
| `sources` | 1 à 8 citations **« Dans le cours »** (voir ci-dessous) |
| `verify` | `needsReview` = badge « À vérifier » ; `reason` obligatoire dans ce cas |
| `explain` | bouton « Explique-moi » : `text` factuel + `sourceRefs`, et `analogy` (étiquette fixe `hors cours`) |
| `hash`, `widgetFriendly` | calculés par `build` |

**Citation (`SourceRef`)**

| Champ | Règle |
|---|---|
| `id` | étiquette locale `s1`, `s2`… utilisée par `sourceRefs` |
| `sourceId`, `page`, `section` | fichier, page (ou diapo), titre de la section |
| `kind` | `text` : `excerpt` obligatoire. `figure`, `table`, `formula` : `image.bbox` et `alt` obligatoires (`excerpt` facultatif, vérifié s'il existe) |
| `excerpt` | copié tel quel, `[...]` pour sauter un passage |
| `image` | zone de la page à afficher ; `path` ajouté par `build` |

Exemple réel (cours de démo, question n°1) :

```json
{
  "chapterId": "ch_demo_planetes", "notionId": "n_demo_ordre_planetes",
  "type": "qcu", "answerMode": "single", "difficulty": 1,
  "priority": true, "beeIds": ["bee_demo_planetes_p1_01"],
  "stem": "Quelle planète est la plus proche du Soleil ?",
  "propositions": [
    { "id": "A", "text": "Mercure", "correct": true,
      "explanation": "Mercure est citée en premier dans l'ordre à partir du Soleil : c'est la plus proche.",
      "sourceRefs": ["s1"] },
    { "id": "B", "text": "Vénus", "correct": false,
      "explanation": "Vénus vient en deuxième position, juste après Mercure.", "sourceRefs": ["s1"] }
  ],
  "sources": [{ "id": "s1", "sourceId": "src_demo_planetes", "page": 1, "section": "1. Vue d'ensemble", "kind": "text",
    "excerpt": "Le Système solaire compte huit planètes. Dans l'ordre à partir du Soleil : Mercure, Vénus, la Terre, Mars, Jupiter, Saturne, Uranus et Neptune." }],
  "verify": { "needsReview": false }
}
```

### 2.4 Abeille

`Bee` : `sourceId`, `page`, `bbox`, `detection` (`method` : `embedded-image`, `template`, `vector`, `manual`, `synthetic` ; `score`), `attachment` :

| `status` | Sens | Champs |
|---|---|---|
| `attached` | rattachée automatiquement | `notionId`, `anchor` (`sentence`, `paragraph`, `section`, `figure`, `table` + `text` copié tel quel + `bbox`) |
| `ambiguous` | **à valider par toi**, jamais devinée | `candidates` (ancres possibles avec score), `note` |
| `validated` | ambiguïté tranchée par toi | comme `attached` |
| `rejected` | faux positif écarté | n'est plus comptée |

Seules `attached` et `validated` comptent pour `priority`, `beeCount` et `tier`.

### 2.5 Fiche, mnémotechnique

- **Fiche** (`Sheet`) : 1 à 16 `items` (`definition`, `keypoint`, `number`, `classification`, `figure`, `formula`), chacun avec 1 à 3 citations. « Une page maximum » = **1800 caractères** au total (paramètre). Les items abeille viennent en premier, et chaque notion abeille du chapitre doit y figurer.
- **Mnémotechnique** (`Mnemonic`) : `list` (éléments **dans l'ordre du cours**, `ordered`), `sources` (l'extrait où apparaît la liste), `mnemonic` (`kind` : `acronym`, `phrase`, `image` ; `text` ; `mapping` mot par mot vers `itemIndex`, `null` pour un mot de liaison). Affichage : « Mnémotechnique (aide à la mémoire, hors cours) » à côté de la liste exacte.

### 2.6 Règles de validation (`quizpipe validate`)

| Code | Gravité | Contrôle |
|---|---|---|
| `E-FILE` `E-JSON` `E-SCHEMA` | erreur | fichier absent, JSON invalide, non conforme au schéma |
| `E-REF` `E-PAGE` `E-ID-DUP` | erreur | référence inconnue, page hors document, id en double |
| `E-QUOTE` | erreur | extrait (ou passage d'abeille) introuvable **tel quel** sur la page citée |
| `E-PAGES-MISSING` | erreur | texte des pages non extrait (lancer `extract`) |
| `E-ANSWER` | erreur | forme incohérente : vrai/faux ≠ V,F ; QCU ≠ 1 bonne réponse ; QCM non `multiple` ; ids non consécutifs |
| `E-PRIORITY` `E-BEE-LINK` `E-BEE-COUNT` `E-BEE-TIER` | erreur | incohérence abeille ↔ notion ↔ question ↔ chapitre |
| `E-DUP` | erreur | même énoncé et mêmes propositions |
| `E-SHEET` | erreur | fiche trop longue, notion abeille absente, item prioritaire invalide |
| `E-MNEMO` | erreur | liste absente du cours ou dans un autre ordre, élément omis ou ajouté, mauvaise initiale, texte ≠ assemblage des mots |
| `E-HASH` `E-MANIFEST` `E-IMAGE` | erreur | étape `built` : hash, sha256 du manifeste, capture manquante |
| `W-STALE` | avertissement | le cours a changé depuis la génération |
| `W-COVER-EMPTY` `W-COVER-DIFF` `W-COVER-QUOTA` | avertissement | notion sans question, niveau de difficulté manquant, quota non atteint (3 par notion, 6 si abeille) |
| `W-DUP-NEAR` | avertissement | questions quasi identiques (énoncé **et** propositions) |
| `W-SECTION` `W-IMAGE-REGION` `W-SRC-UNUSED` `W-REF-SOURCE` `W-SHEET-ORDER` `W-BEE-AMBIGUOUS` `W-NO-SHEET` `W-ANSWER` | avertissement | section introuvable sur la page, capture qui ne recouvre pas le tableau détecté, citation inutilisée, source hors chapitre, item abeille mal placé, abeille ambiguë sans candidat, chapitre sans fiche, moins de 4 propositions |

## 3. Données utilisateur (SwiftData)

Tout est local, rien ne quitte l'appareil. Les références au contenu sont des ids texte.

| Entité | Champs | Rôle |
|---|---|---|
| `UserSettings` (1 ligne) | `yearCode`, `selectedUEIds`, `dailyReminderEnabled/Hour/Minute`, `newCardsPerDay` (10), `scoringScheme`, `lastSeenContentVersion`, `seenChapterIds`, `onboardingDone` | onboarding, réglages, détection des chapitres ajoutés |
| `CardState` | `questionId` (unique), `phase` (`new`, `learning`, `review`), `ease`, `intervalDays`, `reps`, `lapses`, `due`, `lastReviewAt`, `suspended` | révision espacée |
| `Attempt` | `id`, `questionId`, `notionId`, `chapterId`, `sessionId?`, `date`, `selectedIds`, `errors`, `score`, `grade`, `durationMs`, `mode`, `viewedCourse`, `viewedExplain` | historique brut (statistiques, streak) |
| `Session` | `id`, `mode` (`training`, `exam`, `eve`, `daily`, `review`), `scopeKind`, `scopeIds`, `startedAt`, `finishedAt?`, `timeLimitSec?`, `questionIds`, `score?` | entraînement, examen blanc, veille d'exam |
| `NotionStat` | `notionId` (unique), `attempts`, `correct`, `ema`, `seenQuestionIds`, `lastAttemptAt`, `mastery` | points faibles (cache de l'historique) |
| `Favorite` | `questionId` (unique), `createdAt` | favoris |
| `Note` | `targetKind` (`question`, `notion`, `chapter`), `targetId`, `text`, `updatedAt` | notes personnelles |
| `ErrorReport` | `id`, `questionId`, `category`, `comment`, `createdAt`, `exportedAt?` | « signaler une erreur » : file locale, export JSON par la feuille de partage (aucun serveur) |
| `CustomMnemonic` | `mnemonicId` (unique), `text`, `updatedAt` | mon mnémotechnique à la place de celui du pipeline |
| `StreakDay` | `day` (`yyyy-MM-dd`, heure locale, unique), `attempts` | régularité |
| `DailyRecord` | `day` (unique), `questionId`, `selectedIds`, `isCorrect`, `answeredAt`, `source` (`widget`/`app`) | question du jour |

### 3.1 Règles de calcul

**Révision espacée (SM-2 adapté, une carte par question).** Paramètres regroupés dans `SRSParameters` (testables) : facilité initiale 2,5, minimum 1,3, premiers intervalles 1 puis 3 jours.

| Note | Quand (automatique) | Effet |
|---|---|---|
| `again` | question à réponse unique fausse, ou QCM avec au moins 2 erreurs | `lapses += 1`, facilité −0,20, intervalle 1 jour, la question revient en fin de session (2 fois au plus) |
| `hard` | QCM avec exactement 1 erreur | facilité −0,15, intervalle × 1,2 |
| `good` | réponse exacte | 1 j, puis 3 j, puis intervalle × facilité |
| `easy` | choix manuel « Facile » sur l'écran de correction | facilité +0,15, intervalle × facilité × 1,3 |

Une **erreur** = une proposition cochée à tort ou oubliée. Sur l'écran de correction, un tap facultatif permet de passer en « Difficile » ou « Facile ». Par défaut, tout est automatique : zéro friction.

**Score d'un QCM** (`Scoring`, paramétrable). Par défaut : *tout ou rien* (1 point si exactement les bonnes propositions, sinon 0), en attendant le barème de ta fac (par exemple 1, 0,5, 0,2 selon le nombre d'erreurs).

**Maîtrise d'une notion (0 à 100).** Moyenne mobile exponentielle (α = 0,4) des résultats (1, 0,5, 0) sur les dernières tentatives, multipliée par `0,6 + 0,4 × couverture`, où couverture = `min(1, questions distinctes vues / min(3, questions de la notion))`. Fragile si < 60 (< 70 pour une notion abeille) ou si la dernière tentative est fausse. Sans tentative : « non travaillée ».

**Streak.** Un jour compte s'il compte au moins une tentative (tous modes, question du jour comprise). Le streak courant se compte jusqu'à aujourd'hui, ou jusqu'à hier si aujourd'hui n'est pas encore fait (il ne casse qu'à la fin de la journée).

**Question du jour.** Candidates : questions `widgetFriendly` des UE choisies, pas répondues depuis 7 jours.
`score = 3,0 × abeille + 2,5 × due + 2,0 × (1 − maîtrise/100) + 0,5 × jamais vue − 1,0 × même notion que la veille`, ajouté d'un départage déterministe par date. 14 jours sont pré-calculés à chaque ouverture.

**Veille d'exam** (UE ou module, 15 / 30 / 60 min). Nombre de questions = durée ÷ temps moyen estimé (30 s QCU et vrai/faux, 60 s QCM, ajusté par ton historique). Ordre : (1) notions abeille de maîtrise < 70, de la plus faible à la plus forte ; (2) autres notions de maîtrise < 60 ; (3) complément avec les révisions dues puis les notions abeille jamais vues. Pas plus de 3 questions par notion et pas de question vue depuis moins de 3 jours. Bilan final : notions encore fragiles, avec lien vers la fiche du chapitre.

## 4. Échanges app ↔ widget (App Group)

| Fichier | Écrit par | Contenu |
|---|---|---|
| `daily.json` | app | 14 jours de questions du jour (énoncé, propositions avec `correct`, explication courte, source), dernier état des réponses |
| `outbox/<uuid>.json` | widget (AppIntent) | `{ day, questionId, selectedIds, answeredAt, source: "widget" }` : un fichier par réponse, donc pas de conflit d'écriture |

L'app importe l'outbox au lancement et au retour au premier plan (tentative, révision espacée, streak, `DailyRecord`), puis réécrit `daily.json`.

## 5. Évolution et compatibilité

- Ajouter un cours ajoute des chapitres : les ids existants ne changent pas, la progression est conservée. L'app compare `seenChapterIds` à la taxonomie et affiche « Nouveaux chapitres ».
- Un cours modifié : `W-STALE`, puis seules les questions dont l'extrait n'existe plus sont réécrites. Les autres gardent leur id.
- Une question retirée disparaît du contenu ; son état SwiftData devient orphelin et est ignoré.
- Changement majeur du schéma (`2.x`) : l'app refuse l'ancien contenu et affiche un message clair.
