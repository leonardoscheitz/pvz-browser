"""Build the static site from the repository's GOTY resources and a pinned web engine."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "vendor" / "pvz-portable-2493154.zip"
ENGINE_SHA256 = "3a215c83f7544c7967253fe282ab86a5872f99daea7303ce5871f09cdb78d9e8"
RESOURCE_DIRS = {"images", "data", "particles", "reanim", "sounds", "compiled"}
PAK_PART_BYTES = 2 * 1024 * 1024
XOR = bytes(value ^ 0xF7 for value in range(256))


def publish_file(site, stem, extension, data):
    digest = hashlib.sha256(data).hexdigest()[:16]
    path = f"assets/{stem}-{digest}.{extension}"
    (site / path).write_bytes(data)
    return {"url": path, "size": len(data)}


def engine_archive():
    data = ENGINE.read_bytes()
    if hashlib.sha256(data).hexdigest() != ENGINE_SHA256:
        raise ValueError(f"SHA-256 incorreto para o motor em {ENGINE}")
    return ZipFile(io.BytesIO(data))


def pack_resources(site, archive):
    # The engine's native PAK index has case-insensitive names and little-endian fields.
    entries = sorted((i for i in archive.infolist() if not i.is_dir()
                      and i.filename.partition("/")[0] in RESOURCE_DIRS),
                     key=lambda i: i.filename.casefold())
    header = io.BytesIO()
    header.write(struct.pack("<II", 0xBAC04AC0, 0))
    for entry in entries:
        name = entry.filename.encode("ascii")
        header.write(struct.pack("BB", 0, len(name)) + name)
        header.write(struct.pack("<IQ", entry.file_size, 0))
    header.write(b"\x80")
    parts = []
    with tempfile.TemporaryFile() as pak:
        pak.write(header.getvalue().translate(XOR))
        for entry in entries:
            pak.write(archive.read(entry).translate(XOR))
        raw_size = pak.tell()
        pak.seek(0)
        while raw := pak.read(PAK_PART_BYTES):
            output = io.BytesIO()
            with gzip.GzipFile(fileobj=output, mode="wb", compresslevel=9, mtime=0) as compressed:
                compressed.write(raw)
            part = publish_file(site, "lawn", "bin", output.getvalue())
            parts.append({**part, "offset": pak.tell() - len(raw), "rawSize": len(raw)})
    return {"parts": parts, "size": sum(p["size"] for p in parts), "rawSize": raw_size}


def build(site):
    (site / "assets").mkdir()
    with engine_archive() as engine:
        glue = publish_file(site, "engine", "js", engine.read("pvz-portable.js"))
        wasm = publish_file(site, "engine-wasm", "bin",
                            gzip.compress(engine.read("pvz-portable.wasm"), compresslevel=9, mtime=0))
    with ZipFile(ROOT / "modern" / "pvz-goty.zip") as archive:
        pak = pack_resources(site, archive)
        properties = []
        for path in sorted(archive.namelist()):
            if path.startswith("properties/") and not path.endswith("/"):
                entry = publish_file(site, Path(path).stem, Path(path).suffix[1:], archive.read(path))
                properties.append({**entry, "path": path})
        skin = {
            "BACKGROUND": "titlescreen.jpg", "LOGO": "PvZ_Logo.jpg", "ALPHA": "PvZ_Logo_.png",
            "DIRT": "LoadBar_dirt.png", "GRASS": "LoadBar_grass.png",
        }
        art = {key: publish_file(site, "title-" + key.lower(), Path(name).suffix[1:],
                                 archive.read("images/" + name))["url"] for key, name in skin.items()}

    manifest = {"glue": glue, "wasm": wasm, "pak": pak, "properties": properties}
    storage = publish_file(site, "saves", "js", (ROOT / "saves.js").read_bytes())
    script = (ROOT / "game.js").read_text(encoding="utf-8").replace("./saves.js", "./" + Path(storage["url"]).name)
    game = publish_file(site, "game", "js", script.encode("utf-8"))
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    replacements = {**art, "CONFIG": json.dumps(manifest, separators=(",", ":")), "SCRIPT": game["url"]}
    for key, value in replacements.items():
        page = page.replace("{{" + key + "}}", value)
    (site / "index.html").write_text(page, encoding="utf-8")
    (site / ".nojekyll").touch()
    shutil.copytree(ROOT / "licenses", site / "licenses")
    shutil.copy(ROOT / "README.txt", site / "README.txt")
    # Old bookmarks should launch the native game too. They never need Wine's files.
    legacy = site / "modern"
    legacy.mkdir()
    (legacy / "boxedwine.html").write_text(
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Plants vs. Zombies</title>'
        '<meta http-equiv="refresh" content="0;url=../"><a href="../">Jogar Plants vs. Zombies</a></html>',
        encoding="utf-8")
    total = sum(p.stat().st_size for p in (site / "assets").iterdir())
    print(f"Recursos web: {total:,} bytes. Pacote do jogo: {pak['size']:,} bytes.")


if __name__ == "__main__":
    dest = ROOT / "dist"
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        staging = Path(tmp) / "site"
        staging.mkdir()
        build(staging)
        previous = Path(tmp) / "previous"
        if dest.exists():
            dest.rename(previous)
        try:
            os.replace(staging, dest)
        except OSError:
            if previous.exists():
                previous.rename(dest)
            raise
