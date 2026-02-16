"""
🧠 RUNE Memory — Persistent Enhancement Store
SQLite-backed history tracking for prompts, results, and preferences.
"""
import sqlite3
import json
import os
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass
class EnhancementRecord:
    id: int
    timestamp: str
    original_prompt: str
    enhanced_prompt: str
    model: str
    spinoza_score: float
    grade: str
    tokens_in: int
    tokens_out: int
    cost: float
    tags: list[str]


@dataclass
class UsageStats:
    total_runs: int
    total_cost: float
    avg_score: float
    best_score: float
    worst_score: float
    models_used: dict[str, int]
    grade_distribution: dict[str, int]
    first_run: str
    last_run: str


@dataclass
class PromptStats:
    prompt_hash: str
    use_count: int
    last_used: str
    avg_score: float


class MemoryStore:
    """SQLite-backed persistent store for RUNE enhancement history."""

    def __init__(self, db_path: str = "~/.rune/history.db") -> None:
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS enhancements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                original_prompt TEXT NOT NULL,
                enhanced_prompt TEXT NOT NULL,
                model TEXT NOT NULL,
                spinoza_score REAL NOT NULL DEFAULT 0.0,
                grade TEXT NOT NULL DEFAULT '',
                tokens_in INTEGER NOT NULL DEFAULT 0,
                tokens_out INTEGER NOT NULL DEFAULT 0,
                cost REAL NOT NULL DEFAULT 0.0,
                tags TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS prompt_usage (
                prompt_hash TEXT PRIMARY KEY,
                use_count INTEGER NOT NULL DEFAULT 0,
                last_used TEXT NOT NULL,
                avg_score REAL NOT NULL DEFAULT 0.0
            );
        """)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ── Enhancement logging ──────────────────────────────────────────

    def log_enhancement(
        self,
        original: str,
        enhanced: str,
        model: str,
        spinoza_score: float = 0.0,
        grade: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: float = 0.0,
        tags: Optional[list[str]] = None,
    ) -> int:
        """Save an enhancement run. Returns the new record id."""
        tags = tags or []
        ts = datetime.now().isoformat()
        cur = self._conn.execute(
            """INSERT INTO enhancements
               (timestamp, original_prompt, enhanced_prompt, model,
                spinoza_score, grade, tokens_in, tokens_out, cost, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ts, original, enhanced, model, spinoza_score, grade,
             tokens_in, tokens_out, cost, json.dumps(tags)),
        )
        # Update prompt_usage
        prompt_hash = hashlib.sha256(original.encode()).hexdigest()[:16]
        existing = self._conn.execute(
            "SELECT use_count, avg_score FROM prompt_usage WHERE prompt_hash = ?",
            (prompt_hash,),
        ).fetchone()
        if existing:
            new_count = existing["use_count"] + 1
            new_avg = (existing["avg_score"] * existing["use_count"] + spinoza_score) / new_count
            self._conn.execute(
                "UPDATE prompt_usage SET use_count = ?, last_used = ?, avg_score = ? WHERE prompt_hash = ?",
                (new_count, ts, new_avg, prompt_hash),
            )
        else:
            self._conn.execute(
                "INSERT INTO prompt_usage (prompt_hash, use_count, last_used, avg_score) VALUES (?, 1, ?, ?)",
                (prompt_hash, ts, spinoza_score),
            )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def _row_to_record(self, row: sqlite3.Row) -> EnhancementRecord:
        return EnhancementRecord(
            id=row["id"],
            timestamp=row["timestamp"],
            original_prompt=row["original_prompt"],
            enhanced_prompt=row["enhanced_prompt"],
            model=row["model"],
            spinoza_score=row["spinoza_score"],
            grade=row["grade"],
            tokens_in=row["tokens_in"],
            tokens_out=row["tokens_out"],
            cost=row["cost"],
            tags=json.loads(row["tags"]),
        )

    # ── History queries ──────────────────────────────────────────────

    def get_history(
        self,
        limit: int = 20,
        model: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> list[EnhancementRecord]:
        """Retrieve recent enhancement history with optional filters."""
        query = "SELECT * FROM enhancements WHERE 1=1"
        params: list = []
        if model is not None:
            query += " AND model = ?"
            params.append(model)
        if min_score is not None:
            query += " AND spinoza_score >= ?"
            params.append(min_score)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_record(r) for r in rows]

    def search_history(self, query: str) -> list[EnhancementRecord]:
        """Full-text search across original and enhanced prompts."""
        pattern = f"%{query}%"
        rows = self._conn.execute(
            """SELECT * FROM enhancements
               WHERE original_prompt LIKE ? OR enhanced_prompt LIKE ?
               ORDER BY id DESC""",
            (pattern, pattern),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    # ── Stats ────────────────────────────────────────────────────────

    def get_stats(self) -> UsageStats:
        """Aggregate usage statistics."""
        cur = self._conn
        row = cur.execute(
            """SELECT COUNT(*) as cnt, COALESCE(SUM(cost),0) as total_cost,
                      COALESCE(AVG(spinoza_score),0) as avg_s,
                      COALESCE(MAX(spinoza_score),0) as best,
                      COALESCE(MIN(spinoza_score),0) as worst,
                      MIN(timestamp) as first_run, MAX(timestamp) as last_run
               FROM enhancements"""
        ).fetchone()

        models: dict[str, int] = {}
        for m in cur.execute("SELECT model, COUNT(*) as c FROM enhancements GROUP BY model"):
            models[m["model"]] = m["c"]

        grades: dict[str, int] = {}
        for g in cur.execute("SELECT grade, COUNT(*) as c FROM enhancements GROUP BY grade"):
            grades[g["grade"]] = g["c"]

        return UsageStats(
            total_runs=row["cnt"],
            total_cost=row["total_cost"],
            avg_score=round(row["avg_s"], 4),
            best_score=row["best"],
            worst_score=row["worst"],
            models_used=models,
            grade_distribution=grades,
            first_run=row["first_run"] or "",
            last_run=row["last_run"] or "",
        )

    def get_prompt_stats(self, prompt_hash: str) -> Optional[PromptStats]:
        """Get usage stats for a specific prompt hash."""
        row = self._conn.execute(
            "SELECT * FROM prompt_usage WHERE prompt_hash = ?", (prompt_hash,)
        ).fetchone()
        if row is None:
            return None
        return PromptStats(
            prompt_hash=row["prompt_hash"],
            use_count=row["use_count"],
            last_used=row["last_used"],
            avg_score=row["avg_score"],
        )

    # ── Preferences ──────────────────────────────────────────────────

    def set_preference(self, key: str, value: str) -> None:
        self._conn.execute(
            """INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (key, value, datetime.now().isoformat()),
        )
        self._conn.commit()

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    # ── Maintenance ──────────────────────────────────────────────────

    def clear_history(self, before_date: Optional[str] = None) -> int:
        """Delete history records. Returns count deleted."""
        if before_date:
            cur = self._conn.execute(
                "DELETE FROM enhancements WHERE timestamp < ?", (before_date,)
            )
        else:
            cur = self._conn.execute("DELETE FROM enhancements")
            self._conn.execute("DELETE FROM prompt_usage")
        self._conn.commit()
        return cur.rowcount

    def export_history(self, path: str) -> int:
        """Export all enhancements as JSON. Returns count exported."""
        records = self.get_history(limit=999_999)
        data = [asdict(r) for r in records]
        export_path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(export_path) or ".", exist_ok=True)
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return len(data)

    # ── Display ──────────────────────────────────────────────────────

    @staticmethod
    def format_stats(stats: UsageStats) -> str:
        """Format usage stats for terminal display."""
        fav_model = max(stats.models_used, key=stats.models_used.get, default="—")  # type: ignore[arg-type]
        lines = [
            "╔══════════════════════════════════════╗",
            "║        🧠 RUNE Usage Statistics       ║",
            "╠══════════════════════════════════════╣",
            f"║  Total runs     : {stats.total_runs:<18}║",
            f"║  Total cost     : ${stats.total_cost:<17.4f}║",
            f"║  Avg score      : {stats.avg_score:<18.4f}║",
            f"║  Best / Worst   : {stats.best_score:.2f} / {stats.worst_score:<10.2f}  ║",
            f"║  Favorite model : {fav_model:<18}║",
            "╠══════════════════════════════════════╣",
            "║  Models used:                        ║",
        ]
        for model, count in sorted(stats.models_used.items(), key=lambda x: -x[1]):
            lines.append(f"║    {model:<20} × {count:<9}║")
        lines.append("╠══════════════════════════════════════╣")
        lines.append("║  Grade distribution:                 ║")
        for grade, count in sorted(stats.grade_distribution.items()):
            lines.append(f"║    {grade:<6} : {count:<24}║")
        lines.append("╠══════════════════════════════════════╣")
        lines.append(f"║  First run : {stats.first_run[:19]:<23}║")
        lines.append(f"║  Last run  : {stats.last_run[:19]:<23}║")
        lines.append("╚══════════════════════════════════════╝")
        return "\n".join(lines)
