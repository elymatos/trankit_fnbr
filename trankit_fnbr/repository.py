from typing import Dict, Iterable, List, Mapping, Protocol, Sequence, Tuple

from .domain import Lemma, ParsedToken, Pattern


class LexiconRepository(Protocol):
    @property
    def revision(self) -> str:
        ...

    def lemmas_for(self, form: str, upos: str, language: str) -> Sequence[Lemma]:
        ...

    def patterns(self, language: str) -> Sequence[Pattern]:
        ...


class InMemoryLexiconRepository:
    def __init__(
        self,
        revision: str,
        forms: Mapping[str, Sequence[Lemma]],
        patterns: Sequence[Pattern],
    ) -> None:
        self._revision = revision
        self._forms = {key.casefold(): tuple(value) for key, value in forms.items()}
        self._patterns = tuple(patterns)

    @property
    def revision(self) -> str:
        return self._revision

    def lemmas_for(self, form: str, upos: str, language: str) -> Sequence[Lemma]:
        candidates = self._forms.get(form.casefold(), ())
        exact = tuple(lemma for lemma in candidates if not lemma.upos or lemma.upos == upos)
        return exact or candidates

    def patterns(self, language: str) -> Sequence[Pattern]:
        return self._patterns
