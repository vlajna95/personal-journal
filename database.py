"""Database layer for the Personal Journal app.

All note subjects and content are stored encrypted.
The database itself is plain SQLite; field-level Fernet encryption
protects the journal data with a password-derived key.
"""

import base64
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

import crypto_utils

DB_PATH = Path(__file__).parent / "journal.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            note_date  TEXT    NOT NULL,
            subject    TEXT    NOT NULL,
            content    TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_notes_date ON notes (note_date);

        CREATE TABLE IF NOT EXISTS alarms (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            subject    TEXT NOT NULL,
            note       TEXT NOT NULL,
            alarm_dt   TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_alarms_dt ON alarms (alarm_dt);
        """
    )

    # Multi-diary schema: check whether diary table already has diary_id column.
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(diary)").fetchall()}
    if not cols:
        # Fresh database — create diaries + diary tables with full schema.
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS diaries (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS diary (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT    NOT NULL,
                diary_id   INTEGER NOT NULL DEFAULT 1,
                content    TEXT    NOT NULL,
                updated_at TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(entry_date, diary_id),
                FOREIGN KEY(diary_id) REFERENCES diaries(id)
            );

            CREATE INDEX IF NOT EXISTS idx_diary_date     ON diary (entry_date);
            CREATE INDEX IF NOT EXISTS idx_diary_diary_id ON diary (diary_id);
            """
        )
    elif "diary_id" not in cols:
        # Existing single-diary database — migrate to multi-diary schema.
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS diaries (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );

            INSERT OR IGNORE INTO diaries (id, name) VALUES (1, '');

            CREATE TABLE IF NOT EXISTS diary_new (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT    NOT NULL,
                diary_id   INTEGER NOT NULL DEFAULT 1,
                content    TEXT    NOT NULL,
                updated_at TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(entry_date, diary_id),
                FOREIGN KEY(diary_id) REFERENCES diaries(id)
            );

            INSERT INTO diary_new (id, entry_date, diary_id, content, updated_at)
                SELECT id, entry_date, 1, content, updated_at FROM diary;

            DROP TABLE diary;
            ALTER TABLE diary_new RENAME TO diary;

            CREATE INDEX IF NOT EXISTS idx_diary_date     ON diary (entry_date);
            CREATE INDEX IF NOT EXISTS idx_diary_diary_id ON diary (diary_id);
            """
        )
    else:
        # Schema already up to date — ensure diaries table and indexes exist.
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS diaries (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_diary_date     ON diary (entry_date);
            CREATE INDEX IF NOT EXISTS idx_diary_diary_id ON diary (diary_id);
            """
        )
    conn.commit()


# ---------------------------------------------------------------------------
# First-launch / password management
# ---------------------------------------------------------------------------

def is_first_launch() -> bool:
    """Return True if the database has not been initialised yet."""
    if not DB_PATH.exists():
        return True
    with _connect() as conn:
        _init_schema(conn)
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'password_hash'"
        ).fetchone()
        return row is None


def setup_password(password: str) -> None:
    """Initialise the database with a new master password."""
    salt = crypto_utils.generate_salt()
    salt_b64 = base64.b64encode(salt).decode("ascii")
    pw_hash = crypto_utils.hash_password(password, salt)
    with _connect() as conn:
        _init_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('salt', ?)",
            (salt_b64,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('password_hash', ?)",
            (pw_hash,),
        )
        conn.commit()


def authenticate(password: str) -> Optional[Fernet]:
    """Verify *password* and return a ready Fernet instance, or None on failure."""
    with _connect() as conn:
        salt_row = conn.execute(
            "SELECT value FROM meta WHERE key = 'salt'"
        ).fetchone()
        hash_row = conn.execute(
            "SELECT value FROM meta WHERE key = 'password_hash'"
        ).fetchone()

    if salt_row is None or hash_row is None:
        return None

    salt_b64 = salt_row["value"]
    stored_hash = hash_row["value"]

    if not crypto_utils.verify_password(password, salt_b64, stored_hash):
        return None

    salt = base64.b64decode(salt_b64)
    return crypto_utils.make_fernet(password, salt)


# ---------------------------------------------------------------------------
# Note CRUD
# ---------------------------------------------------------------------------

