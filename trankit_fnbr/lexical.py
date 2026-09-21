import re
from dataclasses import replace
from typing import Iterable, List, Optional, Sequence, Set, Tuple

from .domain import Lemma, LexicalAnalysis, LexicalToken, ParsedToken, Pattern
from .repository import LexiconRepository


_ELEMENT_RE = re.compile(r"\{[^}]+\}[+*]?|\[[^]]+\]|<[^>]+>|\([^()]+\)[+*]?|[^\s]+")
_SOURCE_PRIORITY = {"fixed": 2, "variable": 1, "ordinary": 0}


class LexicalProcessor:
    """Build a lexical lattice and its deterministic non-overlapping projection."""

    policy_version = "1"

    def __init__(self, repository: LexiconRepository) -> None:
        self.repository = repository

    def process(self, tokens: Sequence[ParsedToken], language: str = "pt") -> LexicalAnalysis:
        if not tokens:
            return LexicalAnalysis((), (), self.repository.revision, self.policy_version)

        lattice = self._ordinary_candidates(tokens, language)
        patterns = tuple(self.repository.patterns(language))
        self._patterns_by_name = {pattern.name: pattern for pattern in patterns}
        self._matching_stack: Set[Tuple[int, int]] = set()
        for pattern in patterns:
            lattice.extend(self._pattern_candidates(pattern, tokens))

        selected = self._select(lattice, tokens)
        return LexicalAnalysis(tuple(lattice), tuple(selected), self.repository.revision, self.policy_version)

    def _ordinary_candidates(self, tokens: Sequence[ParsedToken], language: str) -> List[LexicalToken]:
        result: List[LexicalToken] = []
        for token in tokens:
            lemmas = tuple(self.repository.lemmas_for(token.text, token.upos, language))
            selected = lemmas[0] if len(lemmas) == 1 else None
            result.append(LexicalToken(
                id="token:{}".format(token.id), text=token.text,
                start_token=token.id, end_token=token.id,
                start_char=token.start_char, end_char=token.end_char,
                components=(token.id,), lemma_candidates=lemmas,
                selected_lemma=selected,
            ))
        return result

    def _pattern_candidates(self, pattern: Pattern, tokens: Sequence[ParsedToken]) -> List[LexicalToken]:
        result: List[LexicalToken] = []
        elements = _ELEMENT_RE.findall(pattern.expression.strip())
        if not elements:
            return result
        source = pattern.source
        if pattern.name.startswith("$"):
            source = "construction"
        elif all(not element.startswith(("{", "[", "(")) for element in elements):
            source = "fixed" if pattern.source == "variable" else pattern.source

        for start in range(len(tokens)):
            ends = self._match_sequence(elements, tokens, start)
            for end in sorted(ends):
                if end <= start:
                    continue
                matched = tokens[start:end]
                text = " ".join(token.text for token in matched)
                result.append(LexicalToken(
                    id="lemma:{}:{}-{}".format(pattern.lemma_id, matched[0].id, matched[-1].id),
                    text=text, start_token=matched[0].id, end_token=matched[-1].id,
                    start_char=matched[0].start_char, end_char=matched[-1].end_char,
                    components=tuple(token.id for token in matched),
                    lemma_candidates=(pattern.lemma,), selected_lemma=pattern.lemma,
                    source=source, reviewed=pattern.reviewed,
                ))
        return result

    def _match_sequence(
        self, elements: Sequence[str], tokens: Sequence[ParsedToken], start: int
    ) -> Set[int]:
        positions = {start}
        for element in elements:
            next_positions: Set[int] = set()
            optional = element.startswith("[") and element.endswith("]")
            mandatory = element.startswith("<") and element.endswith(">")
            inner = element[1:-1].strip() if optional or mandatory else element
            if optional:
                next_positions.update(positions)
            inner_elements = _ELEMENT_RE.findall(inner)
            for position in positions:
                if optional and len(inner_elements) > 1:
                    next_positions.update(self._match_sequence(inner_elements, tokens, position))
                else:
                    next_positions.update(self._match_element(inner, tokens, position))
            positions = next_positions
            if not positions:
                break
        return positions

    def _match_element(self, element: str, tokens: Sequence[ParsedToken], position: int) -> Set[int]:
        repeated = element.endswith(("+", "*"))
        if repeated:
            base = element[:-1]
            positions = {position}
            frontier = {position}
            while frontier:
                next_frontier: Set[int] = set()
                for current in frontier:
                    next_frontier.update(self._match_element(base, tokens, current))
                next_frontier -= positions
                positions.update(next_frontier)
                frontier = next_frontier
            if element.endswith("+"):
                positions.discard(position)
            return positions
        if position >= len(tokens):
            return set()
        if element.startswith("(") and element.endswith(")"):
            result: Set[int] = set()
            for alternative in element[1:-1].split("|"):
                result.update(self._match_sequence(_ELEMENT_RE.findall(alternative.strip()), tokens, position))
            return result
        token = tokens[position]
        if element == "{*}":
            return {position + 1}
        if element.startswith("{") and element.endswith("}"):
            constraint = element[1:-1].split("@", 1)[0]
            if constraint.startswith("$"):
                referenced = self._patterns_by_name.get(constraint)
                if referenced is None:
                    return set()
                marker = (referenced.lemma_id, position)
                if marker in self._matching_stack:
                    return set()
                self._matching_stack.add(marker)
                try:
                    return self._match_sequence(
                        _ELEMENT_RE.findall(referenced.expression.strip()), tokens, position
                    )
                finally:
                    self._matching_stack.remove(marker)
            if constraint.startswith("CE:"):
                return set()
            upos, _, feature = constraint.partition(":")
            allowed_upos = upos.split("|")
            if token.upos not in allowed_upos:
                return set()
            if feature and feature.casefold() not in token.feats.casefold():
                return set()
            return {position + 1}
        return {position + 1} if token.text.casefold() == element.casefold() else set()

    def _select(
        self, lattice: Sequence[LexicalToken], tokens: Sequence[ParsedToken]
    ) -> List[LexicalToken]:
        lexical_candidates = [
            candidate for candidate in lattice
            if candidate.source not in {"ordinary", "construction"}
        ]
        lexical_candidates.sort(key=lambda candidate: (
            -int(candidate.reviewed),
            -_SOURCE_PRIORITY.get(candidate.source, 0),
            -len(candidate.components),
            candidate.selected_lemma.id if candidate.selected_lemma else 2 ** 63,
            candidate.start_token,
        ))
        selected: List[LexicalToken] = []
        occupied: Set[int] = set()
        for candidate in lexical_candidates:
            component_set = set(candidate.components)
            if not component_set.intersection(occupied):
                selected.append(candidate)
                occupied.update(component_set)
        ordinary = {candidate.start_token: candidate for candidate in lattice if candidate.source == "ordinary"}
        for token in tokens:
            if token.id not in occupied:
                selected.append(ordinary[token.id])
        selected.sort(key=lambda candidate: candidate.start_token)
        return selected
