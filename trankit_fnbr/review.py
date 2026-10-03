"""Round-trip FNBr labels through a compact, hand-editable review file.

A review file keeps each sentence's ``# sent_id`` and ``# text`` comments and
one tab-separated ``ID FORM LABEL`` line per token. ``LABEL`` is one of the
fifteen lemma types, ``ambiguous``, or ``unresolved``.
"""
from typing import Dict, List, Tuple

from .domain import LEMMA_TYPES

STATUSES = ("ambiguous", "unresolved")
VALID_LABELS = frozenset(LEMMA_TYPES) | frozenset(STATUSES)


def _label_from_misc(misc: str) -> str:
    for part in misc.split("|"):
        if part.startswith("FNBRType="):
            return part.split("=", 1)[1]
        if part.startswith("FNBRStatus="):
            return part.split("=", 1)[1]
    raise ValueError("token has neither FNBRType nor FNBRStatus: {}".format(misc))


def _misc_with_label(misc: str, label: str) -> str:
    kept = [part for part in misc.split("|")
            if part != "_" and not part.startswith(("FNBRType=", "FNBRStatus="))]
    kept.append("FNBRStatus={}".format(label) if label in STATUSES
                else "FNBRType={}".format(label))
    return "|".join(kept)


def export_review(conllu: str) -> str:
    lines: List[str] = []
    for line in conllu.splitlines():
        if not line:
            lines.append("")
        elif line.startswith("# sent_id") or line.startswith("# text"):
            lines.append(line)
        elif not line.startswith("#"):
            columns = line.split("\t")
            lines.append("\t".join((columns[0], columns[1], _label_from_misc(columns[9]))))
    return "\n".join(lines).rstrip("\n") + "\n"


def parse_review(review: str) -> Dict[Tuple[str, str], Tuple[str, str]]:
    """Map (sent_id, token ID) to (form, label), validating every label."""
    labels: Dict[Tuple[str, str], Tuple[str, str]] = {}
    sent_id = None
    for number, line in enumerate(review.splitlines(), start=1):
        if line.startswith("# sent_id"):
            sent_id = line.split("=", 1)[1].strip()
        elif line and not line.startswith("#"):
            columns = line.split("\t")
            if sent_id is None or len(columns) != 3:
                raise ValueError("line {}: expected ID<TAB>FORM<TAB>LABEL after a sent_id".format(number))
            token_id, form, label = columns[0], columns[1], columns[2].strip()
            if label not in VALID_LABELS:
                raise ValueError("line {}: unknown label {!r}".format(number, label))
            labels[(sent_id, token_id)] = (form, label)
    return labels


def apply_review(conllu: str, review: str) -> Tuple[str, int]:
    """Return the CoNLL-U with reviewed labels and the number of changed tokens."""
    labels = parse_review(review)
    output: List[str] = []
    sent_id = None
    seen = 0
    changed = 0
    for line in conllu.splitlines():
        if line.startswith("# sent_id"):
            sent_id = line.split("=", 1)[1].strip()
        if not line or line.startswith("#"):
            output.append(line)
            continue
        columns = line.split("\t")
        key = (str(sent_id), columns[0])
        if key not in labels:
            raise ValueError("review file has no token {} in sentence {}".format(columns[0], sent_id))
        form, label = labels[key]
        if form != columns[1]:
            raise ValueError("sentence {} token {}: form {!r} does not match {!r}".format(
                sent_id, columns[0], form, columns[1]))
        seen += 1
        if label != _label_from_misc(columns[9]):
            columns[9] = _misc_with_label(columns[9], label)
            changed += 1
        output.append("\t".join(columns))
    if seen != len(labels):
        raise ValueError("review file has {} tokens but the CoNLL-U has {}".format(len(labels), seen))
    return "\n".join(output) + "\n", changed
