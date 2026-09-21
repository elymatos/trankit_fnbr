from collections import defaultdict
from typing import DefaultDict, Dict, Sequence

from .domain import LEMMA_TYPES


_CONCEPTUAL = {"event", "object", "role", "relation", "quality", "value"}


def evaluate_lemma_types(
    gold: Sequence[str], ranked_predictions: Sequence[Sequence[str]]
) -> Dict[str, object]:
    if len(gold) != len(ranked_predictions):
        raise ValueError("gold and predictions must have the same length")
    if not gold:
        raise ValueError("at least one labeled token is required")
    top_one = [predictions[0] if predictions else "<missing>" for predictions in ranked_predictions]
    confusion: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
    for expected, predicted in zip(gold, top_one):
        confusion[expected][predicted] += 1

    per_type = {}
    for label in LEMMA_TYPES:
        tp = sum(1 for expected, predicted in zip(gold, top_one) if expected == label == predicted)
        fp = sum(1 for expected, predicted in zip(gold, top_one) if expected != label == predicted)
        fn = sum(1 for expected, predicted in zip(gold, top_one) if expected == label != predicted)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_type[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}

    present = [metrics["f1"] for metrics in per_type.values() if metrics["support"]]
    sort_gold = ["conceptual" if label in _CONCEPTUAL else "procedural" for label in gold]
    sort_pred = ["conceptual" if label in _CONCEPTUAL else "procedural" for label in top_one]
    sort_f1s = []
    for label in ("conceptual", "procedural"):
        tp = sum(1 for expected, predicted in zip(sort_gold, sort_pred) if expected == label == predicted)
        fp = sum(1 for expected, predicted in zip(sort_gold, sort_pred) if expected != label == predicted)
        fn = sum(1 for expected, predicted in zip(sort_gold, sort_pred) if expected == label != predicted)
        denominator = 2 * tp + fp + fn
        sort_f1s.append(2 * tp / denominator if denominator else 0.0)

    report: Dict[str, object] = {
        "accuracy": sum(a == b for a, b in zip(gold, top_one)) / len(gold),
        "macro_f1": sum(present) / len(present) if present else 0.0,
        "conceptual_procedural_f1": sum(sort_f1s) / len(sort_f1s),
        "per_type": per_type,
        "confusion_matrix": {label: dict(values) for label, values in confusion.items()},
    }
    for k in (2, 3):
        report["top_{}_recall".format(k)] = sum(
            expected in predictions[:k]
            for expected, predictions in zip(gold, ranked_predictions)
        ) / len(gold)
    return report
