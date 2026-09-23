"""Turn permit PDFs into page images the vision pipeline can read.

Two kinds of pages show up in real permit sets and they need different
downstream treatment:

  * born-digital CAD exports carry a text layer, so dimensions and room names
    can be read straight out of the PDF;
  * scanned sheets carry none, and everything has to come from OCR.

`has_text` records which is which, so later stages don't have to guess.
"""

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pymupdf

DATA = Path(__file__).resolve().parent.parent / "data"
PERMITS = DATA / "permits"

# Drawing sheets run up to 36x24in. At a fixed 300 dpi that is a 78 megapixel
# image, so pages are rendered to a long-edge pixel budget instead: big sheets
# get the resolution they need without letter-size pages being wastefully large.
MAX_PIXELS = 4000


# A sheet announces what it is in its title block, in the largest text on the
# page: a sheet number ("A101") over a title ("FLOOR PLAN - LEVEL 1"). Reading
# the spans biggest-first means the title block wins over any passing mention
# of "floor plan" in a note.
# Sheet numbers come in many house styles: A101, A-902, A1-101, S1.1, G000.
SHEET_NUMBER = re.compile(r"^[A-Z]{1,2}\d?[-.]?\d{1,3}(\.\d+)?[A-Z]?$")

# Door and window tags ("X27", "M02") look just like sheet numbers but are set
# in small type out in the drawing. The real sheet number lives in the title
# block, which runs down the right edge or along the bottom of the sheet.
TITLE_BLOCK = 0.75

TITLES = (
    ("floor_plan", ("FLOOR PLAN", "LEVEL 1", "LEVEL 2", "MAIN FLOOR", "UPPER FLOOR", "LOWER FLOOR", "LOFT PLAN")),
    ("site_plan", ("SITE PLAN", "SITE & ", "PLOT PLAN")),
    ("roof_plan", ("ROOF PLAN",)),
    ("foundation", ("FOUNDATION", "FRAMING")),
    ("elevation", ("ELEVATION",)),
    ("section", ("SECTION",)),
    ("schedule", ("SCHEDULE",)),
    ("detail", ("DETAIL",)),
    ("notes", ("NOTES", "GENERAL", "CODE", "COVER", "INDEX", "REQUIREMENTS", "MEASURES", "DIAGRAM", "SYMBOL")),
)


def clean(text):
    """Fold ligatures and collapse whitespace so titles match plainly."""
    return " ".join(unicodedata.normalize("NFKD", text).split()).upper()


def text_spans(page):
    """Every text span as (font size, text, x, y), largest first.

    x and y are the span's centre as a fraction of the page, so callers can ask
    where on the sheet the text sits without carrying the page around.
    """
    width, height = page.rect.width, page.rect.height
    spans = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if span["text"].strip():
                    x0, y0, x1, y1 = span["bbox"]
                    spans.append((span["size"], clean(span["text"]),
                                  (x0 + x1) / 2 / width, (y0 + y1) / 2 / height))
    return sorted(spans, key=lambda s: -s[0])


def classify(spans):
    """Guess the sheet number and what kind of drawing the page holds."""
    sheet = next(
        (text for _, text, x, y in spans
         if SHEET_NUMBER.match(text) and (x > TITLE_BLOCK or y > TITLE_BLOCK)),
        None,
    )
    for _, text, _, _ in spans:
        for label, keywords in TITLES:
            if any(k in text for k in keywords):
                return label, sheet
    return None, sheet


@dataclass
class Page:
    pdf: Path
    number: int
    size_in: tuple[float, float]
    has_text: bool
    label: str | None = None
    sheet: str | None = None
    image: Path | None = None

    @property
    def name(self):
        return f"{self.pdf.stem}_p{self.number:03}"


def read_pages(pdf):
    """Describe each page without rendering it."""
    pdf = Path(pdf)
    pages = []
    with pymupdf.open(pdf) as doc:
        for i, page in enumerate(doc):
            spans = text_spans(page)
            label, sheet = classify(spans) if spans else (None, None)
            size = (page.rect.width / 72, page.rect.height / 72)
            pages.append(Page(pdf, i + 1, size, bool(spans), label, sheet))
    return pages


def render(pdf, out_dir=None, max_pixels=MAX_PIXELS):
    """Rasterize every page to a PNG and return the pages with image paths."""
    pdf = Path(pdf)
    out_dir = Path(out_dir or DATA / "pages")
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = read_pages(pdf)
    with pymupdf.open(pdf) as doc:
        for page, source in zip(pages, doc):
            zoom = max_pixels / max(source.rect.width, source.rect.height)
            image = out_dir / f"{page.name}.png"
            source.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(image)
            page.image = image
    return pages


def survey(folder=PERMITS):
    """List every permit page: size, and whether it has a usable text layer."""
    pages = [p for pdf in sorted(Path(folder).glob("*.[pP][dD][fF]")) for p in read_pages(pdf)]
    scanned = [p for p in pages if not p.has_text]
    print(f"{len(pages)} pages in {len(set(p.pdf for p in pages))} pdfs")
    print(f"  {len(scanned)} scanned (no text layer), {len(pages) - len(scanned)} born-digital")
    sizes = sorted({p.size_in for p in pages})
    print(f"  page sizes (in): {sizes}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "survey"
    if command == "survey":
        survey()
    else:
        for page in render(sys.argv[2]):
            print(page.image, f"{page.size_in[0]:.0f}x{page.size_in[1]:.0f}in", "text" if page.has_text else "scanned")
