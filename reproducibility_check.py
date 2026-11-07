
import hashlib
import json
from pathlib import Path

# Project directories
BASE_DIR = Path(__file__).resolve().parent

FOLDERS_TO_CHECK = [
    "data",
    "ground_truth",
    "outputs"
]


def calculate_checksum(file_path):
    """Calculate SHA256 checksum of a file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def generate_manifest():
    """Generate checksums for project data files."""

    manifest = {}

    for folder in FOLDERS_TO_CHECK:
        folder_path = BASE_DIR / folder

        if not folder_path.exists():
            print(f"Warning: {folder} folder not found")
            continue

        for file_path in sorted(folder_path.rglob("*")):
            if file_path.is_file() and file_path.name != "checksum_manifest.json":
                relative_path = str(
                    file_path.relative_to(BASE_DIR)
                )

                manifest[relative_path] = calculate_checksum(
                    file_path
                )

    return manifest


def main():
    print("Starting reproducibility check...")

    manifest = generate_manifest()

    output_file = BASE_DIR / "outputs" / "checksum_manifest.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=4)

    print(f"Files checked: {len(manifest)}")
    print(f"Manifest saved: {output_file.name}")
    print("Reproducibility manifest generated successfully.")


if __name__ == "__main__":
    main()
