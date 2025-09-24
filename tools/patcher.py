# tools/patcher.py
from __future__ import annotations
import io, os, sys, re, argparse

def ensure_boot_call(main_path: str):
    with open(main_path, "r", encoding="utf-8") as f:
        src = f.read()
    if "app.extensions.boot" in src and "install_extensions" in src:
        return False  # already present
    trailer = "\n\n# === [AUTO PATCH] Install codeX extensions ===\n" \
              "try:\n" \
              "    from app.extensions.boot import install_extensions\n" \
              "    install_extensions()\n" \
              "except Exception as _e:\n" \
              "    print('[boot] install failed:', _e)\n"
    with open(main_path, "a", encoding="utf-8") as f:
        f.write(trailer)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default="app/main.py")
    args = ap.parse_args()
    os.makedirs("tools", exist_ok=True)
    changed = ensure_boot_call(args.main)
    print("patched" if changed else "already")

if __name__ == "__main__":
    main()
