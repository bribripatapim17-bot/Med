# QuizMed : quiz de révision pour les études de médecine (iOS)

Application iOS 17+ (SwiftUI, SwiftData, WidgetKit) dont **tout le contenu vient des cours** de la fac, avec une traçabilité vérifiée : chaque question cite l'extrait exact du cours, son fichier, sa page et sa section.

| Dossier | Contenu | État |
|---|---|---|
| `docs/` | architecture, schéma de données | livrable 2 |
| `schemas/content.schema.json` | format JSON du contenu (source de vérité) | livrable 2 |
| `pipeline/quizpipe/` | pipeline Python : `extract`, `validate`, `stamp` | livrable 2 (tests : 40) |
| `demo/` | cours de démonstration **fictif et non médical** + contenu de test | livrable 2 |
| `ios/` | projet Xcode (XcodeGen), package `QuizCore`, app, widget | livrable 3 |

## Lancer le pipeline (Windows, PowerShell)

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "pipeline"

# 1. générer le PDF de démo et extraire son texte
.venv\Scripts\python.exe demo\make_demo_course.py
.venv\Scripts\python.exe -m quizpipe extract "demo\sources\Demo\S1\UE D1 - Astronomie\Chapitre 1 - Les planetes.pdf" --source-id src_demo_planetes --out demo\work\pages --render-dpi 80

# 2. écrire le contenu de démo, poser l'empreinte du cours, valider
.venv\Scripts\python.exe demo\author_demo_content.py
.venv\Scripts\python.exe -m quizpipe stamp    --content demo\content --work demo\work
.venv\Scripts\python.exe -m quizpipe validate --content demo\content --work demo\work --min-normal 2 --min-bee 3

# 3. tests
.venv\Scripts\python.exe -m pytest pipeline\tests -q
```

Les quotas `--min-normal 2 --min-bee 3` sont réduits pour la démo ; les valeurs par défaut sont 3 et 6.

## Environnement

Python 3.13, `pymupdf`, `jsonschema`, `pytest` (installés dans `.venv`). OpenCV s'ajoutera avec la détection d'abeilles (livrable 1).
