"""Offline library unpacker. Run: python3 unpack_library.py PyLib-*.txt

На машине БЕЗ интернета:
  python3 unpack_library.txt PyLib-requests-part*.txt
  python3 unpack_library.txt PyLib-requests-part*.txt --install
  python3 unpack_library.txt PyLib-requests.txt --install --venv ~/myenv

Собирает base64-чанки → tar.gz → папка wheels/, опционально pip install --no-index.
Первая строка — docstring (НЕ #!), чтобы почта не блокировала файл.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


def die(msg: str) -> None:
    print("ОШИБКА:", msg, file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], env: dict | None = None) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd, env=env)


def expand_inputs(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pat in patterns:
        p = Path(pat)
        matches = [p] if p.exists() else sorted(Path(".").glob(pat))
        for m in matches:
            rp = m.resolve()
            if rp in seen:
                continue
            # не брать сам распаковщик / манифест
            if m.name in {"unpack_library.py", "unpack_library.txt", "MANIFEST.txt", "pack_library.py"}:
                continue
            seen.add(rp)
            paths.append(m)
    if not paths:
        die("Не найдены входные .txt (PyLib-*.txt)")
    return paths


def read_b64_parts(paths: list[Path]) -> tuple[bytes, dict[str, str]]:
    meta: dict[str, str] = {}
    chunks: list[tuple[str, str]] = []

    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if not lines:
            die(f"Пустой файл: {path}")
        first = lines[0]
        if first.startswith("#!"):
            die(
                f"{path}: первая строка начинается с #! — такой файл почта могла повредить.\n"
                f"Перешлите снова или уберите shebang."
            )

        part_id = "000"
        for key in ("kind", "sha256", "bytes", "part"):
            m = re.search(rf"\b{key}=([^\s]+)", first)
            if m:
                meta[key] = m.group(1)
                if key == "part":
                    part_id = m.group(1)

        body: list[str] = []
        in_body = False
        for line in lines:
            s = line.strip()
            if s == "BEGIN" or s == "# ---BEGIN---":
                in_body = True
                continue
            if s == "END" or s == "# ---END---":
                in_body = False
                continue
            if in_body and s and not s.startswith("#"):
                body.append(s)
        chunks.append((part_id, "".join(body)))

    chunks.sort(key=lambda x: x[0])
    b64 = "".join(c for _, c in chunks)
    try:
        data = base64.b64decode(b64, validate=False)
    except Exception as e:
        die(f"base64 decode failed: {e}")
    return data, meta


def extract_payload(data: bytes, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    tar_path = dest / "payload.tgz"
    tar_path.write_bytes(data)
    wheels_dir = dest / "wheels"
    if wheels_dir.exists():
        shutil.rmtree(wheels_dir)
    wheels_dir.mkdir(parents=True)

    with tarfile.open(tar_path, "r:gz") as tf:
        try:
            tf.extractall(wheels_dir, filter="data")
        except TypeError:
            tf.extractall(wheels_dir)

    tar_path.unlink(missing_ok=True)
    return wheels_dir


def has_pip(py: str) -> bool:
    return (
        subprocess.call(
            [py, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        == 0
    )


def bootstrap_pip(py: str, wheels: Path, boot: Path) -> dict:
    """Если нет pip — поднять из pip-*.whl в пачке."""
    env = os.environ.copy()
    if has_pip(py):
        return env

    print("pip не найден — пробую ensurepip...")
    run([py, "-m", "ensurepip", "--upgrade", "--default-pip"])
    if has_pip(py):
        return env

    pip_whls = sorted(wheels.glob("pip-*.whl"))
    setup_whls = sorted(wheels.glob("setuptools-*.whl"))
    wheel_whls = sorted(wheels.glob("wheel-*.whl"))
    if not pip_whls:
        die(
            "Нет pip в системе и нет pip-*.whl в пачке.\n"
            "На машине с интернетом добавьте: python3 pack_library.py pip setuptools wheel\n"
            "или: sudo apt-get install python3-pip"
        )

    boot.mkdir(parents=True, exist_ok=True)
    extract_to = boot / "pyboot"
    if extract_to.exists():
        shutil.rmtree(extract_to)
    extract_to.mkdir(parents=True)

    for whl in [pip_whls[-1], *(setup_whls[-1:] or []), *(wheel_whls[-1:] or [])]:
        with zipfile.ZipFile(whl) as zf:
            zf.extractall(extract_to)

    env["PYTHONPATH"] = str(extract_to) + (
        (":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else ""
    )
    print(f"pip через bootstrap PYTHONPATH={extract_to}")
    # попытаться поставить pip нормально
    run(
        [py, "-m", "pip", "install", "-q", "--no-index", f"--find-links={wheels}", "pip", "setuptools", "wheel"],
        env=env,
    )
    return env


def install_wheels(wheels: Path, venv: Path | None, user: bool) -> None:
    py = sys.executable
    env = os.environ.copy()

    if venv is not None:
        pybin = venv / "bin" / "python"
        if not pybin.exists():
            print(f"Создаю venv: {venv}")
            rc = run([sys.executable, "-m", "venv", str(venv)])
            if rc != 0 or not pybin.exists():
                print("venv не создался — ставлю через --user / --target")
                venv = None
            else:
                py = str(pybin)
        else:
            py = str(pybin)

    env = bootstrap_pip(py, wheels, wheels.parent / "bootstrap")

    pkgs = []
    for p in sorted(wheels.glob("*.whl")):
        pkgs.append(str(p))
    # source distributions на всякий случай
    for p in sorted(wheels.glob("*.tar.gz")):
        if p.name != "payload.tgz":
            pkgs.append(str(p))

    if not pkgs:
        die(f"В {wheels} нет wheel/tar.gz для установки")

    cmd = [py, "-m", "pip", "install", "--no-index", f"--find-links={wheels}"]
    if user and venv is None:
        cmd.append("--user")
    # ставим всё из find-links по именам файлов — проще поставить каталог:
    # pip install --no-index --find-links=DIR pkg1 pkg2
    # Извлечём имена пакетов из имён wheel: name-version-...
    names: list[str] = []
    for p in wheels.glob("*.whl"):
        # pep 427: {distribution}-{version}(-...)-*.whl
        dist = p.name.split("-")[0]
        if dist not in names and dist not in {"pip", "setuptools", "wheel"}:
            names.append(dist)
    # сначала tooling
    for tool in ("pip", "setuptools", "wheel"):
        if list(wheels.glob(f"{tool}-*.whl")):
            run(cmd + [tool], env=env)
    if names:
        run(cmd + names, env=env)
    else:
        # fallback: поставить каждый wheel файлом
        for p in pkgs:
            run(cmd + [p], env=env)

    print("\nПроверка import:")
    for name in names[:10]:
        mod = name.replace("-", "_")
        subprocess.call([py, "-c", f"import {mod}; print('  OK', '{mod}')"], env=env)


def main() -> int:
    ap = argparse.ArgumentParser(description="Распаковать PyLib-*.txt и опционально установить")
    ap.add_argument("files", nargs="+", help="PyLib-*.txt или part*.txt")
    ap.add_argument(
        "-o",
        "--out",
        default="restored-wheels",
        help="куда положить wheels (по умолчанию restored-wheels)",
    )
    ap.add_argument(
        "--install",
        action="store_true",
        help="сразу pip install --no-index из распакованных wheels",
    )
    ap.add_argument(
        "--venv",
        default=None,
        help="создать/использовать venv по пути и ставить туда",
    )
    ap.add_argument(
        "--user",
        action="store_true",
        help="pip install --user (если без --venv)",
    )
    args = ap.parse_args()

    paths = expand_inputs(args.files)
    print("Входные файлы:")
    for p in paths:
        print(f"  {p}")

    data, meta = read_b64_parts(paths)
    digest = hashlib.sha256(data).hexdigest()
    print(f"decoded {len(data)} bytes, sha256={digest}")
    if meta.get("sha256") and meta["sha256"] != digest:
        die(f"sha256 не совпал!\n  ждали {meta['sha256']}\n  получили {digest}\n(потеряна часть письма?)")
    if meta.get("bytes") and int(meta["bytes"]) != len(data):
        print(f"WARNING: размер {len(data)}, в манифесте {meta['bytes']}")

    out = Path(args.out).resolve()
    wheels = extract_payload(data, out)
    files = sorted(wheels.glob("*"))
    print(f"Распаковано в {wheels} ({len(files)} файлов):")
    for f in files:
        if f.name.startswith("_"):
            print(f"  meta {f.name}")
        else:
            print(f"  {f.name}")

    if args.install:
        venv = Path(args.venv).expanduser().resolve() if args.venv else None
        install_wheels(wheels, venv, args.user)
        print("\nГотово: пакеты установлены.")
    else:
        print("\nГотово. Установка:")
        print(f"  python3 {Path(__file__).name} {' '.join(args.files)} --install")
        print(f"  # или: python3 -m pip install --no-index --find-links={wheels} <пакет>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