def get_dates_with_notes() -> list[str]:
    """Return distinct dates that have at least one note, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT note_date FROM notes ORDER BY note_date DESC"
        ).fetchall()
    return [row["note_date"] for row in rows]


def get_notes_for_date(note_date: str, fernet: Fernet) -> list[dict]:
    """Return all notes for *note_date*, with subject/content decrypted."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, note_date, subject, content, created_at "
            "FROM notes WHERE note_date = ? ORDER BY created_at ASC",
            (note_date,),
        ).fetchall()

    result = []
    for row in rows:
        try:
            subject = crypto_utils.decrypt(fernet, row["subject"])
            content = crypto_utils.decrypt(fernet, row["content"])
        except Exception:
            subject = "<decryption error>"
            content = "<decryption error>"
        result.append(
            {
                "id": row["id"],
                "note_date": row["note_date"],
                "subject": subject,
                "content": content,
                "created_at": row["created_at"],
            }
        )
    return result


def add_note(subject: str, content: str, fernet: Fernet) -> int:
    """Encrypt and insert a new note for today. Returns the new row id."""
    today = date.today().isoformat()
    enc_subject = crypto_utils.encrypt(fernet, subject)
    enc_content = crypto_utils.encrypt(fernet, content)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO notes (note_date, subject, content) VALUES (?, ?, ?)",
            (today, enc_subject, enc_content),
        )
        conn.commit()
        return cur.lastrowid


def update_note(note_id: int, subject: str, content: str, fernet: Fernet) -> None:
    """Encrypt and update subject/content for the note with *note_id*."""
    enc_subject = crypto_utils.encrypt(fernet, subject)
    enc_content = crypto_utils.encrypt(fernet, content)
    with _connect() as conn:
        conn.execute(
            "UPDATE notes SET subject = ?, content = ? WHERE id = ?",
            (enc_subject, enc_content, note_id),
        )
        conn.commit()


def delete_note(note_id: int) -> None:
    """Permanently remove the note with *note_id*."""
    with _connect() as conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Alarm CRUD
# ---------------------------------------------------------------------------

def get_due_alarms() -> list[dict]:
    """Return alarms whose alarm_dt has passed, oldest first.

    alarm_dt is stored unencrypted so this query needs no fernet.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, subject, alarm_dt FROM alarms WHERE alarm_dt <= ? ORDER BY alarm_dt ASC",
            (now,),
        ).fetchall()
    return [{"id": row["id"], "subject": row["subject"], "alarm_dt": row["alarm_dt"]} for row in rows]


def get_all_alarms(fernet: Fernet) -> list[dict]:
    """Return all alarms ordered by alarm_dt ASC. Subject is plaintext; note is decrypted."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, subject, note, alarm_dt, created_at FROM alarms ORDER BY alarm_dt ASC"
        ).fetchall()

    result = []
    for row in rows:
        try:
            note = crypto_utils.decrypt(fernet, row["note"])
        except Exception:
            note = "<decryption error>"
        result.append({
            "id":         row["id"],
            "subject":    row["subject"],
            "note":       note,
            "alarm_dt":   row["alarm_dt"],
            "created_at": row["created_at"],
        })
    return result


