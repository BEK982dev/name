import sqlite3
import os
from datetime import datetime

DB_PATH = "bot_database.db"


class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    file_size TEXT,
                    format_id TEXT,
                    telegram_file_id TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            conn.commit()

    def save_user(self, user_id: int, username: str):
        with self._get_conn() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO users (user_id, username)
                VALUES (?, ?)
            ''', (user_id, username))
            conn.commit()

    def get_user_files(self, user_id: int) -> list:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM files WHERE user_id = ?
                ORDER BY created_at DESC LIMIT 20
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def save_file(self, user_id: int, title: str, url: str,
                  quality: str, file_size: str, format_id: str) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute('''
                INSERT INTO files (user_id, title, url, quality, file_size, format_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, title, url, quality, file_size, format_id))
            conn.commit()
            return cursor.lastrowid

    def update_file_telegram_id(self, file_id: int, telegram_file_id: str):
        with self._get_conn() as conn:
            conn.execute('''
                UPDATE files SET telegram_file_id = ? WHERE id = ?
            ''', (telegram_file_id, file_id))
            conn.commit()

    def get_file_by_id(self, file_id: int, user_id: int) -> dict | None:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM files WHERE id = ? AND user_id = ?
            ''', (file_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_file(self, file_id: int, user_id: int):
        with self._get_conn() as conn:
            conn.execute('''
                DELETE FROM files WHERE id = ? AND user_id = ?
            ''', (file_id, user_id))
            conn.commit()

    def clear_user_files(self, user_id: int):
        with self._get_conn() as conn:
            conn.execute('DELETE FROM files WHERE user_id = ?', (user_id,))
            conn.commit()
