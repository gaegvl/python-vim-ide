"""PyIDE offline tools installer. Run: python3 bin/install_tools.py

Без bash/shebang/pipefail. Сам поднимает pip из vendor/wheels, если
модуля pip в системе нет (типично для Astra).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
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
    print("+", " ".join(str(x) for x in cmd))
    return subprocess.call(cmd, **kw)


def has_pip(py: str) -> bool:
    return subprocess.call(
        [py, "-m", "pip", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) == 0


def find_wheel(wheels: Path, name: str) -> Path | None:
    matches = sorted(wheels.glob(f"{name}-*.whl"))
    return matches[-1] if matches else None


def bootstrap_pip(py: str, wheels: Path, boot_dir: Path) -> None:
    """Установить pip без существующего pip: распаковать wheel + zipimport."""
    if has_pip(py):
        print("pip уже есть")
        return

    print("pip не найден — пробую ensurepip...")
    run([py, "-m", "ensurepip", "--upgrade", "--default-pip"])
    if has_pip(py):
        print("pip поднят через ensurepip")
        return

    pip_whl = find_wheel(wheels, "pip")
    setup_whl = find_wheel(wheels, "setuptools")
    wheel_whl = find_wheel(wheels, "wheel")
    if not pip_whl:
        die(
            "Нет модуля pip и нет pip-*.whl в vendor/wheels.\n"
            "Обновите пакет с почты (нужны pip/setuptools/wheel) или:\n"
            "  sudo apt-get install python3-pip"
        )

    print(f"Поднимаю pip из {pip_whl.name} (офлайн)...")
    boot_dir.mkdir(parents=True, exist_ok=True)
    extract_to = boot_dir / "pyboot"
    if extract_to.exists():
        shutil.rmtree(extract_to)
    extract_to.mkdir(parents=True)

    for whl in (pip_whl, setup_whl, wheel_whl):
        if whl is None:
            continue
        with zipfile.ZipFile(whl) as zf:
            zf.extractall(extract_to)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(extract_to) + (
        (":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else ""
    )

    # поставить pip/setuptools/wheel уже «нормально» в этот же интерпретатор
    cmd = [
        py,
        "-m",
        "pip",
        "install",
        "-q",
        "--no-index",
        f"--find-links={wheels}",
        "pip",
        "setuptools",
        "wheel",
    ]
    # для target/venv без site-packages прав — user или prefix
    rc = run(cmd, env=env)
    if rc != 0:
        # fallback: оставить PYTHONPATH на распакованный pip
        marker = boot_dir / "BOOTSTRAP_PYTHONPATH"
        marker.write_text(str(extract_to), encoding="utf-8")
        print(f"pip будет через PYTHONPATH={extract_to}")
        return

    if not has_pip(py):
        # всё ещё нет — используем boot PYTHONPATH дальше
        marker = boot_dir / "BOOTSTRAP_PYTHONPATH"
        marker.write_text(str(extract_to), encoding="utf-8")
        print(f"pip через bootstrap PYTHONPATH={extract_to}")
    else:
        print("pip установлен офлайн из wheels")


def pip_cmd(py: str, wheels: Path, boot_dir: Path, extra: list[str]) -> tuple[list[str], dict]:
    env = os.environ.copy()
    marker = boot_dir / "BOOTSTRAP_PYTHONPATH"
    if marker.is_file():
        boot = marker.read_text(encoding="utf-8").strip()
        env["PYTHONPATH"] = boot + ((":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")
    return [py, "-m", "pip", "install", "-q", "--no-index", f"--find-links={wheels}", *extra], env


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

    py = os.environ.get("PYTHON", sys.executable or "python3")
    base = pick_base()
    print(f"Каталог установки: {base}")
    print(f"Wheels: {wheels} ({len(whls)} файлов)")
    print(f"Python: {py}")

    venv = Path(os.environ.get("PYIDE_VENV", base / "venv"))
    target = Path(os.environ.get("PYIDE_TARGET", base / "pyroot"))
    boot_dir = base / "bootstrap"

    mode = "venv"
    pybin = venv / "bin" / "python"
    bindir = venv / "bin"

    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)

    # venv без pip, если ensurepip нет — всё равно ок, поднимем сами
    rc = run([py, "-m", "venv", str(venv)])
    if rc != 0 or not pybin.is_file():
        print("venv не создался — режим --target в", target)
        mode = "target"
        writable_dir(target) or die(f"Не могу писать в {target}")
        (target / "bin").mkdir(parents=True, exist_ok=True)
        py_for_pip = py
        bindir = target / "bin"
        pybin_path = Path(py)
    else:
        print(f"Режим: venv ({venv})")
        py_for_pip = str(pybin)
        pybin_path = pybin

    bootstrap_pip(py_for_pip, wheels, boot_dir)

    # обязательные / желательные / опциональные (бинарные под конкретный CPython)
    required = ["pip", "setuptools", "wheel", "jedi", "parso"]
    useful = ["ruff", "pytest"]
    optional = ["isort", "debugpy"]  # часто нет wheel под версию Python на Astra
    print("Ставлю пакеты...")
    for pkg in required + useful + optional:
        if mode == "venv":
            cmd, env = pip_cmd(py_for_pip, wheels, boot_dir, [pkg])
        else:
            cmd, env = pip_cmd(
                py_for_pip,
                wheels,
                boot_dir,
                ["--target", str(target), pkg],
            )
        if run(cmd, env=env) == 0:
            print(f"  OK  {pkg}")
        elif pkg in optional:
            print(f"  SKIP {pkg} (нет wheel под этот Python — для IDE не критично)")
        else:
            print(f"  SKIP {pkg}")

    # shebang fix
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
                f.write_text(f"#!{pybin_path}\n{rest}", encoding="utf-8")
                f.chmod(f.stat().st_mode | 0o111)
                print(f"  shebang fix: {f.name}")

    print("\nПроверка:")
    env = os.environ.copy()
    if mode == "target":
        env["PYTHONPATH"] = str(target) + ((":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")
    check_py = str(pybin_path)
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
            f'export PATH="{bindir}:$PATH"\nexport PYIDE_PYTHON="{pybin_path}"\n',
            encoding="utf-8",
        )
        (base / "install-mode").write_text("venv\n", encoding="utf-8")
        (base / "python").write_text(f"{pybin_path}\n", encoding="utf-8")
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

    legacy = Path.home() / ".local" / "share" / "pyide"
    if writable_dir(legacy):
        if mode == "venv":
            (legacy / "python").write_text(f"{pybin_path}\n", encoding="utf-8")
        else:
            (legacy / "pythonpath").write_text(f"{target}\n", encoding="utf-8")

    print(f"\nГотово.\n  source {marker}\n  В Vim: :PyIdeHealth")
    if not find_wheel(wheels, "pip"):
        print("Подсказка: в следующем почтовом пакете будут pip/setuptools/wheel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
