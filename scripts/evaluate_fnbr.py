#!/usr/bin/env python3
"""Evaluate FNBr typing and lexical dependency attachment on a held-out split."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trankit import Pipeline

from trankit_fnbr.metrics import evaluate_lemma_types


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("outputs/h8418_0_test.fnbr.conllu"))
    parser.add_argument("--cache-dir", default="./cache/fnbr")
    parser.add_argument("--embedding", default="xlm-roberta-large")
    parser.add_argument("--output", type=Path, default=Path("outputs/h8418_0_test.metrics.json"))
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    gold, ranked, sentences = [], [], []
    heads, relations = [], []
    for block in args.data.read_text(encoding="utf-8").strip().split("\n\n"):
        rows = [line.split("\t") for line in block.splitlines() if line and not line.startswith("#")]
        if not rows:
            continue
        sentences.append([row[1] for row in rows])
        gold.append([next((part.split("=", 1)[1] for part in row[9].split("|")
                           if part.startswith("FNBRType=")), None) for row in rows])
        heads.append([int(row[6]) for row in rows])
        relations.append([row[7] for row in rows])
    pipeline = Pipeline(lang="customized", cache_dir=args.cache_dir,
                        gpu=not args.cpu, embedding=args.embedding)
    predictions = pipeline.posdep(sentences)["sentences"]
    if len(predictions) != len(sentences):
        raise ValueError("inference returned a different sentence count")
    correct_heads = correct_labels = dependency_count = 0
    for gold_sentence, gold_heads, gold_relations, prediction in zip(
            gold, heads, relations, predictions):
        tokens = prediction["tokens"]
        if len(tokens) != len(gold_sentence):
            raise ValueError("inference returned a different token count")
        for label, expected_head, expected_relation, token in zip(
                gold_sentence, gold_heads, gold_relations, tokens):
            dependency_count += 1
            if token["head"] == expected_head:
                correct_heads += 1
                if token.get("deprel") == expected_relation:
                    correct_labels += 1
            if label is not None:
                candidates = token["lemma_type_candidates"]
                ranked.append([candidate["type"] for candidate in candidates])
    labels = [label for sentence in gold for label in sentence if label is not None]
    if len(labels) != len(ranked):
        raise ValueError("labeled token count mismatch")
    report = evaluate_lemma_types(labels, ranked)
    report["labeled_tokens"] = len(labels)
    report["sentences"] = len(sentences)
    report["projected_tree_uas_including_punct"] = correct_heads / dependency_count
    report["projected_tree_las_including_punct"] = correct_labels / dependency_count
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("test labeled tokens:", len(labels), "accuracy:", report["accuracy"],
          "macro-F1:", report["macro_f1"], "UAS:", report["projected_tree_uas_including_punct"],
          "LAS:", report["projected_tree_las_including_punct"])


if __name__ == "__main__":
    main()
