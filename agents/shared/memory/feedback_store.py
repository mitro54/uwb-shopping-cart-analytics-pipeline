from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from agents.shared.config import CONFIG
from agents.shared.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class FeedbackExample:
    question: str
    sql_used: str | None
    answer: str
    similarity: float
    rating: str


class FeedbackStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._model: SentenceTransformer | None = None
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    sql_used TEXT,
                    schema_hash TEXT,
                    rating TEXT,
                    comment TEXT,
                    embedding TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_interactions_rating
                ON interactions(rating);

                CREATE INDEX IF NOT EXISTS idx_interactions_thread
                ON interactions(thread_id);
            """)

    def _embedder(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(CONFIG.embedding_model)
        return self._model

    def _embed(self, text: str) -> list[float]:
        return self._embedder().encode(text, normalize_embeddings=True).tolist()

    def save_interaction(
        self,
        *,
        thread_id: str,
        question: str,
        answer: str,
        sql_used: str | None,
        schema_hash: str | None,
    ) -> int:
        embedding = self._embed(question)
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO interactions (
                    ts, thread_id, question, answer, sql_used, schema_hash, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    thread_id,
                    question,
                    answer,
                    sql_used,
                    schema_hash,
                    json.dumps(embedding),
                ),
            )
            return int(cur.lastrowid)

    def save_feedback(self, interaction_id: int, rating: str, comment: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE interactions SET rating = ?, comment = ? WHERE id = ?",
                (rating.strip().lower(), comment.strip(), interaction_id),
            )

    def similar_good_examples(
        self,
        question: str,
        *,
        top_k: int = 3,
        min_similarity: float = 0.65,
        schema_hash: str | None = None,
    ) -> list[FeedbackExample]:
        query_emb = np.array(self._embed(question))
        with self._conn() as conn:
            if schema_hash:
                rows = conn.execute(
                    """
                    SELECT question, answer, sql_used, rating, embedding
                    FROM interactions
                    WHERE rating = 'good' AND schema_hash = ?
                    """,
                    (schema_hash,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT question, answer, sql_used, rating, embedding
                    FROM interactions
                    WHERE rating = 'good'
                    """
                ).fetchall()

        scored: list[FeedbackExample] = []
        for row in rows:
            emb = np.array(json.loads(row["embedding"]))
            score = float(np.dot(query_emb, emb))
            if score >= min_similarity:
                scored.append(
                    FeedbackExample(
                        question=row["question"],
                        answer=row["answer"],
                        sql_used=row["sql_used"],
                        similarity=score,
                        rating=row["rating"],
                    )
                )

        scored.sort(key=lambda item: item.similarity, reverse=True)
        return scored[:top_k]

    def similar_bad_examples(
        self,
        question: str,
        *,
        top_k: int = 2,
        min_similarity: float = 0.70,
    ) -> list[FeedbackExample]:
        query_emb = np.array(self._embed(question))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT question, answer, sql_used, rating, embedding
                FROM interactions
                WHERE rating = 'bad'
                """
            ).fetchall()

        scored: list[FeedbackExample] = []
        for row in rows:
            emb = np.array(json.loads(row["embedding"]))
            score = float(np.dot(query_emb, emb))
            if score >= min_similarity:
                scored.append(
                    FeedbackExample(
                        question=row["question"],
                        answer=row["answer"],
                        sql_used=row["sql_used"],
                        similarity=score,
                        rating=row["rating"],
                    )
                )

        scored.sort(key=lambda item: item.similarity, reverse=True)
        return scored[:top_k]

    def build_few_shot_block(self, question: str, schema_hash: str | None = None) -> str:
        examples = self.similar_good_examples(question, schema_hash=schema_hash)
        if not examples:
            return ""

        lines = [
            "Successful prior examples relevant to the current task:",
        ]
        for idx, ex in enumerate(examples, start=1):
            lines.append(f"Example {idx}")
            lines.append(f"Question: {ex.question}")
            if ex.sql_used:
                lines.append(f"SQL: {ex.sql_used[:600]}")
            lines.append(f"Answer style: {ex.answer[:500]}")
            lines.append("")
        return "\n".join(lines)

    def build_lessons_learned_block(self, question: str) -> str:
        examples = self.similar_bad_examples(question)
        if not examples:
            return ""

        lines = [
            "LESSONS LEARNED (Avoid these mistakes):",
        ]
        for idx, ex in enumerate(examples, start=1):
            lines.append(f"Warning {idx}")
            lines.append(f"Prior failed question: {ex.question}")
            lines.append(f"What went wrong (Answer was rated bad): {ex.answer[:400]}")
            lines.append("")
        return "\n".join(lines)

    def stats(self) -> dict[str, int]:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
            good = conn.execute("SELECT COUNT(*) FROM interactions WHERE rating = 'good'").fetchone()[0]
            bad = conn.execute("SELECT COUNT(*) FROM interactions WHERE rating = 'bad'").fetchone()[0]
            unrated = conn.execute("SELECT COUNT(*) FROM interactions WHERE rating IS NULL").fetchone()[0]
        return {"total": total, "good": good, "bad": bad, "unrated": unrated}
