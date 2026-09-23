"""Turn permit PDFs into page images the vision pipeline can read.

Two kinds of pages show up in real permit sets and they need different
downstream treatment:

  * born-digital CAD exports carry a text layer, so dimensions and room names
    can be read straight out of the PDF;
  * scanned sheets carry none, and everything has to come from OCR.

`has_text` records which is which, so later stages don't have to guess.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import pymupdf

DATA = Path(__file__).resolve().parent.parent / "data"
PERMITS = DATA / "permits"

# Drawing sheets run up to 36x24in. At a fixed 300 dpi that is a 78 megapixel
# image, so pages are rendered to a long-edge pixel budget instead: big sheets
# get the resolution they need without letter-size pages being wastefully large.
MAX_PIXELS = 4000


@dataclass
class Page:
    pdf: Path
    number: int
    size_in: tuple[float, float]
    has_text: bool
    image: Path | None = None

    @property
    def name(self):
        return f"{self.pdf.stem}_p{self.number:03}"


def read_pages(pdf):
    """Describe each page without rendering it."""
    pdf = Path(pdf)
    with pymupdf.open(pdf) as doc:
        return [
            Page(pdf, i + 1, (page.rect.width / 72, page.rect.height / 72), bool(page.get_text().strip()))
            for i, page in enumerate(doc)
        ]


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
