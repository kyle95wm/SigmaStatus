import sqlite3
from datetime import datetime, timezone
from typing import Optional


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReportDB:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._ensure_schema()

    # ---------------- Schema helpers ----------------

    def _table_columns(self, table: str) -> list[str]:
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        return [r[1] for r in cur.fetchall()]

    def _ensure_column(self, table: str, col: str, decl: str) -> None:
        cols = self._table_columns(table)
        if col not in cols:
            cur = self.conn.cursor()
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            self.conn.commit()

    def _ensure_schema(self) -> None:
        cur = self.conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS plex_liveboards (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS plex_statuses (
                guild_id INTEGER NOT NULL,
                server_name TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, server_name)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS plex_manual_overrides (
                guild_id INTEGER NOT NULL,
                server_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, server_name)
            )
            """
        )

        self.conn.commit()
        self._ensure_column("plex_manual_overrides", "staff_message_id", "INTEGER")

        # Default setting values
        if self._get_setting("report_pings_enabled") is None:
            self._set_setting("report_pings_enabled", "1")

    # ---------------- Settings ----------------

    def _get_setting(self, key: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None

    def _set_setting(self, key: str, value: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    # ---------------- Report pings ----------------

    def get_report_pings_enabled(self) -> bool:
        v = self._get_setting("report_pings_enabled")
        return v != "0"

    def toggle_report_pings(self) -> bool:
        enabled = self.get_report_pings_enabled()
        new_val = "0" if enabled else "1"
        self._set_setting("report_pings_enabled", new_val)
        return new_val == "1"

    # ---------------- Plex liveboard ----------------

    def set_plex_liveboard(self, guild_id: int, channel_id: int, message_id: int):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO plex_liveboards (guild_id, channel_id, message_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id)
            DO UPDATE SET channel_id=excluded.channel_id,
                          message_id=excluded.message_id
            """,
            (int(guild_id), int(channel_id), int(message_id)),
        )
        self.conn.commit()

    def get_plex_liveboard(self, guild_id: int):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT guild_id, channel_id, message_id FROM plex_liveboards WHERE guild_id=?",
            (int(guild_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "guild_id": row["guild_id"],
            "channel_id": row["channel_id"],
            "message_id": row["message_id"],
        }

    def list_plex_liveboards(self) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT guild_id, channel_id, message_id FROM plex_liveboards")
        rows = cur.fetchall()
        return [
            {"guild_id": r["guild_id"], "channel_id": r["channel_id"], "message_id": r["message_id"]}
            for r in rows
        ]

    def clear_plex_liveboard(self, guild_id: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM plex_liveboards WHERE guild_id=?", (int(guild_id),))
        self.conn.commit()

    # ---------------- Plex statuses ----------------

    def set_plex_status(self, guild_id: int, server_name: str, status: str, updated_at: Optional[str] = None):
        now = updated_at or _utcnow_iso()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO plex_statuses (guild_id, server_name, status, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, server_name)
            DO UPDATE SET status=excluded.status,
                          updated_at=excluded.updated_at
            """,
            (int(guild_id), str(server_name).upper(), str(status), now),
        )
        self.conn.commit()

    def set_plex_manual_override(
        self,
        guild_id: int,
        server_name: str,
        is_active: bool,
        staff_message_id: Optional[int] = None,
    ):
        cur = self.conn.cursor()
        server_name = str(server_name).upper()

        if is_active:
            cur.execute(
                """
                INSERT INTO plex_manual_overrides (guild_id, server_name, created_at, staff_message_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, server_name)
                DO UPDATE SET created_at=excluded.created_at,
                              staff_message_id=COALESCE(excluded.staff_message_id, plex_manual_overrides.staff_message_id)
                """,
                (int(guild_id), server_name, _utcnow_iso(), int(staff_message_id) if staff_message_id else None),
            )
        else:
            cur.execute(
                "DELETE FROM plex_manual_overrides WHERE guild_id=? AND server_name=?",
                (int(guild_id), server_name),
            )

        self.conn.commit()

    def has_plex_manual_override(self, guild_id: int, server_name: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM plex_manual_overrides WHERE guild_id=? AND server_name=?",
            (int(guild_id), str(server_name).upper()),
        )
        return cur.fetchone() is not None

    def get_plex_manual_override(self, guild_id: int, server_name: str) -> Optional[dict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT guild_id, server_name, created_at, staff_message_id
            FROM plex_manual_overrides
            WHERE guild_id=? AND server_name=?
            """,
            (int(guild_id), str(server_name).upper()),
        )
        row = cur.fetchone()
        if not row:
            return None

        return {
            "guild_id": row["guild_id"],
            "server_name": row["server_name"],
            "created_at": row["created_at"],
            "staff_message_id": row["staff_message_id"],
        }

    def clear_plex_manual_overrides(self, guild_id: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM plex_manual_overrides WHERE guild_id=?", (int(guild_id),))
        self.conn.commit()

    def get_plex_statuses(self, guild_id: int) -> dict[str, str]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT server_name, status FROM plex_statuses WHERE guild_id=?",
            (int(guild_id),),
        )
        rows = cur.fetchall()
        out: dict[str, str] = {}
        for r in rows:
            out[str(r["server_name"]).upper()] = str(r["status"])
        return out

    def clear_plex_statuses(self, guild_id: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM plex_statuses WHERE guild_id=?", (int(guild_id),))
        self.conn.commit()
