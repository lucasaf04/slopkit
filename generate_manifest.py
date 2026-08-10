import hashlib
import json
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
    "sw.js",
)


def is_allowed(relpath):
    if os.path.basename(relpath).startswith("."):
        return False
    return any(relpath == path or relpath.startswith(path) for path in ALLOWED_TARGETS)


def build_manifest():
    project_root = os.path.dirname(os.path.abspath(__file__))
    file_hashes = {}
    combined_sha = hashlib.sha256()

    for root, _, files in os.walk(project_root):
        for file in sorted(files):
            filepath = os.path.join(root, file)
            relpath = os.path.relpath(filepath, project_root).replace("\\", "/")
            if not is_allowed(relpath):
                continue
            with open(filepath, "rb") as f:
                content = f.read()
                file_hash = hashlib.sha256(content).hexdigest()
                file_hashes[relpath] = file_hash
                combined_sha.update(relpath.encode("utf-8"))
                combined_sha.update(file_hash.encode("utf-8"))

    sorted_file_hashes = dict(sorted(file_hashes.items()))
    manifest_version = combined_sha.hexdigest()[:16]

    manifest_data = {
        "version": manifest_version,
        "hash_algorithm": "sha256",
        "combined_sha256": combined_sha.hexdigest(),
        "total_files": len(sorted_file_hashes),
        "files": sorted_file_hashes,
    }

    manifest_path = os.path.join(project_root, "cache-manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(
        f"Generated {manifest_path} with {len(sorted_file_hashes)} files (version: {manifest_version})"
    )
    return manifest_data


def stage_for_deploy(stage_dir):
    project_root = os.path.dirname(os.path.abspath(__file__))
    manifest_data = build_manifest()

    stage_path = os.path.abspath(os.path.join(project_root, stage_dir))
    if os.path.exists(stage_path):
        shutil.rmtree(stage_path)
    os.makedirs(stage_path, exist_ok=True)

    for relpath in manifest_data["files"]:
        src = os.path.join(project_root, relpath)
        dst = os.path.join(stage_path, relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    shutil.copy2(
        os.path.join(project_root, "cache-manifest.json"),
        os.path.join(stage_path, "cache-manifest.json"),
    )

    print(
        f"Staged {len(manifest_data['files']) + 1} files into '{stage_dir}' for deployment"
    )


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--stage":
        stage_for_deploy(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "--stage":
        stage_for_deploy("_site")
    else:
        build_manifest()
