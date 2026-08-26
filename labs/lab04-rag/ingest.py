#!/usr/bin/env python3
"""Chunk a guidance corpus, embed it, and index it into pgvector.

Runs in two modes, matching the rest of the labs:

  --dry-run (default when psycopg is not installed)
      Walk the corpus, chunk it, and report exactly what would be indexed.
      Needs nothing but a Python interpreter, so it works on a laptop during
      the event.

  live
      Embed each chunk against an OpenAI-compatible embeddings endpoint (the
      one you stood up in Lab 01 or Lab 03) and upsert into pgvector.

The chunking is deliberately boring: fixed window with overlap, split on
paragraph boundaries where it can. Published tax guidance is already
structured into short numbered sections, and clever splitters tend to break
that structure rather than respect it.

Environment for live mode:
  EMBED_ENDPOINT   default http://127.0.0.1:8000/v1/embeddings
  PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".md", ".adoc", ".html", ".htm"}


@dataclasses.dataclass
class Chunk:
    source: str
    ordinal: int
    text: str

    @property
    def uid(self) -> str:
        raw = f"{self.source}:{self.ordinal}:{self.text}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:32]


def read_documents(source: Path) -> list[tuple[str, str]]:
    """Return (relative path, text) for every readable document in the corpus."""
    docs: list[tuple[str, str]] = []
    if not source.exists():
        sys.exit(f"corpus not found: {source}")
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"  skipped {path}: {exc}", file=sys.stderr)
            continue
        if text.strip():
            docs.append((str(path.relative_to(source)), text))
    return docs


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Fixed window with overlap, preferring a paragraph break near the edge."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than chunk size")
    text = text.replace("\r\n", "\n")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            window = text.rfind("\n\n", start + size // 2, end)
            if window != -1:
                end = window
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def embed(texts: list[str], endpoint: str, model: str) -> list[list[float]]:
    payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
    request = urllib.request.Request(
        endpoint, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.load(response)
    except urllib.error.URLError as exc:
        sys.exit(
            f"embeddings endpoint unreachable at {endpoint}: {exc}\n"
            "Start the model from Lab 01, or re-run with --dry-run."
        )
    return [item["embedding"] for item in body["data"]]


def index(chunks: list[Chunk], endpoint: str, model: str, batch: int) -> None:
    try:
        import psycopg  # type: ignore
    except ImportError:
        sys.exit(
            "psycopg is not installed, so this run cannot reach pgvector.\n"
            "  pip install 'psycopg[binary]'\n"
            "Or re-run with --dry-run to walk the corpus without indexing."
        )

    dsn = (
        f"host={os.environ.get('PGHOST', 'localhost')} "
        f"port={os.environ.get('PGPORT', '5432')} "
        f"dbname={os.environ.get('PGDATABASE', 'tax_guidance')} "
        f"user={os.environ.get('PGUSER', 'postgres')} "
        f"password={os.environ.get('PGPASSWORD', '')}"
    )
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tax_guidance (
                uid       TEXT PRIMARY KEY,
                source    TEXT NOT NULL,
                ordinal   INTEGER NOT NULL,
                body      TEXT NOT NULL,
                embedding vector(768)
            )
            """
        )
        for offset in range(0, len(chunks), batch):
            window = chunks[offset : offset + batch]
            vectors = embed([c.text for c in window], endpoint, model)
            cur.executemany(
                """
                INSERT INTO tax_guidance (uid, source, ordinal, body, embedding)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (uid) DO UPDATE SET body = EXCLUDED.body,
                                                embedding = EXCLUDED.embedding
                """,
                [
                    (c.uid, c.source, c.ordinal, c.text, vec)
                    for c, vec in zip(window, vectors)
                ],
            )
            print(f"  indexed {min(offset + batch, len(chunks))}/{len(chunks)}")
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS tax_guidance_hnsw
            ON tax_guidance USING hnsw (embedding vector_cosine_ops)
            """
        )
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="./corpus", type=Path)
    parser.add_argument("--chunk", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=120)
    parser.add_argument("--embed-model", default="granite-embedding-125m")
    parser.add_argument(
        "--embed-endpoint",
        default=os.environ.get("EMBED_ENDPOINT", "http://127.0.0.1:8000/v1/embeddings"),
    )
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="chunk and report without embedding or indexing",
    )
    args = parser.parse_args()

    print(f"Scanning {args.source} ...")
    documents = read_documents(args.source)
    if not documents:
        print(
            "  no readable documents found.\n"
            "  Drop your published guidance into the corpus directory as .txt,\n"
            "  .md, .adoc or .html and run again."
        )
        return 1

    chunks: list[Chunk] = []
    for name, text in documents:
        pieces = chunk_text(text, args.chunk, args.overlap)
        chunks.extend(Chunk(name, i, p) for i, p in enumerate(pieces))
        print(f"  {name:<48} {len(text):>8,} chars  {len(pieces):>6,} chunks")

    print(f"  total {len(chunks):,} chunks from {len(documents)} documents")

    if args.dry_run:
        print("\nDry run: nothing embedded, nothing indexed.")
        print("Re-run without --dry-run once pgvector and the embeddings")
        print("endpoint are reachable.")
        return 0

    index(chunks, args.embed_endpoint, args.embed_model, args.batch)
    print(f"Indexed {len(chunks):,} chunks into pgvector.tax_guidance (HNSW)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
