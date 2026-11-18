"""Offline library packer. Run: python3 pack_library.py <package> [extra...]

На машине С интернетом:
  python3 pack_library.py requests
  python3 pack_library.py django==4.2 --chunk-mb 20
  python3 pack_library.py numpy pandas -r requirements.txt

Скачивает wheels (+ зависимости), упаковывает в base64 .txt,
при необходимости режет на чанки < 25 МБ (лимит почты).

Первая строка файла — НЕ shebang (почта режет #!).
Отправляйте только *.txt на офлайн-машину.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


DEFAULT_CHUNK_MB = 20  # запас до лимита письма 25 МБ


def die(msg: str) -> None:
    print("ОШИБКА:", msg, file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        die(f"команда завершилась с кодом {r.returncode}: {' '.join(cmd)}")


def download_wheels(packages: list[str], req_file: str | None, dest: Path, py_ver: str | None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "download", "-d", str(dest)]
    if py_ver:
        cmd += ["--python-version", py_ver]
    if req_file:
        cmd += ["-r", req_file]
    cmd += packages
    if not packages and not req_file:
        die("Укажите пакет(ы) или -r requirements.txt")
    run(cmd)
    whls = list(dest.glob("*.whl")) + list(dest.glob("*.tar.gz"))
    if not whls:
        die(f"В {dest} ничего не скачалось")
    print(f"Скачано файлов: {len(whls)}")


def make_tarball(wheels_dir: Path, tar_path: Path, meta: dict[str, str]) -> None:
    # кладём meta.txt + все пакеты
    meta_path = wheels_dir / "_pack_meta.txt"
    lines = [f"{k}={v}" for k, v in meta.items()]
    meta_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with tarfile.open(tar_path, "w:gz") as tf:
        for p in sorted(wheels_dir.iterdir()):
            if p.is_file():
                tf.add(p, arcname=p.name)


def write_chunk_file(path: Path, kind: str, digest: str, size: int, body: str, part: str | None = None) -> None:
    """Первая строка — обычный текст, БЕЗ #!"""
    header = f"PyLib-mail-pack kind={kind} sha256={digest} bytes={size}"
    if part is not None:
        header += f" part={part}"
    path.write_text(
        header
        + "\n"
        + f"RESTORE: python3 unpack_library.py {path.name if part is None else 'PyLib-*-part*.txt'}\n"
        + "BEGIN\n"
        + body
        + ("\n" if not body.endswith("\n") else "")
        + "END\n",
        encoding="utf-8",
    )
    first = path.read_text(encoding="utf-8").splitlines()[0]
    if first.startswith("#!"):
        die(f"BUG: shebang in {path}")


def pack(tar_path: Path, out_dir: Path, kind: str, chunk_mb: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = tar_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    size = len(raw)
    b64 = base64.b64encode(raw).decode("ascii")
    print(f"payload: {size} bytes, sha256={digest}")
    print(f"base64:  {len(b64)} chars")

    # копируем распаковщик рядом (без shebang — у него docstring первой строкой)
    unpack_src = Path(__file__).resolve().parent / "unpack_library.py"
    if unpack_src.is_file():
        # имя только .txt — почта режет .py
        target = out_dir / "unpack_library.txt"
        text = unpack_src.read_text(encoding="utf-8")
        if text.startswith("#!"):
            text = text.split("\n", 1)[1]
            if not text.lstrip().startswith('"""'):
                text = '"""Offline library unpacker. Run: python3 unpack_library.txt ..."""\n' + text
        target.write_text(text, encoding="utf-8")
        print(f"  + {target.name}")

    if chunk_mb <= 0 or len(b64) <= chunk_mb * 1024 * 1024:
        out = out_dir / f"PyLib-{kind}.txt"
        write_chunk_file(out, kind, digest, size, b64)
        print(f"  + {out.name} ({out.stat().st_size / 1024 / 1024:.1f} MB)")
        return [out]

    # режем base64 по символам (~1 байт на символ в ASCII)
    chunk_chars = chunk_mb * 1024 * 1024
    parts: list[Path] = []
    n = 0
    for i in range(0, len(b64), chunk_chars):
        piece = b64[i : i + chunk_chars]
        part_id = f"{n:03d}"
        out = out_dir / f"PyLib-{kind}-part{part_id}.txt"
        write_chunk_file(out, kind, digest, size, piece, part=part_id)
        print(f"  + {out.name} ({out.stat().st_size / 1024 / 1024:.1f} MB)")
        parts.append(out)
        n += 1

    manifest = out_dir / "MANIFEST.txt"
    manifest.write_text(
        f"PyLib mail pack\n"
        f"kind={kind}\n"
        f"sha256={digest}\n"
        f"bytes={size}\n"
        f"parts={n}\n"
        f"\n"
        f"Отправьте почтой все PyLib-*.txt и unpack_library.txt\n"
        f"(без #! в первой строке, только расширение .txt).\n"
        f"\n"
        f"На офлайн-ПК:\n"
        f"  python3 unpack_library.txt PyLib-{kind}-part*.txt\n"
        f"  python3 unpack_library.txt PyLib-{kind}-part*.txt --install\n",
        encoding="utf-8",
    )
    print(f"  + {manifest.name}")
    print(f"Частей: {n} (лимит чанка {chunk_mb} МБ)")
    return parts


def safe_kind(packages: list[str], req_file: str | None) -> str:
    if req_file:
        return "requirements"
    if not packages:
        return "pkgs"
    name = packages[0].split("==")[0].split("[")[0].strip()
    name = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)
    return name[:40] or "pkgs"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Скачать Python-библиотеку и упаковать в .txt для почты"
    )
    ap.add_argument("packages", nargs="*", help="имена пакетов, напр. requests django==4.2")
    ap.add_argument("-r", "--requirement", help="requirements.txt")
    ap.add_argument(
        "-o",
        "--out",
        default="dist-mail",
        help="папка с .txt для отправки (по умолчанию dist-mail)",
    )
    ap.add_argument(
        "--chunk-mb",
        type=int,
        default=DEFAULT_CHUNK_MB,
        help=f"размер чанка в МБ (0 = один файл). По умолчанию {DEFAULT_CHUNK_MB}",
    )
    ap.add_argument(
        "--python-version",
        default=None,
        help="целевая версия Python на Astra, напр. 3.9 / 3.11 (для pip download)",
    )
    ap.add_argument(
        "--keep-wheels",
        action="store_true",
        help="оставить скачанные wheels в out/wheels/",
    )
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()
    kind = safe_kind(args.packages, args.requirement)

    with tempfile.TemporaryDirectory(prefix="pylib-pack-") as tmp:
        tmp_path = Path(tmp)
        wheels = tmp_path / "wheels"
        download_wheels(args.packages, args.requirement, wheels, args.python_version)

        if args.keep_wheels:
            keep = out_dir / "wheels"
            if keep.exists():
                shutil.rmtree(keep)
            shutil.copytree(wheels, keep)
            print(f"Wheels сохранены в {keep}")

        meta = {
            "packages": " ".join(args.packages) if args.packages else "",
            "requirement": args.requirement or "",
            "python_version": args.python_version or "",
        }
        tar_path = tmp_path / "payload.tgz"
        make_tarball(wheels, tar_path, meta)
        pack(tar_path, out_dir, kind, args.chunk_mb)

    print()
    print("Готово. Отправьте файлы из:", out_dir)
    print("На офлайн-ПК: python3 unpack_library.txt PyLib-*-part*.txt --install")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
