"""Extraction d'un PDF de cours : texte par page, blocs positionnés, images, tableaux.

Tout vient du PDF, rien n'est deviné. La sortie (work/pages/<sourceId>.pages.json) sert à :
  - vérifier que chaque extrait « Dans le cours » existe tel quel sur la page citée ;
  - rattacher les abeilles aux blocs de texte (étape bees) ;
  - proposer l'arborescence (étape structure).
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pymupdf

from . import SCHEMA_VERSION


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_bbox(b, w: float, h: float) -> list[float]:
    """(x0, y0, x1, y1) en points -> [x, y, largeur, hauteur] normalisés 0..1, origine en haut à gauche."""
    x0, y0, x1, y1 = b
    x = min(max(x0 / w, 0.0), 1.0)
    y = min(max(y0 / h, 0.0), 1.0)
    bw = min(max((x1 - x0) / w, 0.0), 1.0 - x)
    bh = min(max((y1 - y0) / h, 0.0), 1.0 - y)
    return [round(x, 4), round(y, 4), round(bw, 4), round(bh, 4)]


def _is_bold(span: dict) -> bool:
    return bool(span["flags"] & 16) or "bold" in span["font"].lower()


def _body_font_size(doc: pymupdf.Document) -> float:
    counts: Counter[float] = Counter()
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    counts[round(span["size"], 1)] += len(span["text"].strip())
    return counts.most_common(1)[0][0] if counts else 11.0


def extract_pdf(pdf_path: Path, source_id: str, out_dir: Path | None = None) -> dict:
    """Extrait un PDF. Écrit <out_dir>/<source_id>.pages.json si out_dir est fourni."""
    doc = pymupdf.open(pdf_path)
    body = _body_font_size(doc)
    pages = []
    text_chars = 0
    for pno, page in enumerate(doc, start=1):
        w, h = page.rect.width, page.rect.height
        blocks = []
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            spans = [s for line in block["lines"] for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = "\n".join("".join(s["text"] for s in line["spans"]) for line in block["lines"]).strip()
            size = max(s["size"] for s in spans)
            bold = all(_is_bold(s) for s in spans)
            single_line = len(block["lines"]) == 1
            heading = size >= body * 1.15 or (bold and single_line and len(text) <= 90)
            blocks.append({
                "id": f"p{pno}b{len(blocks) + 1}",
                "bbox": norm_bbox(block["bbox"], w, h),
                "text": text,
                "fontSize": round(size, 1),
                "bold": bold,
                "heading": heading,
            })
        images = [
            {"bbox": norm_bbox(i["bbox"], w, h), "digest": i["digest"].hex() if isinstance(i["digest"], bytes) else str(i["digest"]),
             "width": i["width"], "height": i["height"]}
            for i in page.get_image_info(hashes=True)
        ]
        tables = []
        for t in page.find_tables().tables:
            tables.append({"bbox": norm_bbox(t.bbox, w, h), "rows": t.extract()})
        text = page.get_text("text")
        text_chars += len(text.strip())
        pages.append({"page": pno, "width": round(w, 2), "height": round(h, 2), "text": text,
                      "blocks": blocks, "images": images, "tables": tables})
    result = {
        "schemaVersion": SCHEMA_VERSION,
        "sourceId": source_id,
        "file": {"name": pdf_path.name, "sha256": sha256_file(pdf_path), "bytes": pdf_path.stat().st_size},
        "pageCount": doc.page_count,
        "textLayer": text_chars >= 20 * doc.page_count,
        "bodyFontSize": body,
        "pages": pages,
    }
    doc.close()
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{source_id}.pages.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def render_pages(pdf_path: Path, out_dir: Path, dpi: int = 150) -> list[Path]:
    """Rasterise chaque page en PNG (p001.png, p002.png...). Sert à l'inspection et à la détection d'abeilles."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with pymupdf.open(pdf_path) as doc:
        for pno, page in enumerate(doc, start=1):
            target = out_dir / f"p{pno:03d}.png"
            page.get_pixmap(dpi=dpi).save(target)
            paths.append(target)
    return paths
