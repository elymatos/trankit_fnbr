from dataclasses import dataclass
from typing import Dict, List, Sequence, Set

from .domain import LexicalToken, ParsedToken


class ProjectionError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectedToken:
    id: int
    text: str
    lemma: str
    upos: str
    xpos: str
    feats: str
    head: int
    deprel: str
    lexical_token_id: str
    source_token_ids: tuple


def project_dependencies(
    source_tokens: Sequence[ParsedToken], selected: Sequence[LexicalToken]
) -> List[ProjectedToken]:
    source = {token.id: token for token in source_tokens}
    component_to_lexical: Dict[int, int] = {}
    for projected_id, lexical in enumerate(selected, 1):
        for component in lexical.components:
            if component in component_to_lexical:
                raise ProjectionError("selected lexical spans overlap")
            if component not in source:
                raise ProjectionError("unknown source token {}".format(component))
            component_to_lexical[component] = projected_id
    if set(component_to_lexical) != set(source):
        raise ProjectionError("selected sequence does not cover every source token")

    result: List[ProjectedToken] = []
    for projected_id, lexical in enumerate(selected, 1):
        component_ids = set(lexical.components)
        anchors = [source[token_id] for token_id in lexical.components
                   if source[token_id].head not in component_ids]
        if len(anchors) != 1:
            raise ProjectionError(
                "lexical token {} must have exactly one external syntactic head".format(lexical.id)
            )
        anchor = anchors[0]
        projected_head = 0 if anchor.head == 0 else component_to_lexical[anchor.head]
        selected_lemma = lexical.selected_lemma
        result.append(ProjectedToken(
            id=projected_id,
            text=lexical.text,
            lemma=selected_lemma.name if selected_lemma else anchor.lemma,
            upos=anchor.upos,
            xpos=anchor.xpos,
            feats=anchor.feats,
            head=projected_head,
            deprel=anchor.deprel,
            lexical_token_id=lexical.id,
            source_token_ids=lexical.components,
        ))
    _validate_tree(result)
    return result


def _validate_tree(tokens: Sequence[ProjectedToken]) -> None:
    roots = [token.id for token in tokens if token.head == 0]
    if len(roots) != 1:
        raise ProjectionError("projected tree must have exactly one root")
    valid_ids = {token.id for token in tokens}
    for token in tokens:
        if token.head not in valid_ids and token.head != 0:
            raise ProjectionError("projected tree contains an unknown head")
        if token.head == token.id:
            raise ProjectionError("projected tree contains a self-loop")
        visited: Set[int] = set()
        cursor = token
        by_id = {item.id: item for item in tokens}
        while cursor.head:
            if cursor.id in visited:
                raise ProjectionError("projected tree contains a cycle")
            visited.add(cursor.id)
            cursor = by_id[cursor.head]
