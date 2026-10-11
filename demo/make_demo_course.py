"""Génère le cours de DÉMONSTRATION (fictif, non médical) : un PDF de 3 pages sur les planètes.

Sert à tester toute la chaîne (extraction, validation, plus tard détection d'abeilles et app iOS) sans cours réel.
Il écrit aussi la « vérité terrain » des abeilles dessinées (bees.json) et sources.json, que le futur détecteur
devra retrouver. Aucune information médicale ici.

    python demo/make_demo_course.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent
PDF_REL = "Demo/S1/UE D1 - Astronomie/Chapitre 1 - Les planetes.pdf"
PDF_PATH = ROOT / "sources" / PDF_REL
SOURCE_ID = "src_demo_planetes"

W, H = 595.0, 842.0
LEFT, RIGHT = 70.0, 525.0
WIDTH = RIGHT - LEFT
GRAY = (0.45, 0.45, 0.45)


def nb(rect: pymupdf.Rect) -> list[float]:
    """Rect en points -> [x, y, largeur, hauteur] normalisés."""
    return [round(rect.x0 / W, 4), round(rect.y0 / H, 4), round(rect.width / W, 4), round(rect.height / H, 4)]


def text(page, y, s, size=11.0, bold=False, x=LEFT, w=WIDTH, color=(0, 0, 0), align=0) -> pymupdf.Rect:
    rect = pymupdf.Rect(x, y, x + w, y + 300)
    rc = page.insert_textbox(rect, s, fontsize=size, fontname="hebo" if bold else "helv", color=color, align=align)
    if rc < 0:
        raise RuntimeError(f"texte trop long : {s[:40]}")
    return pymupdf.Rect(x, y, x + w, y + 300 - rc)


def draw_bee(page, x, y, s=22.0) -> pymupdf.Rect:
    """Abeille vectorielle simple : ailes bleutées, corps jaune rayé de noir."""
    sh = page.new_shape()
    for x0, x1 in ((0.16, 0.50), (0.46, 0.82)):
        sh.draw_oval(pymupdf.Rect(x + x0 * s, y, x + x1 * s, y + 0.40 * s))
        sh.finish(fill=(0.75, 0.88, 1.0), color=(0.35, 0.5, 0.7), width=0.5)
    sh.draw_oval(pymupdf.Rect(x + 0.06 * s, y + 0.30 * s, x + 0.94 * s, y + 0.90 * s))
    sh.finish(fill=(1.0, 0.78, 0.1), color=(0.2, 0.15, 0.0), width=0.8)
    for fx in (0.38, 0.55, 0.72):
        sh.draw_line((x + fx * s, y + 0.36 * s), (x + fx * s, y + 0.84 * s))
        sh.finish(color=(0.1, 0.1, 0.1), width=1.8, closePath=False)
    sh.draw_circle((x + 0.17 * s, y + 0.56 * s), 0.07 * s)
    sh.finish(fill=(0.1, 0.1, 0.1), color=(0.1, 0.1, 0.1), width=0.3)
    sh.commit()
    return pymupdf.Rect(x, y, x + s, y + s)


def table(page, y, rows, col_w, row_h=24.0, size=10.0) -> pymupdf.Rect:
    sh = page.new_shape()
    for r in range(len(rows)):
        cx = LEFT
        for c in range(len(col_w)):
            sh.draw_rect(pymupdf.Rect(cx, y + r * row_h, cx + col_w[c], y + (r + 1) * row_h))
            sh.finish(color=(0, 0, 0), width=0.8, fill=(0.92, 0.92, 0.92) if r == 0 else None)
            cx += col_w[c]
    sh.commit()
    for r, row in enumerate(rows):
        cx = LEFT
        for c, cell in enumerate(row):
            page.insert_text((cx + 6, y + r * row_h + 16), cell, fontsize=size, fontname="hebo" if r == 0 else "helv")
            cx += col_w[c]
    return pymupdf.Rect(LEFT, y, LEFT + sum(col_w), y + len(rows) * row_h)


def header(page) -> None:
    text(page, 28, "UE D1 - Astronomie  |  Module 1 : Le Système solaire  |  COURS DE DÉMONSTRATION (fictif)",
         size=8.5, color=GRAY)


def build() -> dict:
    doc = pymupdf.open()
    anchors: dict[str, dict] = {}

    # ---------------------------------------------------------------- page 1
    p1 = doc.new_page(width=W, height=H)
    header(p1)
    text(p1, 56, "Chapitre 1 - Les planètes", size=20, bold=True)
    text(p1, 104, "1. Vue d'ensemble", size=14, bold=True)
    s_ordre = ("Le Système solaire compte huit planètes. Dans l'ordre à partir du Soleil : Mercure, Vénus, "
               "la Terre, Mars, Jupiter, Saturne, Uranus et Neptune.")
    r = text(p1, 130, s_ordre)
    bee1 = draw_bee(p1, 36, r.y0 + 1)
    anchors["ordre"] = {"text": s_ordre, "rect": r}
    text(p1, 196, "2. Classification des planètes", size=14, bold=True)
    s_tell = ("Les planètes telluriques (Mercure, Vénus, la Terre et Mars) sont rocheuses et possèdent une surface "
              "solide. On distingue trois catégories de planètes selon leur composition principale (tableau "
              "ci-dessous).")
    text(p1, 222, s_tell)
    tbl = table(p1, 290, [
        ["Catégorie", "Planètes", "Composition principale"],
        ["Telluriques", "Mercure, Vénus, Terre, Mars", "Roches et métaux"],
        ["Géantes gazeuses", "Jupiter, Saturne", "Hydrogène et hélium"],
        ["Géantes de glaces", "Uranus, Neptune", "Glaces (eau, ammoniac, méthane)"],
    ], col_w=[110, 160, 185])
    anchors["tableau"] = {"rect": tbl}

    # ---------------------------------------------------------------- page 2
    p2 = doc.new_page(width=W, height=H)
    header(p2)
    text(p2, 56, "3. Les planètes géantes", size=14, bold=True)
    s_geantes = ("Jupiter et Saturne sont des géantes gazeuses, composées principalement d'hydrogène et d'hélium. "
                 "Uranus et Neptune sont des géantes de glaces.")
    text(p2, 82, s_geantes)
    text(p2, 140, "4. Quelques records", size=14, bold=True)
    s_r1 = "Jupiter est la plus grande planète du Système solaire. Mercure est la plus petite."
    text(p2, 166, s_r1)
    s_venus = "Vénus est la planète la plus chaude du Système solaire, avec une température de surface d'environ 465 °C."
    r = text(p2, 206, s_venus)
    bee2 = draw_bee(p2, 540, r.y0 + 1)
    anchors["venus"] = {"text": s_venus, "rect": r}

    # ---------------------------------------------------------------- page 3
    p3 = doc.new_page(width=W, height=H)
    header(p3)
    text(p3, 56, "5. Mouvements des planètes", size=14, bold=True)
    s_annee = "La Terre met environ 365,25 jours pour effectuer un tour autour du Soleil."
    r_annee = text(p3, 82, s_annee)
    s_uranus = ("L'axe de rotation d'Uranus est incliné d'environ 98° : la planète tourne pour ainsi dire couchée "
                "sur le côté.")
    r_uranus = text(p3, r_annee.y1 + 6, s_uranus)
    gap_mid = (r_annee.y1 + r_uranus.y0) / 2
    bee3 = draw_bee(p3, 36, gap_mid - 11)
    anchors["annee"] = {"text": s_annee, "rect": r_annee}
    anchors["uranus"] = {"text": s_uranus, "rect": r_uranus}
    text(p3, 170, "6. Troisième loi de Kepler", size=14, bold=True)
    text(p3, 196, "Pour une planète en orbite autour du Soleil, le carré de la période orbitale est proportionnel "
                  "au cube du demi-grand axe de l'orbite :")
    box = pymupdf.Rect(LEFT + 110, 246, LEFT + 345, 304)
    sh = p3.new_shape()
    sh.draw_rect(box)
    sh.finish(color=(0, 0, 0), width=1.0, fill=(0.97, 0.97, 0.9))
    sh.commit()
    text(p3, 252, "T² = a³", size=20, bold=True, x=box.x0, w=box.width, align=1)
    text(p3, 284, "(T en années, a en unités astronomiques)", size=9, x=box.x0, w=box.width, align=1)
    anchors["kepler"] = {"rect": box}
    text(p3, 322, "Exemple : une planète située à 1 UA du Soleil a une période de 1 an.")

    doc.set_toc([
        [1, "Chapitre 1 - Les planètes", 1], [2, "1. Vue d'ensemble", 1], [2, "2. Classification des planètes", 1],
        [2, "3. Les planètes géantes", 2], [2, "4. Quelques records", 2],
        [2, "5. Mouvements des planètes", 3], [2, "6. Troisième loi de Kepler", 3],
    ])
    doc.set_metadata({"title": "Chapitre 1 - Les planètes (démo fictive, non médicale)", "author": "QuizMed démo"})
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(PDF_PATH, garbage=3, deflate=True)
    doc.close()

    bees = [
        {"id": "bee_demo_planetes_p1_01", "sourceId": SOURCE_ID, "page": 1, "bbox": nb(bee1),
         "detection": {"method": "synthetic", "score": 1.0},
         "attachment": {"status": "attached", "notionId": "n_demo_ordre_planetes",
                        "anchor": {"kind": "paragraph", "text": anchors["ordre"]["text"], "bbox": nb(anchors["ordre"]["rect"])}}},
        {"id": "bee_demo_planetes_p2_01", "sourceId": SOURCE_ID, "page": 2, "bbox": nb(bee2),
         "detection": {"method": "synthetic", "score": 1.0},
         "attachment": {"status": "attached", "notionId": "n_demo_records",
                        "anchor": {"kind": "sentence", "text": anchors["venus"]["text"], "bbox": nb(anchors["venus"]["rect"])}}},
        {"id": "bee_demo_planetes_p3_01", "sourceId": SOURCE_ID, "page": 3, "bbox": nb(bee3),
         "detection": {"method": "synthetic", "score": 1.0},
         "attachment": {"status": "ambiguous",
                        "candidates": [
                            {"anchor": {"kind": "paragraph", "text": anchors["annee"]["text"], "bbox": nb(anchors["annee"]["rect"])}, "score": 0.52},
                            {"anchor": {"kind": "paragraph", "text": anchors["uranus"]["text"], "bbox": nb(anchors["uranus"]["rect"])}, "score": 0.48}],
                        "note": "Abeille entre deux paragraphes : année terrestre ou axe d'Uranus ?"}},
    ]
    geometry = {"kepler_box": nb(anchors["kepler"]["rect"]), "table": nb(anchors["tableau"]["rect"])}
    return {"bees": bees, "geometry": geometry}


def main() -> None:
    out = build()
    sha = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()
    content = ROOT / "content"
    content.mkdir(exist_ok=True)
    (content / "bees.json").write_text(
        json.dumps({"schemaVersion": "1.0.0", "bees": out["bees"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (content / "sources.json").write_text(json.dumps({"schemaVersion": "1.0.0", "sources": [{
        "id": SOURCE_ID, "fileName": PDF_PATH.name, "relPath": PDF_REL, "fileType": "pdf",
        "sha256": sha, "pageCount": 3, "textLayer": True}]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PDF :", PDF_PATH)
    print("sha256 :", sha)
    print("géométrie (à reporter dans les captures) :", json.dumps(out["geometry"]))


if __name__ == "__main__":
    main()