def get_alarm_by_id(alarm_id: int, fernet: Optional[Fernet]) -> dict:
    """Return a single alarm by id. Subject is plaintext; note is decrypted if fernet given."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, subject, note, alarm_dt FROM alarms WHERE id = ?",
            (alarm_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"Alarm {alarm_id} not found")
    note = ""
    if fernet is not None:
        try:
            note = crypto_utils.decrypt(fernet, row["note"])
        except Exception:
            note = "<decryption error>"
    return {"id": row["id"], "subject": row["subject"], "note": note, "alarm_dt": row["alarm_dt"]}


def add_alarm(subject: str, note: str, alarm_dt: str, fernet: Fernet) -> int:
    """Insert a new alarm. Subject is stored plaintext; note is encrypted. Returns the new row id."""
    enc_note = crypto_utils.encrypt(fernet, note)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO alarms (subject, note, alarm_dt) VALUES (?, ?, ?)",
            (subject, enc_note, alarm_dt),
        )
        conn.commit()
        return cur.lastrowid


def update_alarm(alarm_id: int, subject: str, note: str, alarm_dt: str, fernet: Fernet) -> None:
    """Update an existing alarm. Subject is stored plaintext; note is encrypted."""
    enc_note = crypto_utils.encrypt(fernet, note)
    with _connect() as conn:
        conn.execute(
            "UPDATE alarms SET subject = ?, note = ?, alarm_dt = ? WHERE id = ?",
            (subject, enc_note, alarm_dt, alarm_id),
        )
        conn.commit()


def snooze_alarm(alarm_id: int, minutes: int) -> None:
    """Push alarm_dt forward by *minutes* from now."""
    new_dt = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        conn.execute(
            "UPDATE alarms SET alarm_dt = ? WHERE id = ?",
            (new_dt, alarm_id),
        )
        conn.commit()


def delete_alarm(alarm_id: int) -> None:
    """Permanently remove an alarm."""
    with _connect() as conn:
        conn.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Diary CRUD
# ---------------------------------------------------------------------------

def get_diary_dates(diary_id: int) -> list[str]:
    """Return all dates that have a diary entry for *diary_id*, oldest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT entry_date FROM diary WHERE diary_id = ? ORDER BY entry_date ASC",
            (diary_id,),
        ).fetchall()
    return [row["entry_date"] for row in rows]


def get_diary_entry(entry_date: str, diary_id: int, fernet: Fernet) -> str:
    """Return the decrypted diary content for *entry_date* in *diary_id*, or '' if none."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT content FROM diary WHERE entry_date = ? AND diary_id = ?",
            (entry_date, diary_id),
        ).fetchone()
    if row is None:
        return ""
    try:
        return crypto_utils.decrypt(fernet, row["content"])
    except Exception:
        return "<decryption error>"


def search_all(query: str, fernet: Fernet) -> list[dict]:
    """Search notes, alarms and diary entries for *query* (case-insensitive).

    Returns a list of dicts.  Each dict always has:
      type        'note' | 'alarm' | 'diary'
    Notes also carry:   id, note_date, subject, content, created_at
    Alarms also carry:  id, subject, note, alarm_dt
    Diary entries carry: entry_date, content
    """
    q = query.lower()
    results: list[dict] = []

    # ── Notes ─────────────────────────────────────────────────────────
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, note_date, subject, content, created_at "
            "FROM notes ORDER BY note_date DESC, created_at ASC"
        ).fetchall()
    for row in rows:
        try:
            subject = crypto_utils.decrypt(fernet, row["subject"])
            content = crypto_utils.decrypt(fernet, row["content"])
        except Exception:
            continue
        if q in subject.lower() or q in content.lower():
            results.append({
                "type":       "note",
                "id":         row["id"],
                "note_date":  row["note_date"],
                "subject":    subject,
                "content":    content,
                "created_at": row["created_at"],
            })

    # ── Alarms ────────────────────────────────────────────────────────
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, subject, note, alarm_dt FROM alarms ORDER BY alarm_dt ASC"
        ).fetchall()
    for row in rows:
        try:
            note = crypto_utils.decrypt(fernet, row["note"])
        except Exception:
            note = ""
        subject = row["subject"]  # stored plaintext
        if q in subject.lower() or q in note.lower():
            results.append({
                "type":     "alarm",
                "id":       row["id"],
                "subject":  subject,
                "note":     note,
                "alarm_dt": row["alarm_dt"],
            })

    # ── Diary ─────────────────────────────────────────────────────────
    with _connect() as conn:
        rows = conn.execute(
            "SELECT entry_date, diary_id, content FROM diary ORDER BY entry_date DESC"
        ).fetchall()
    for row in rows:
        try:
            content = crypto_utils.decrypt(fernet, row["content"])
        except Exception:
            continue
        if q in content.lower():
            results.append({
                "type":       "diary",
                "diary_id":   row["diary_id"],
                "entry_date": row["entry_date"],
                "content":    content,
            })

    return results


def get_all_diary_entries(fernet: Fernet, diary_id: int) -> list[dict]:
    """Return all entries for *diary_id* with content decrypted, oldest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT entry_date, content, updated_at FROM diary "
            "WHERE diary_id = ? ORDER BY entry_date ASC",
            (diary_id,),
        ).fetchall()
    result = []
    for row in rows:
        try:
            content = crypto_utils.decrypt(fernet, row["content"])
        except Exception:
            content = ""
        if content:
            result.append({
                "entry_date": row["entry_date"],
                "content": content,
                "updated_at": row["updated_at"],
            })
    return result


