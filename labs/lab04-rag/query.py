#!/usr/bin/env python3
"""Answer a question from the indexed guidance corpus, with citations.

The important behaviour in this file is not the answer. It is the refusal.

RELEVANCE_THRESHOLD is the line between "I found supporting guidance" and
"I did not". Below it the script refuses and refers, and returns exit code 3
so a calling workflow can route the contact to a human. A retrieval system
that always answers is worse than no retrieval system, because it launders a
guess into something that looks sourced.

  --explain   print the retrieval trace instead of an answer, so you can show
              a governance board why a refusal happened.

Environment:
  INFERENCE_ENDPOINT  default http://127.0.0.1:8000/v1/chat/completions
  EMBED_ENDPOINT      default http://127.0.0.1:8000/v1/embeddings
  PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

RELEVANCE_THRESHOLD = 0.75
TOP_K = 6

SYSTEM_PROMPT = """You answer questions about tax administration for agency
staff, using only the numbered guidance passages provided. Rules:

1. Use only the passages given. Do not add knowledge from anywhere else.
2. Cite the passage number for every claim you make.
3. If the passages do not answer the question, say so plainly and recommend
   referral to a specialist. Do not guess.
4. Never state a determination about a specific taxpayer as final. You are
   drafting for a human reviewer who edits and signs.
"""


def post_json(url: str, payload: dict, timeout: int = 120) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        sys.exit(f"endpoint unreachable at {url}: {exc}")


def retrieve(question: str, embed_endpoint: str, embed_model: str) -> list[dict]:
    try:
        import psycopg  # type: ignore
    except ImportError:
        sys.exit(
            "psycopg is not installed.\n"
            "  pip install 'psycopg[binary]'\n"
            "Run labs/lab04-rag/run.sh in simulate mode to walk this lab "
            "without a database."
        )

    body = post_json(embed_endpoint, {"model": embed_model, "input": [question]})
    vector = body["data"][0]["embedding"]

    dsn = (
        f"host={os.environ.get('PGHOST', 'localhost')} "
        f"port={os.environ.get('PGPORT', '5432')} "
        f"dbname={os.environ.get('PGDATABASE', 'tax_guidance')} "
        f"user={os.environ.get('PGUSER', 'postgres')} "
        f"password={os.environ.get('PGPASSWORD', '')}"
    )
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT source, ordinal, body, 1 - (embedding <=> %s::vector) AS score
            FROM tax_guidance
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vector, vector, TOP_K),
        )
        return [
            {"source": r[0], "ordinal": r[1], "body": r[2], "score": float(r[3])}
            for r in cur.fetchall()
        ]


def answer(question: str, passages: list[dict], endpoint: str, model: str) -> str:
    context = "\n\n".join(
        f"[{i + 1}] ({p['source']}, chunk {p['ordinal']})\n{p['body']}"
        for i, p in enumerate(passages)
    )
    body = post_json(
        endpoint,
        {
            "model": model,
            "temperature": 0.1,
            "max_tokens": 600,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Guidance passages:\n\n{context}\n\nQuestion: {question}",
                },
            ],
        },
    )
    return body["choices"][0]["message"]["content"].strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--model", default="granite-8b-tax-v1")
    parser.add_argument("--embed-model", default="granite-embedding-125m")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get(
            "INFERENCE_ENDPOINT", "http://127.0.0.1:8000/v1/chat/completions"
        ),
    )
    parser.add_argument(
        "--embed-endpoint",
        default=os.environ.get("EMBED_ENDPOINT", "http://127.0.0.1:8000/v1/embeddings"),
    )
    args = parser.parse_args()

    candidates = retrieve(args.question, args.embed_endpoint, args.embed_model)
    passing = [c for c in candidates if c["score"] >= RELEVANCE_THRESHOLD]

    if args.explain:
        print("retrieval trace:")
        for i, c in enumerate(candidates, 1):
            verdict = "accepted" if c["score"] >= RELEVANCE_THRESHOLD else "REJECTED"
            label = f"{c['source']}, chunk {c['ordinal']}"
            print(f"  candidate {i}  {label:<44} score {c['score']:.3f}  {verdict}")
        print(f"  {'threshold':<57} {RELEVANCE_THRESHOLD:.3f}")
        print(f"  {'passing candidates':<57} {len(passing)}")
        print("decision:", "answer from guidance" if passing else "refuse and refer")
        return 0 if passing else 3

    if not passing:
        print(
            "I do not have guidance covering this question in the indexed corpus.\n"
            "Refer this to a specialist rather than relying on this answer.\n"
        )
        print(f"sources: none above threshold ({RELEVANCE_THRESHOLD})")
        return 3

    print(answer(args.question, passing, args.endpoint, args.model))
    print("\nsources:")
    for i, p in enumerate(passing, 1):
        print(f"  [{i}] {p['source']}, chunk {p['ordinal']:<6} score {p['score']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
