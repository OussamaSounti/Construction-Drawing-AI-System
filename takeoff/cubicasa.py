"""CubiCasa5k: download and extract the dataset."""

import hashlib
import sys
import urllib.request
from pathlib import Path
from zipfile import ZipFile

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
    """Fetch the archive, resuming if a partial download is already on disk."""
    DATA.mkdir(exist_ok=True)
    total = _total_size()
    done = ARCHIVE.stat().st_size if ARCHIVE.exists() else 0
    if done >= total:
        print(f"already downloaded: {ARCHIVE}")
        return

    request = urllib.request.Request(URL, headers={"Range": f"bytes={done}-"})
    with urllib.request.urlopen(request) as response, open(ARCHIVE, "ab") as f:
        while chunk := response.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            print(f"\r{done / 1e9:.2f} / {total / 1e9:.2f} GB", end="", flush=True)
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


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "download"
    {"download": download, "verify": verify, "extract": extract}[command]()
