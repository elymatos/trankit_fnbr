#!/usr/bin/env python3
"""Run the FNBr pipeline for one raw sentence and print its JSON result."""

import argparse
from contextlib import redirect_stdout
import json
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

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
    parser.add_argument("--scaffold-source", choices=("projected", "model"),
                        help="use projected UD or dependencies from a joint FNBr checkpoint")
    parser.add_argument("--fnbr-cache-dir", type=Path,
                        help="FNBr checkpoint cache (e.g. ./cache/fnbr-joint)")
    parser.add_argument("--model-version", help="version shown in model-mode output")
    parser.add_argument("--compact", action="store_true", help="print compact JSON")
    args = parser.parse_args(argv)

    load_dotenv(PROJECT_ROOT / ".env")
    if args.scaffold_source:
        os.environ["FNBR_SCAFFOLD_SOURCE"] = args.scaffold_source
    if args.fnbr_cache_dir:
        os.environ["FNBR_TRANKIT_CACHE_DIR"] = str(args.fnbr_cache_dir)
    if args.model_version:
        os.environ["FNBR_MODEL_VERSION"] = args.model_version
    missing = [
        name for name in ("FNBR_DATABASE_URL", "FNBR_LEXICON_REVISION")
        if not os.getenv(name)
    ]
    if missing:
        parser.error(
            "missing {}. Create the local configuration with "
            "`cp .env.example .env`, then set the read-only FNBr database URL "
            "and lexicon revision.".format(", ".join(missing))
        )

    sentence = args.sentence if args.sentence is not None else sys.stdin.read()
    sentence = sentence.strip()
    if not sentence:
        parser.error("a non-empty sentence is required")

    # Trankit reports model-loading progress on stdout. Keep stdout reserved
    # for the machine-readable result and route those diagnostics to stderr.
    with redirect_stdout(sys.stderr):
        pipeline = build_pipeline(predictor_mode=args.predictor)
        result = pipeline.analyze(sentence, args.top_k)
    json.dump(
        result,
        sys.stdout,
        ensure_ascii=False,
        indent=None if args.compact else 2,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
