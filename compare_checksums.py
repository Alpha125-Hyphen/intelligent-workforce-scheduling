
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = BASE_DIR / "outputs" / "checksum_manifest.json"


def load_manifest():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def compare_manifests(first, second):
    all_files = set(first) | set(second)

    differences = []

    for filename in sorted(all_files):
        if first.get(filename) != second.get(filename):
            differences.append(filename)

    return differences


def main():
    print("Loading checksum manifest...")

    first_manifest = load_manifest()

    print("Files recorded:", len(first_manifest))

    print("\nNext, regenerate the dataset using:")
    print("python main.py")
    print("python reproducibility_check.py")

    second_manifest = load_manifest()

    differences = compare_manifests(
        first_manifest,
        second_manifest
    )

    if differences:
        print("\nFiles with different checksums:")
        for filename in differences:
            print(filename)
    else:
        print("\nAll checksums match.")


if __name__ == "__main__":
    main()
