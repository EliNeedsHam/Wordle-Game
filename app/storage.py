import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .game import MAX_GUESSES


DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "instance" / "wordforge.sqlite3"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path=None):
        self.path = Path(path or DEFAULT_DATA_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    created_at TEXT NOT NULL,
                    games_played INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    max_streak INTEGER NOT NULL DEFAULT 0,
                    guess_1 INTEGER NOT NULL DEFAULT 0,
                    guess_2 INTEGER NOT NULL DEFAULT 0,
                    guess_3 INTEGER NOT NULL DEFAULT 0,
                    guess_4 INTEGER NOT NULL DEFAULT 0,
                    guess_5 INTEGER NOT NULL DEFAULT 0,
                    guess_6 INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL,
                    answer TEXT NOT NULL,
                    gif_url TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY(profile_id) REFERENCES profiles(id)
                );

                CREATE TABLE IF NOT EXISTS guesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    guess_index INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(game_id) REFERENCES games(id)
                );
                """
            )
            columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(games)").fetchall()
            }
            if "gif_url" not in columns:
                conn.execute("ALTER TABLE games ADD COLUMN gif_url TEXT")

    def list_profiles(self):
        with self.connect() as conn:
            rows = conn.execute("SELECT id, name, created_at FROM profiles ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def create_profile(self, name):
        clean_name = " ".join((name or "").strip().split())
        if not clean_name:
            raise ValueError("Profile name is required.")
        if len(clean_name) > 24:
            raise ValueError("Profile name must be 24 characters or fewer.")

        with self.connect() as conn:
            try:
                cursor = conn.execute(
                    "INSERT INTO profiles (name, created_at) VALUES (?, ?)",
                    (clean_name, utc_now()),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("A profile with that name already exists.") from exc
            profile_id = cursor.lastrowid
            row = conn.execute(
                "SELECT id, name, created_at FROM profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        return dict(row)

    def get_profile(self, profile_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return dict(row) if row else None

    def create_game(self, profile_id, answer, gif_url=None):
        with self.connect() as conn:
            conn.execute(
                "UPDATE games SET status = 'abandoned' WHERE profile_id = ? AND status = 'active'",
                (profile_id,),
            )
            cursor = conn.execute(
                """
                INSERT INTO games (profile_id, answer, gif_url, status, created_at)
                VALUES (?, ?, ?, 'active', ?)
                """,
                (profile_id, answer, gif_url, utc_now()),
            )
            game_id = cursor.lastrowid
        return self.get_game(game_id)

    def get_current_game(self, profile_id):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM games
                WHERE profile_id = ? AND status = 'active'
                ORDER BY id DESC LIMIT 1
                """,
                (profile_id,),
            ).fetchone()
        return self._game_with_guesses(dict(row)) if row else None

    def get_game(self, game_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        return self._game_with_guesses(dict(row)) if row else None

    def add_guess(self, game_id, word, pattern):
        game = self.get_game(game_id)
        if not game:
            raise ValueError("Game not found.")
        guess_index = len(game["guesses"]) + 1
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO guesses (game_id, guess_index, word, pattern, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (game_id, guess_index, word, json.dumps(pattern), utc_now()),
            )
        return self.get_game(game_id)

    def complete_game(self, game_id, status, guess_count):
        if status not in {"won", "lost"}:
            raise ValueError("Completed status must be won or lost.")
        game = self.get_game(game_id)
        if not game or game["status"] != "active":
            return game

        with self.connect() as conn:
            conn.execute(
                "UPDATE games SET status = ?, completed_at = ? WHERE id = ?",
                (status, utc_now(), game_id),
            )
            profile = conn.execute(
                "SELECT * FROM profiles WHERE id = ?", (game["profile_id"],)
            ).fetchone()
            if status == "won":
                streak = profile["current_streak"] + 1
                max_streak = max(profile["max_streak"], streak)
                conn.execute(
                    f"""
                    UPDATE profiles
                    SET games_played = games_played + 1,
                        wins = wins + 1,
                        current_streak = ?,
                        max_streak = ?,
                        guess_{guess_count} = guess_{guess_count} + 1
                    WHERE id = ?
                    """,
                    (streak, max_streak, game["profile_id"]),
                )
            else:
                conn.execute(
                    """
                    UPDATE profiles
                    SET games_played = games_played + 1,
                        losses = losses + 1,
                        current_streak = 0
                    WHERE id = ?
                    """,
                    (game["profile_id"],),
                )
        return self.get_game(game_id)

    def stats_for_profile(self, profile_id):
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        games_played = profile["games_played"]
        win_percentage = round((profile["wins"] / games_played) * 100) if games_played else 0
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, status, answer, created_at, completed_at
                FROM games
                WHERE profile_id = ? AND status IN ('won', 'lost')
                ORDER BY id DESC LIMIT 8
                """,
                (profile_id,),
            ).fetchall()
        return {
            "games_played": games_played,
            "wins": profile["wins"],
            "losses": profile["losses"],
            "win_percentage": win_percentage,
            "current_streak": profile["current_streak"],
            "max_streak": profile["max_streak"],
            "guess_distribution": {
                str(index): profile[f"guess_{index}"] for index in range(1, MAX_GUESSES + 1)
            },
            "recent_games": [dict(row) for row in rows],
        }

    def _game_with_guesses(self, game):
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT guess_index, word, pattern, created_at
                FROM guesses
                WHERE game_id = ?
                ORDER BY guess_index
                """,
                (game["id"],),
            ).fetchall()
        game["guesses"] = [
            {
                "index": row["guess_index"],
                "word": row["word"],
                "pattern": json.loads(row["pattern"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
        return game
