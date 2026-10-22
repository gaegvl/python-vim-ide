"""PyIDE offline tools installer. Run: python3 bin/install_tools.py

Без bash/shebang/pipefail — для Astra, где sh=dash и нет /usr/bin/env.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def die(msg: str) -> None:
    print("ОШИБКА:", msg, file=sys.stderr)
    raise SystemExit(1)


def writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".pyide_write_test_{os.getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def pick_base() -> Path:
    env = os.environ.get("PYIDE_HOME", "").strip()
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            Path.home() / ".local" / "share" / "pyide",
            Path.home() / "pyide",
            Path(f"/tmp/pyide-{os.environ.get('USER', 'user')}"),
        ]
    )
    for c in candidates:
        if writable_dir(c):
            return c
    die("Нет папки с правами на запись (~/.local, ~/pyide, /tmp)")


def run(cmd: list[str], **kw) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd, **kw)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    wheels = Path(os.environ.get("WHEELS", root / "vendor" / "wheels"))
    if not wheels.is_dir():
        die(f"Нет каталога {wheels}")
    whls = list(wheels.glob("*.whl"))
    if not whls:
        die(f"В {wheels} нет .whl — сначала распакуйте почтовый пакет")
    if not os.access(whls[0], os.R_OK):
        die(f"Нет чтения {wheels}: chmod -R u+rX \"{wheels}\"")

    py = os.environ.get("PYTHON", "python3")
    base = pick_base()
    print(f"Каталог установки: {base}")
    print(f"Wheels: {wheels}")

    venv = Path(os.environ.get("PYIDE_VENV", base / "venv"))
    target = Path(os.environ.get("PYIDE_TARGET", base / "pyroot"))
    mode = "venv"
    pybin = venv / "bin" / "python"
    bindir = venv / "bin"

    # try venv
    if venv.exists():
        import shutil

        shutil.rmtree(venv, ignore_errors=True)
    rc = run([py, "-m", "venv", str(venv)])
    if rc != 0 or not pybin.is_file():
        print("venv не создался — режим --target")
        mode = "target"
        writable_dir(target) or die(f"Не могу писать в {target}")
        (target / "bin").mkdir(parents=True, exist_ok=True)
        pybin = Path(py)
        bindir = target / "bin"
        pip_base = [py, "-m", "pip", "install", "-q", "--no-index", f"--find-links={wheels}", "--target", str(target)]
    else:
        print(f"Режим: venv ({venv})")
        run([str(pybin), "-m", "pip", "install", "-q", "--upgrade", "pip"])
        pip_base = [str(pybin), "-m", "pip", "install", "-q", "--no-index", f"--find-links={wheels}"]

    print("Ставлю пакеты...")
    for pkg in ("jedi", "parso", "ruff", "pytest", "isort", "debugpy"):
        cmd = list(pip_base) + [pkg]
        if run(cmd) == 0:
            print(f"  OK  {pkg}")
        else:
            print(f"  SKIP {pkg}")

    # shebang fix for text scripts only
    if bindir.is_dir() and mode == "venv":
        for f in bindir.iterdir():
            if not f.is_file():
                continue
            try:
                data = f.read_bytes()
            except OSError:
                continue
            if b"\0" in data[:256]:
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if text.startswith("#!/usr/bin/env") or text.startswith("#! /usr/bin/env"):
                rest = text.split("\n", 1)[1] if "\n" in text else ""
                f.write_text(f"#!{pybin}\n{rest}", encoding="utf-8")
                f.chmod(f.stat().st_mode | 0o111)
                print(f"  shebang fix: {f.name}")

    print("\nПроверка:")
    env = os.environ.copy()
    if mode == "target":
        env["PYTHONPATH"] = str(target) + ((":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")
    check_py = str(pybin) if mode == "venv" else py
    for mod in ("jedi", "pytest"):
        r = subprocess.run(
            [check_py, "-c", f"import {mod}; print('  {mod}', {mod}.__version__)"],
            env=env,
        )
        if r.returncode != 0:
            print(f"  {mod} НЕ установлен")

    marker = base / "env.sh"
    if mode == "venv":
        marker.write_text(
            f'export PATH="{bindir}:$PATH"\nexport PYIDE_PYTHON="{pybin}"\n',
            encoding="utf-8",
        )
        (base / "install-mode").write_text("venv\n", encoding="utf-8")
        (base / "python").write_text(f"{pybin}\n", encoding="utf-8")
    else:
        marker.write_text(
            f'export PYTHONPATH="{target}${{PYTHONPATH:+:$PYTHONPATH}}"\n'
            f'export PATH="{bindir}:$PATH"\n'
            f'export PYIDE_PYTHON="{py}"\n'
            f'export PYIDE_PYTHONPATH="{target}"\n',
            encoding="utf-8",
        )
        (base / "install-mode").write_text("target\n", encoding="utf-8")
        (base / "pythonpath").write_text(f"{target}\n", encoding="utf-8")

    # legacy hints for Vim
    legacy = Path.home() / ".local" / "share" / "pyide"
    if writable_dir(legacy):
        if mode == "venv":
            (legacy / "python").write_text(f"{pybin}\n", encoding="utf-8")
        else:
            (legacy / "pythonpath").write_text(f"{target}\n", encoding="utf-8")

    print(f"\nГотово.\n  source {marker}\n  В Vim: :PyIdeHealth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