def get_all_notes(fernet: Fernet) -> list[dict]:
    """Return all notes with subject/content decrypted, ordered by date then time."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, note_date, subject, content, created_at "
            "FROM notes ORDER BY note_date ASC, created_at ASC"
        ).fetchall()
    result = []
    for row in rows:
        try:
            subject = crypto_utils.decrypt(fernet, row["subject"])
            content = crypto_utils.decrypt(fernet, row["content"])
        except Exception:
            continue
        result.append({
            "id":         row["id"],
            "note_date":  row["note_date"],
            "subject":    subject,
            "content":    content,
            "created_at": row["created_at"],
        })
    return result


# ---------------------------------------------------------------------------
# Diaries management (multi-diary)
# ---------------------------------------------------------------------------

def ensure_default_diary(default_name: str, fernet: Fernet) -> int:
    """Ensure the default diary (id=1) exists with an encrypted name. Returns 1."""
    with _connect() as conn:
        row = conn.execute("SELECT id, name FROM diaries WHERE id = 1").fetchone()
        if row is None:
            enc_name = crypto_utils.encrypt(fernet, default_name)
            conn.execute(
                "INSERT OR IGNORE INTO diaries (id, name) VALUES (1, ?)", (enc_name,)
            )
            conn.commit()
        elif row["name"] == "":
            # Migration sentinel — fill in the real name.
            enc_name = crypto_utils.encrypt(fernet, default_name)
            conn.execute("UPDATE diaries SET name = ? WHERE id = 1", (enc_name,))
            conn.commit()
    return 1


def get_diaries(fernet: Fernet) -> list[dict]:
    """Return all diaries with decrypted names, ordered by id ASC."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name FROM diaries ORDER BY id ASC"
        ).fetchall()
    result = []
    for row in rows:
        try:
            name = crypto_utils.decrypt(fernet, row["name"])
        except Exception:
            name = f"Diary {row['id']}"
        result.append({"id": row["id"], "name": name})
    return result


def add_diary(name: str, fernet: Fernet) -> int:
    """Create a new diary with the given encrypted name. Returns the new diary id."""
    enc_name = crypto_utils.encrypt(fernet, name)
    with _connect() as conn:
        cur = conn.execute("INSERT INTO diaries (name) VALUES (?)", (enc_name,))
        conn.commit()
        return cur.lastrowid


def rename_diary(diary_id: int, name: str, fernet: Fernet) -> None:
    """Rename a diary."""
    enc_name = crypto_utils.encrypt(fernet, name)
    with _connect() as conn:
        conn.execute("UPDATE diaries SET name = ? WHERE id = ?", (enc_name, diary_id))
        conn.commit()


def delete_diary(diary_id: int) -> None:
    """Delete a diary and all its entries."""
    with _connect() as conn:
        conn.execute("DELETE FROM diary WHERE diary_id = ?", (diary_id,))
        conn.execute("DELETE FROM diaries WHERE id = ?", (diary_id,))
        conn.commit()


def count_diary_entries(diary_id: int) -> int:
    """Return the number of entries in a diary."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM diary WHERE diary_id = ?", (diary_id,)
        ).fetchone()
    return row["n"] if row else 0


def save_diary_entry(entry_date: str, content: str, diary_id: int, fernet: Fernet) -> None:
    """Upsert a diary entry for *diary_id*. Deletes the row when *content* is empty."""
    if not content:
        with _connect() as conn:
            conn.execute(
                "DELETE FROM diary WHERE entry_date = ? AND diary_id = ?",
                (entry_date, diary_id),
            )
            conn.commit()
        return
    enc_content = crypto_utils.encrypt(fernet, content)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO diary (entry_date, diary_id, content, updated_at) "
            "VALUES (?, ?, ?, datetime('now')) "
            "ON CONFLICT(entry_date, diary_id) DO UPDATE SET "
            "  content    = excluded.content, "
            "  updated_at = excluded.updated_at",
            (entry_date, diary_id, enc_content),
        )
        conn.commit()
