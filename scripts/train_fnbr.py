#!/usr/bin/env python3
"""Train the FNBr type-only baseline or joint POS/dependency model."""
import argparse
import hashlib
import json
from pathlib import Path

from trankit import TPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=Path("outputs/h8418_0_train.fnbr.conllu"))
    parser.add_argument("--dev", type=Path, default=Path("outputs/h8418_0_dev.fnbr.conllu"))
    parser.add_argument("--save-dir", default=None)
    parser.add_argument("--joint", action="store_true", help="train POS/dependencies alongside FNBr types")
    parser.add_argument("--embedding", default="xlm-roberta-large")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    manifests = [json.loads(Path(str(path) + ".manifest.json").read_text(encoding="utf-8"))
                 for path in (args.train, args.dev)]
    for field in ("lexicon_revision", "database_schema_version", "lexical_policy_version",
                  "converter_version", "label_policy"):
        if manifests[0].get(field) != manifests[1].get(field):
            parser.error("train/dev manifests disagree on {}".format(field))
    if args.batch_size < 1 or args.epochs < 1:
        parser.error("batch size and epochs must be positive")
    save_dir = args.save_dir or ("./cache/fnbr-joint" if args.joint else "./cache/fnbr")
    checkpoint_dir = Path(save_dir) / args.embedding / "customized"
    metadata_path = checkpoint_dir / "fnbr.training.json"
    objectives = "joint" if args.joint else "type_only"
    if metadata_path.exists():
        previous = json.loads(metadata_path.read_text(encoding="utf-8"))
        if previous.get("objectives") != objectives:
            parser.error("save directory contains a checkpoint trained for different objectives")
    print("Training", "joint" if args.joint else "type-only", "model with lexicon revision",
          manifests[0]["lexicon_revision"], "in", save_dir, flush=True)
    trainer = TPipeline({
        "task": "posdep", "category": "customized",
        "train_conllu_fpath": str(args.train), "dev_conllu_fpath": str(args.dev),
        "save_dir": save_dir, "embedding": args.embedding,
        "batch_size": args.batch_size, "max_epoch": args.epochs,
        "lemma_type_only": not args.joint, "gpu": not args.cpu,
    })
    trainer.train()
    checkpoint = checkpoint_dir / "customized.tagger.mdl"
    # The fork saves only trained adapters/head weights and the selected epoch.
    # Store training objectives separately so runtime cannot use untrained
    # dependency predictions from a type-only model as a learned scaffold.
    import torch
    saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
    metadata = {
        "objectives": objectives,
        "checkpoint_epoch": saved["epoch"],
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "embedding": args.embedding,
        "lexicon_revision": manifests[0]["lexicon_revision"],
        "source_output_sha256": {"train": manifests[0]["output_sha256"],
                                 "dev": manifests[1]["output_sha256"]},
        "epochs": args.epochs,
        "batch_size": args.batch_size,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
