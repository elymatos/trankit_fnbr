#!/usr/bin/env python3
"""Run the FNBr pipeline for one raw sentence and print its JSON result."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from trankit_fnbr.runtime import build_pipeline


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Analyze one raw Portuguese sentence with the local FNBr pipeline."
    )
    parser.add_argument(
        "sentence",
        nargs="?",
        help="raw sentence; when omitted, read it from standard input",
    )
    parser.add_argument("--top-k", type=int, default=3, choices=range(1, 16))
    parser.add_argument(
        "--predictor",
        choices=("lexical", "model"),
        default="lexical",
        help=(
            "lexical uses FNBr dictionary types without a trained checkpoint; "
            "model uses the configured contextual FNBr checkpoint"
        ),
    )
    parser.add_argument("--compact", action="store_true", help="print compact JSON")
    args = parser.parse_args(argv)

    load_dotenv()
    sentence = args.sentence if args.sentence is not None else sys.stdin.read()
    sentence = sentence.strip()
    if not sentence:
        parser.error("a non-empty sentence is required")

    result = build_pipeline(predictor_mode=args.predictor).analyze(sentence, args.top_k)
    json.dump(
        result,
        sys.stdout,
        ensure_ascii=False,
        indent=None if args.compact else 2,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
