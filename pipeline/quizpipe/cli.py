"""Ligne de commande : python -m quizpipe <commande> (extract, validate, stamp)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .extract import extract_pdf, render_pages
from .validate import Config, stamp_content, validate_content


def _cmd_extract(a: argparse.Namespace) -> int:
    out = Path(a.out)
    res = extract_pdf(Path(a.pdf), a.source_id, out)
    layer = "oui" if res["textLayer"] else "NON (PDF scanné : OCR requis avant génération)"
    print(f"{a.source_id} : {res['pageCount']} page(s), couche texte : {layer}")
    print(f"-> {out / (a.source_id + '.pages.json')}")
    if a.render_dpi:
        paths = render_pages(Path(a.pdf), out.parent / "render" / a.source_id, a.render_dpi)
        print(f"{len(paths)} image(s) dans {paths[0].parent}")
    return 0


def _cmd_validate(a: argparse.Namespace) -> int:
    cfg = Config(min_questions_normal=a.min_normal, min_questions_bee=a.min_bee)
    report = validate_content(Path(a.content), Path(a.work), a.stage, cfg)
    for issue in report.issues:
        print(issue)
    if report.ambiguous_bees:
        print(f"abeilles ambiguës à valider : {', '.join(report.ambiguous_bees)}")
    print()
    for k, v in report.stats.items():
        print(f"  {k:<34} {v}")
    verdict = "ÉCHEC" if report.errors else "OK"
    print(f"\n{verdict} : {len(report.errors)} erreur(s), {len(report.warnings)} avertissement(s) [étape {a.stage}]")
    if a.report:
        Path(a.report).write_text(report.render_markdown(), encoding="utf-8")
        print(f"rapport : {a.report}")
    return 1 if report.errors else 0


def _cmd_stamp(a: argparse.Namespace) -> int:
    for line in stamp_content(Path(a.content), Path(a.work)):
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="quizpipe", description="Pipeline de contenu QuizMed")
    ap.add_argument("--version", action="version", version=f"quizpipe {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="extraire le texte, les blocs, les images et les tableaux d'un PDF")
    e.add_argument("pdf")
    e.add_argument("--source-id", required=True, help="identifiant de la source (src_...)")
    e.add_argument("--out", required=True, help="dossier work/pages")
    e.add_argument("--render-dpi", type=int, help="rasteriser aussi les pages en PNG à cette résolution")
    e.set_defaults(func=_cmd_extract)

    v = sub.add_parser("validate", help="valider le contenu (schéma + traçabilité + règles métier)")
    v.add_argument("--content", required=True, help="dossier contenant taxonomy.json, sources.json, bees.json, chapters/")
    v.add_argument("--work", required=True, help="dossier work (contient pages/)")
    v.add_argument("--stage", choices=["generated", "built"], default="generated")
    v.add_argument("--min-normal", type=int, default=3, help="questions minimum par notion standard")
    v.add_argument("--min-bee", type=int, default=6, help="questions minimum par notion abeille")
    v.add_argument("--report", help="écrire un rapport Markdown")
    v.set_defaults(func=_cmd_validate)

    s = sub.add_parser("stamp", help="poser gen.sourceHash (empreinte du cours) sur les packs générés")
    s.add_argument("--content", required=True)
    s.add_argument("--work", required=True)
    s.set_defaults(func=_cmd_stamp)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
