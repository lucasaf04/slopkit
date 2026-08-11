"""Generate cache.appcache for slopkit.

Walks the project directory and emits a standard AppCache manifest.
A version hash derived from all file contents ensures the PS5 WebKit browser
re-downloads the cache whenever any file changes.
"""

import hashlib
import os
import shutil
import sys

ALLOWED_TARGETS = (
    "document/",
    "offsets/",
    "payloads/",
    "slopkit/",
    "ui/",
    "index.html",
)


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_allowed(relpath):
    if os.path.basename(relpath).startswith("."):
        return False
    return any(relpath == path or relpath.startswith(path) for path in ALLOWED_TARGETS)


def build_manifest():
    project_root = os.path.dirname(os.path.abspath(__file__))
    entries = []  # (relpath, hash) pairs

    for root, _, files in os.walk(project_root):
        for name in sorted(files):
            filepath = os.path.join(root, name)
            relpath = os.path.relpath(filepath, project_root).replace("\\", "/")
            if not is_allowed(relpath):
                continue
            entries.append((relpath, file_hash(filepath)))

    entries.sort()

    # Version hash: changes when any file changes
    version = hashlib.sha256("".join(h for _, h in entries).encode()).hexdigest()[:16]

    out = os.path.join(project_root, "cache.appcache")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("CACHE MANIFEST\n")
        f.write(f"# {version}\n\n")
        f.write("CACHE:\n")
        for relpath, _ in entries:
            f.write(relpath + "\n")
        f.write("\nNETWORK:\n*\n")

    print(f"Generated {out} with {len(entries)} files.")
    return out


def stage_for_deploy(stage_dir):
    project_root = os.path.dirname(os.path.abspath(__file__))
    manifest_path = build_manifest()

    stage_path = os.path.abspath(os.path.join(project_root, stage_dir))
    if os.path.exists(stage_path):
        shutil.rmtree(stage_path)
    os.makedirs(stage_path, exist_ok=True)

    # Read paths from the generated manifest
    with open(manifest_path, "r", encoding="utf-8") as f:
        in_cache = False
        paths = []
        for line in f:
            line = line.strip()
            if line == "CACHE:":
                in_cache = True
                continue
            if line.startswith("NETWORK:"):
                break
            if in_cache and line:
                paths.append(line)

    staged_count = 0
    for relpath in paths:
        src = os.path.join(project_root, relpath)
        dst = os.path.join(stage_path, relpath)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            staged_count += 1

    # Also stage the manifest itself
    shutil.copy2(manifest_path, os.path.join(stage_path, "cache.appcache"))
    staged_count += 1

    print(f"Staged {staged_count} files into '{stage_dir}' for deployment")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--stage":
        stage_for_deploy(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "--stage":
        stage_for_deploy("_site")
    else:
        build_manifest()
