#!/usr/bin/env python3
"""Export FNBr labels to review files, or apply edited review files back."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trankit_fnbr.review import apply_review, export_review


def review_path(conllu: Path, review_dir: Path) -> Path:
    return review_dir / (conllu.name[:-len(".conllu")] + ".review.tsv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("export", "apply"))
    parser.add_argument("conllu", type=Path, nargs="+")
    parser.add_argument("--review-dir", type=Path, default=Path("datasets/fnbr/review"))
    parser.add_argument("--force", action="store_true", help="overwrite existing review files on export")
    args = parser.parse_args()
    for conllu in args.conllu:
        review = review_path(conllu, args.review_dir)
        if args.command == "export":
            if review.exists() and not args.force:
                parser.error("{} exists; it may contain edits (use --force to overwrite)".format(review))
            review.parent.mkdir(parents=True, exist_ok=True)
            review.write_text(export_review(conllu.read_text(encoding="utf-8")), encoding="utf-8")
            print("wrote", review)
        else:
            updated, changed = apply_review(conllu.read_text(encoding="utf-8"),
                                            review.read_text(encoding="utf-8"))
            conllu.write_text(updated, encoding="utf-8")
            print("{}: {} labels changed".format(conllu, changed))


if __name__ == "__main__":
    main()
