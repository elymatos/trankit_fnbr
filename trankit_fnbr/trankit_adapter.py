from typing import Any, Dict, List, Mapping, Sequence

from .domain import ParsedToken


def contraction_anchor(ids: Sequence[int], heads: Mapping[int, int]) -> int:
    """Choose an external anchor whose redirected head cannot create a cycle."""
    components = set(ids)
    for word in ids:
        if heads[word] in components:
            continue
        current = heads[word]
        visited = set()
        while current and current not in visited and current not in components:
            visited.add(current)
            current = heads.get(current, 0)
        if current not in components:
            return word
    raise ValueError("contraction has no cycle-free external syntactic anchor")


class TrankitUDParser:
    def __init__(self, pipeline: Any, model_version: str = "trankit-1.1.2") -> None:
        self.pipeline = pipeline
        self.model_version = model_version

    def parse(self, text: str) -> Sequence[Sequence[ParsedToken]]:
        document = self.pipeline(text)
        sentences = document.get("sentences") or [document]
        result = []
        cursor = 0
        for sentence in sentences:
            parsed = []
            for raw in self._syntactic_words(sentence.get("tokens", [])):
                token_text = raw["text"]
                span = raw.get("dspan") or raw.get("span")
                if span and len(span) == 2:
                    start, end = int(span[0]), int(span[1])
                else:
                    start = text.find(token_text, cursor)
                    if start < 0:
                        start = cursor
                    end = start + len(token_text)
                cursor = end
                parsed.append(ParsedToken(
                    id=int(raw["id"]), text=token_text,
                    lemma=raw.get("lemma", token_text.casefold()),
                    upos=raw.get("upos", "_"), xpos=raw.get("xpos", "_"),
                    feats=self._features(raw.get("feats", "_")),
                    head=int(raw.get("head", 0)), deprel=raw.get("deprel", "_"),
                    start_char=start, end_char=end,
                ))
            result.append(parsed)
        return result

    @staticmethod
    def _syntactic_words(tokens: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return contraction-preserving words with dependencies redirected.

        Trankit exposes UD expansions beneath a surface MWT. FNBr patterns are
        keyed by the surface contraction, so the expansion is collapsed here
        before lexical recognition.
        """
        words: List[Dict[str, Any]] = []
        component_to_surface: Dict[int, int] = {}
        for token in tokens:
            expanded = token.get("expanded") or token.get("expanded_tokens")
            if expanded:
                surface_id = int(expanded[0]["id"])
                component_ids = {int(component["id"]) for component in expanded}
                for component_id in component_ids:
                    component_to_surface[component_id] = surface_id
                heads = {int(word["id"]): int(word.get("head", 0))
                         for item in tokens for word in (item.get("expanded") or
                         item.get("expanded_tokens") or [item]) if isinstance(word.get("id"), int)}
                anchor_id = contraction_anchor(sorted(component_ids), heads)
                anchor = next(word for word in expanded if int(word["id"]) == anchor_id)
                collapsed = dict(anchor)
                collapsed.update({
                    "id": surface_id,
                    "text": token["text"],
                    "lemma": token.get("lemma", token["text"].casefold()),
                    "dspan": token.get("dspan"),
                    "span": token.get("span"),
                })
                words.append(collapsed)
            elif isinstance(token.get("id"), int):
                words.append(dict(token))
        for word in words:
            head = int(word.get("head", 0))
            word["head"] = component_to_surface.get(head, head)
        return words

    @staticmethod
    def _features(value: Any) -> str:
        if isinstance(value, dict):
            return "|".join("{}={}".format(key, value[key]) for key in sorted(value)) or "_"
        return value or "_"
