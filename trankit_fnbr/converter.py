import hashlib
from typing import Dict, List, Sequence, Tuple

from .domain import ParsedToken
from .lexical import LexicalProcessor
from .projection import ProjectedToken, project_dependencies


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
    for comments, tokens in _parse_conllu(source):
        analysis = processor.process(tokens, language)
        projected = project_dependencies(tokens, analysis.selected)
        lines = list(comments)
        for token, lexical in zip(projected, analysis.selected):
            misc = []
            if lexical.selected_lemma and lexical.selected_lemma.lemma_type:
                misc.append("FNBRType={}".format(lexical.selected_lemma.lemma_type))
            elif len(lexical.lemma_candidates) > 1:
                misc.append("FNBRStatus=ambiguous")
                unresolved_count += 1
            else:
                misc.append("FNBRStatus=unresolved")
                unresolved_count += 1
            lines.append(_projected_to_conllu(token, "|".join(misc)))
        output_sentences.append("\n".join(lines))
        sentence_id = next((line.split("=", 1)[1].strip() for line in comments
                            if line.startswith("# sent_id =")), str(converted_count + 1))
        instances.append({
            "source_sentence_id": sentence_id,
            "source_token_ids": [token.id for token in tokens],
            "selected": [
                {
                    "lexical_token_id": item.id,
                    "source_token_ids": list(item.components),
                    "selected_lemma_id": item.selected_lemma.id if item.selected_lemma else None,
                }
                for item in analysis.selected
            ],
            "lattice": [
                {
                    "lexical_token_id": item.id,
                    "source_token_ids": list(item.components),
                    "lemma_candidate_ids": [lemma.id for lemma in item.lemma_candidates],
                    "source": item.source,
                }
                for item in analysis.lattice
            ],
        })
        converted_count += 1
    output = "\n\n".join(output_sentences) + ("\n" if output_sentences else "")
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
        "instances": instances,
    }
    return output, manifest


def _parse_conllu(source: str) -> List[Tuple[List[str], List[ParsedToken]]]:
    sentences = []
    for block in source.strip().split("\n\n"):
        comments = []
        rows = []
        sentence_text = ""
        for line in block.splitlines():
            if line.startswith("#"):
                comments.append(line)
                if line.startswith("# text = "):
                    sentence_text = line[len("# text = "):]
                continue
            fields = line.split("\t")
            if len(fields) != 10 or "-" in fields[0] or "." in fields[0]:
                continue
            rows.append(fields)
        cursor = 0
        tokens = []
        for fields in rows:
            form = fields[1]
            start = sentence_text.find(form, cursor) if sentence_text else cursor
            if start < 0:
                start = cursor
            end = start + len(form)
            cursor = end
            tokens.append(ParsedToken(
                id=int(fields[0]), text=form, lemma=fields[2], upos=fields[3],
                xpos=fields[4], feats=fields[5], head=int(fields[6]),
                deprel=fields[7], start_char=start, end_char=end,
            ))
        if tokens:
            sentences.append((comments, tokens))
    return sentences


def _projected_to_conllu(token: ProjectedToken, misc: str) -> str:
    return "\t".join((
        str(token.id), token.text, token.lemma, token.upos or "_", token.xpos or "_",
        token.feats or "_", str(token.head), token.deprel or "_", "_", misc or "_",
    ))
