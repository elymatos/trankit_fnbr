import hashlib
from typing import Dict, List, Sequence, Tuple

from .domain import ParsedToken
from .lexical import LexicalProcessor
from .projection import ProjectedToken, ProjectionError, project_dependencies
from .trankit_adapter import contraction_anchor


def convert_conllu(
    source: str,
    processor: LexicalProcessor,
    source_name: str,
    converter_version: str,
    language: str = "pt",
    code_revision: str = "unknown",
) -> Tuple[str, Dict[str, object]]:
    output_sentences = []
    instances = []
    converted_count = 0
    unresolved_count = 0
    unaligned_tokens = 0
    label_counts = {"resolved": 0, "ambiguous": 0, "unresolved": 0}
    parsed_sentences = _parse_conllu(source)
    prefetch = getattr(processor.repository, "prefetch_forms", None)
    if prefetch is not None:
        prefetch((token.text for _, tokens, _ in parsed_sentences for token in tokens), language)
    for comments, tokens, original_ids in parsed_sentences:
        unaligned_tokens += sum(token.start_char < 0 for token in tokens)
        analysis = processor.process(tokens, language)
        sentence_id = next((line.split("=", 1)[1].strip() for line in comments
                            if line.startswith("# sent_id =")), str(converted_count + 1))
        try:
            projected = project_dependencies(tokens, analysis.selected)
        except ProjectionError as error:
            raise ProjectionError("{}: {}".format(sentence_id, error)) from error
        lines = list(comments)
        for token, lexical in zip(projected, analysis.selected):
            misc = []
            if lexical.selected_lemma and lexical.selected_lemma.lemma_type:
                misc.append("FNBRType={}".format(lexical.selected_lemma.lemma_type))
                label_counts["resolved"] += 1
            elif len(lexical.lemma_candidates) > 1:
                misc.append("FNBRStatus=ambiguous")
                label_counts["ambiguous"] += 1
                unresolved_count += 1
            else:
                misc.append("FNBRStatus=unresolved")
                label_counts["unresolved"] += 1
                unresolved_count += 1
            lines.append(_projected_to_conllu(token, "|".join(misc)))
        output_sentences.append("\n".join(lines))
        instances.append({
            "source_sentence_id": sentence_id,
            "source_token_ids": [token.id for token in tokens],
            "surface_to_source_word_ids": {str(key): list(value) for key, value in original_ids.items()},
            "selected": [
                {
                    "lexical_token_id": item.id,
                    "source_token_ids": list(item.components),
                    "source_word_ids": [word for component in item.components
                                        for word in original_ids[component]],
                    "start_char": item.start_char,
                    "end_char": item.end_char,
                    "selected_lemma_id": item.selected_lemma.id if item.selected_lemma else None,
                }
                for item in analysis.selected
            ],
            "lattice": [
                {
                    "lexical_token_id": item.id,
                    "source_token_ids": list(item.components),
                    "lemma_candidate_ids": [lemma.id for lemma in item.lemma_candidates],
                    "start_char": item.start_char,
                    "end_char": item.end_char,
                    "source": item.source,
                }
                for item in analysis.lattice
            ],
        })
        converted_count += 1
    output = "\n\n".join(output_sentences) + ("\n\n" if output_sentences else "")
    manifest = {
        "converter_version": converter_version,
        "code_revision": code_revision,
        "lexical_policy_version": processor.policy_version,
        "database_schema_version": getattr(processor.repository, "schema_version", "fixture"),
        "lexicon_revision": processor.repository.revision,
        "source_files": [{
            "name": source_name,
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        }],
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "sentences": converted_count,
        "unresolved_or_ambiguous_tokens": unresolved_count,
        "label_counts": label_counts,
        "unaligned_surface_tokens": unaligned_tokens,
        "label_policy": "unique_typed_lemma_provisional",
        "instances": instances,
    }
    return output, manifest


def _parse_conllu(source: str) -> List[Tuple[List[str], List[ParsedToken], Dict[int, Tuple[int, ...]]]]:
    sentences = []
    for block in source.strip().split("\n\n"):
        comments = []
        rows = []
        ranges = {}
        sentence_text = ""
        for line in block.splitlines():
            if line.startswith("#"):
                comments.append(line)
                if line.startswith("# text = "):
                    sentence_text = line[len("# text = "):]
                continue
            fields = line.split("\t")
            if len(fields) != 10:
                raise ValueError("invalid CoNLL-U row: {}".format(line))
            if "-" in fields[0]:
                first, last = (int(part) for part in fields[0].split("-"))
                ranges[first] = (last, fields[1])
            elif "." not in fields[0]:
                rows.append(fields)
        by_id = {int(fields[0]): fields for fields in rows}
        component_to_surface = {}
        original_ids: Dict[int, Tuple[int, ...]] = {}
        for first, (last, _) in ranges.items():
            ids = tuple(range(first, last + 1))
            if any(word not in by_id or word in component_to_surface for word in ids):
                raise ValueError("invalid or overlapping CoNLL-U multiword range")
            original_ids[first] = ids
            component_to_surface.update({word: first for word in ids})
        cursor = 0
        tokens = []
        for fields in rows:
            token_id = int(fields[0])
            if token_id in component_to_surface and component_to_surface[token_id] != token_id:
                continue
            if token_id in ranges:
                last, form = ranges[token_id]
                ids = original_ids[token_id]
                anchor_id = contraction_anchor(ids, {word: int(row[6])
                                                      for word, row in by_id.items()})
                fields = by_id[anchor_id]
            else:
                form = fields[1]
                original_ids[token_id] = (token_id,)
            if sentence_text:
                start = sentence_text.find(form, cursor)
                if start < 0:
                    start = sentence_text.casefold().find(form.casefold(), cursor)
            else:
                start = -1
            end = start + len(form) if start >= 0 else -1
            if start >= 0:
                cursor = end
            head = int(fields[6])
            tokens.append(ParsedToken(
                id=token_id, text=form, lemma=fields[2], upos=fields[3],
                xpos=fields[4], feats=fields[5], head=component_to_surface.get(head, head),
                deprel=fields[7], start_char=start, end_char=end,
            ))
        if tokens:
            sentences.append((comments, tokens, original_ids))
    return sentences


def _projected_to_conllu(token: ProjectedToken, misc: str) -> str:
    return "\t".join((
        str(token.id), token.text, token.lemma, token.upos or "_", token.xpos or "_",
        token.feats or "_", str(token.head), token.deprel or "_", "_", misc or "_",
    ))
