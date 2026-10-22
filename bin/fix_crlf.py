"""Fix Windows CRLF in PyIDE. Run: python3 bin/fix_crlf.py"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTS = {".vim", ".py", ".sh", ".md", ".txt", ""}
names = {"vimrc"}

def main() -> None:
    n = 0
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if "vendor" in p.parts or ".git" in p.parts or "dist" in p.parts:
            continue
        if p.name not in names and p.suffix not in EXTS and p.suffix != "":
            if p.suffix not in {".vim", ".py", ".sh", ".md", ".txt"}:
                continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        if b"\r\n" not in data:
            continue
        p.write_bytes(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        print("fixed", p.relative_to(ROOT))
        n += 1
    print(f"done, {n} files")

if __name__ == "__main__":
    main()
