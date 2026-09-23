"""CubiCasa5k: download the dataset and load its annotations."""

import hashlib
import sys
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from lxml import etree
from PIL import Image, ImageDraw

URL = "https://zenodo.org/api/records/2613548/files/cubicasa5k.zip/content"
MD5 = "0ce0b203d1e3c125b51087b219bd23b9"

DATA = Path(__file__).resolve().parent.parent / "data"
ARCHIVE = DATA / "cubicasa5k.zip"
ROOT = DATA / "cubicasa5k"


def _total_size():
    request = urllib.request.Request(URL, method="HEAD")
    with urllib.request.urlopen(request) as response:
        return int(response.headers["Content-Length"])


def download():
    """Fetch the archive, resuming until every byte is on disk.

    Zenodo drops the connection long before a 5.5 GB transfer finishes, and the
    read just returns empty rather than raising, so a single pass looks like a
    clean finish at whatever point it died. Reconnect with a Range header until
    the file on disk actually matches the advertised size.
    """
    DATA.mkdir(exist_ok=True)
    total = _total_size()
    done = ARCHIVE.stat().st_size if ARCHIVE.exists() else 0

    while done < total:
        request = urllib.request.Request(URL, headers={"Range": f"bytes={done}-"})
        with urllib.request.urlopen(request) as response, open(ARCHIVE, "ab") as f:
            while chunk := response.read(1 << 20):
                f.write(chunk)
                done += len(chunk)
                print(f"\r{done / 1e9:.2f} / {total / 1e9:.2f} GB", end="", flush=True)
        if done < total:
            print(f"\nconnection dropped at {done / 1e9:.2f} GB, resuming")

    print(f"\nsaved to {ARCHIVE}")


def verify():
    """Check the archive against the checksum Zenodo publishes."""
    digest = hashlib.md5()
    with open(ARCHIVE, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    ok = digest.hexdigest() == MD5
    print("checksum ok" if ok else f"CHECKSUM MISMATCH: {digest.hexdigest()}")
    return ok


def extract():
    """Unpack the archive into data/cubicasa5k/."""
    with ZipFile(ARCHIVE) as archive:
        archive.extractall(DATA)
    print(f"extracted to {ROOT}")




# --- loading annotations ---------------------------------------------------
#
# Every object is a <g> whose class attribute starts with its type, e.g.
# "Wall External", "Door Swing Beside", "Window Regular", "Space Bath". The
# outline is that group's first direct <polygon> child. Doors and windows are
# nested inside their wall, so iterating every <g> yields each of them once.
#
# Coordinates need no transform: they are already pixel positions in
# F1_scaled.png. The SVG width/height often differ from the image size, and
# rescaling by that ratio (a common shortcut) shifts every annotation off the
# drawing, progressively worse toward the right and bottom edges.

KINDS = {"Wall": "Wall", "Door": "Door", "Window": "Window", "Space": "Room"}


@dataclass
class Element:
    kind: str
    subtype: str
    points: list[tuple[float, float]]

    @property
    def bbox(self):
        xs = [x for x, _ in self.points]
        ys = [y for _, y in self.points]
        return min(xs), min(ys), max(xs), max(ys)


@dataclass
class Sample:
    folder: Path
    image: Path
    elements: list[Element]

    def of(self, kind):
        return [e for e in self.elements if e.kind == kind]


def load_sample(folder):
    """Read one floor plan and its annotations."""
    folder = Path(folder)
    root = etree.parse(str(folder / "model.svg")).getroot()
    elements = []
    for group in root.iter("{*}g"):
        tokens = (group.get("class") or "").split()
        if not tokens or tokens[0] not in KINDS:
            continue
        polygon = group.find("{*}polygon")
        if polygon is None:
            continue
        points = [tuple(map(float, xy.split(","))) for xy in polygon.get("points").split()]
        elements.append(Element(KINDS[tokens[0]], " ".join(tokens[1:]), points))
    return Sample(folder, folder / "F1_scaled.png", elements)


def iter_samples(split="train"):
    """Yield every sample listed in train.txt / val.txt / test.txt."""
    for line in (ROOT / f"{split}.txt").read_text().split():
        yield load_sample(ROOT / line.strip("/"))


COLORS = {"Wall": (255, 0, 0), "Door": (0, 160, 0), "Window": (0, 80, 255), "Room": (255, 140, 0)}


def preview(sample, path):
    """Draw a sample's annotations over its floor plan, to eyeball alignment."""
    image = Image.open(sample.image).convert("RGB")
    draw = ImageDraw.Draw(image)
    for element in sample.elements:
        draw.polygon(element.points, outline=COLORS[element.kind], width=4)
    image.thumbnail((1400, 1400))
    image.save(path)


def stats(split="train"):
    """Count annotations across a split and write a few preview overlays."""
    counts = Counter()
    rooms = Counter()
    total = 0
    previews = DATA / "previews"
    previews.mkdir(exist_ok=True)

    for sample in iter_samples(split):
        total += 1
        counts.update(e.kind for e in sample.elements)
        rooms.update(e.subtype for e in sample.of("Room"))
        if total <= 3:
            preview(sample, previews / f"{split}_{sample.folder.name}.png")

    print(f"{split}: {total} samples")
    for kind, n in counts.most_common():
        print(f"  {kind:7} {n:7}  ({n / total:.1f} per plan)")
    print("  top rooms:", ", ".join(f"{r}={n}" for r, n in rooms.most_common(8)))
    print(f"  previews written to {previews}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "download"
    {"download": download, "verify": verify, "extract": extract, "stats": stats}[command](*sys.argv[2:])
