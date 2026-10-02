#!/usr/bin/env python3
"""Smoke-test a running FNBr HTTP service (no database credentials needed)."""
import argparse
import json
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8405")
    parser.add_argument("--text", default="Ele tomou o café da manhã logo cedo.")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    with urlopen(base + "/health/ready", timeout=30) as response:
        readiness = json.load(response)
    if readiness.get("status") != "ready":
        raise RuntimeError("FNBr service is not ready")
    request = Request(
        base + "/fnbr/", method="POST",
        data=json.dumps({"text": args.text, "top_k": 3}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=120) as response:
        analysis = json.load(response)
    if (analysis.get("model_version") != readiness.get("model_version") or
            analysis.get("scaffold_source") != readiness.get("scaffold_source")):
        raise RuntimeError("FNBr readiness and analysis use different models")
    tokens = [token for sentence in analysis["sentences"] for token in sentence["tokens"]]
    if not tokens or any("lemma_type_candidates" not in token for token in tokens):
        raise RuntimeError("FNBr analysis is missing lexical type predictions")
    if analysis["scaffold_source"] == "model" and any(
            "projected_head" not in token for token in tokens):
        raise RuntimeError("joint model output is missing projected-tree provenance")
    print("HTTP OK: {} tokens, model {}, scaffold {}".format(
        len(tokens), analysis["model_version"], analysis["scaffold_source"]
    ))


if __name__ == "__main__":
    main()
