#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trankit_fnbr.converter import convert_conllu
from trankit_fnbr.database import MariaDBLexiconRepository
from trankit_fnbr.lexical import LexicalProcessor
from trankit_fnbr.runtime import create_read_only_engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Portparser CoNLL-U to FNBr lexical units")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--allow-other-split", action="store_true")
    args = parser.parse_args()

    if not args.allow_other_split and not args.source.name.startswith("h8418_0_"):
        parser.error("the first experiment is restricted to the h8418_0 split")

    engine = create_read_only_engine(os.environ["FNBR_DATABASE_URL"])
    repository = MariaDBLexiconRepository(
        engine, revision=os.environ["FNBR_LEXICON_REVISION"]
    )
    converted, manifest = convert_conllu(
        args.source.read_text(encoding="utf-8"),
        LexicalProcessor(repository),
        source_name=str(args.source),
        converter_version="0.1.0",
        code_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(converted, encoding="utf-8")
    manifest_path = args.manifest or args.output.with_suffix(args.output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
