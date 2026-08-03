"""
足迹 - 数据库模型和接口
支持多种数据库：SQLite（本地）、PostgreSQL、MySQL
支持多种云存储：阿里云OSS、腾讯云COS、七牛云、AWS S3、Google Cloud、Azure Blob
"""

import os
import json
import threading
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

RUNTIME_CONFIG_FILE = os.environ.get(
    'FOOTPRINT_CONFIG_FILE',
    os.path.join(os.path.dirname(__file__), 'runtime_config.json')
)

# ========== 数据库配置 ==========
DB_CONFIG = {
    'type': os.environ.get('DB_TYPE', 'sqlite'),  # sqlite, postgres, json
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'name': os.environ.get('DB_NAME', os.path.join(os.path.dirname(__file__), 'footprint.db')),
    'user': os.environ.get('DB_USER', ''),
    'password': os.environ.get('DB_PASSWORD', ''),
}


# ========== 记录存储 ==========
class RecordStore:
    """记录存储接口，供 Flask API 使用。"""

    def list(self, mode: str = None, owner_id: str = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get(self, record_id: str, owner_id: str = None) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def create(self, record: Dict[str, Any], owner_id: str = None) -> Dict[str, Any]:
        raise NotImplementedError

    def update(self, record_id: str, record: Dict[str, Any], owner_id: str = None) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def delete(self, record_id: str, owner_id: str = None) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    # ---- Expenses ----
    def list_expenses(self, record_id: str = None, owner_id: str = None) -> list:
        raise NotImplementedError

    def create_expense(self, expense: dict, owner_id: str = None) -> dict:
        raise NotImplementedError

    def update_expense(self, expense_id: str, expense: dict, owner_id: str = None) -> Optional[dict]:
        raise NotImplementedError

    def delete_expense(self, expense_id: str, owner_id: str = None) -> Optional[dict]:
        raise NotImplementedError

    def get_expense_stats(self, owner_id: str = None) -> dict:
        raise NotImplementedError

    # ---- Users ----
    def create_user(self, user_id: str, username: str, password_hash: str, expires_at: str = None) -> dict:
        raise NotImplementedError

    def get_user_by_username(self, username: str) -> Optional[dict]:
        raise NotImplementedError

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        raise NotImplementedError

    def claim_orphan_data(self, user_id: str) -> None:
        """把无主（旧版本导入）的数据归给指定用户，仅在数据尚无属主时执行。"""
        raise NotImplementedError


class JsonRecordStore(RecordStore):
    """向后兼容的 JSON 文件存储。"""

    def __init__(self, metadata_file: str):
        self.metadata_file = metadata_file
        base_dir = os.path.dirname(metadata_file)
        os.makedirs(base_dir, exist_ok=True)
        self.users_file = os.path.join(base_dir, 'users.json')
        self.expenses_file = os.path.join(base_dir, 'expenses.json')

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save(self, records: List[Dict[str, Any]]):
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def _load_users(self) -> list:
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_users(self, users: list):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

    def _load_expenses(self) -> list:
        if os.path.exists(self.expenses_file):
            with open(self.expenses_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_expenses(self, expenses: list):
        with open(self.expenses_file, 'w', encoding='utf-8') as f:
            json.dump(expenses, f, ensure_ascii=False, indent=2)

    def list(self, mode: str = None, owner_id: str = None) -> List[Dict[str, Any]]:
        records = self._load()
        if owner_id:
            records = [r for r in records if r.get('owner_id') == owner_id]
        if mode:
            records = [r for r in records if r.get('mode') == mode]
        return records

    def get(self, record_id: str, owner_id: str = None) -> Optional[Dict[str, Any]]:
        records = self._load()
        if owner_id:
            records = [r for r in records if r.get('owner_id') == owner_id]
        return next((r for r in records if r.get('id') == record_id), None)

    def create(self, record: Dict[str, Any], owner_id: str = None) -> Dict[str, Any]:
        record = dict(record)
        if owner_id:
            record['owner_id'] = owner_id
        records = self._load()
        records.insert(0, record)
        self._save(records)
        return record

    def update(self, record_id: str, record: Dict[str, Any], owner_id: str = None) -> Optional[Dict[str, Any]]:
        records = self._load()
        for i, existing in enumerate(records):
            if existing.get('id') == record_id and (not owner_id or existing.get('owner_id') == owner_id):
                record = dict(record)
                if owner_id:
                    record['owner_id'] = owner_id
                records[i] = record
                self._save(records)
                return record
        return None

    def delete(self, record_id: str, owner_id: str = None) -> Optional[Dict[str, Any]]:
        records = self._load()
        record = next(
            (r for r in records if r.get('id') == record_id and (not owner_id or r.get('owner_id') == owner_id)),
            None
        )
        if not record:
            return None
        self._save([r for r in records if r.get('id') != record_id])
        return record

    # ---- Expenses ----
    def list_expenses(self, record_id: str = None, owner_id: str = None) -> list:
        expenses = self._load_expenses()
        if owner_id:
            expenses = [e for e in expenses if e.get('owner_id') == owner_id]
        if record_id:
            expenses = [e for e in expenses if e.get('record_id') == record_id]
        return expenses

    def create_expense(self, expense: dict, owner_id: str = None) -> dict:
        expense = dict(expense)
        if owner_id:
            expense['owner_id'] = owner_id
        expenses = self._load_expenses()
        expenses.insert(0, expense)
        self._save_expenses(expenses)
        return expense

    def update_expense(self, expense_id: str, expense: dict, owner_id: str = None) -> Optional[dict]:
        expenses = self._load_expenses()
        for i, existing in enumerate(expenses):
            if existing.get('id') == expense_id and (not owner_id or existing.get('owner_id') == owner_id):
                expense = dict(expense)
                if owner_id:
                    expense['owner_id'] = owner_id
                expenses[i] = expense
                self._save_expenses(expenses)
                return expense
        return None

    def delete_expense(self, expense_id: str, owner_id: str = None) -> Optional[dict]:
        expenses = self._load_expenses()
        expense = next(
            (e for e in expenses if e.get('id') == expense_id and (not owner_id or e.get('owner_id') == owner_id)),
            None
        )
        if not expense:
            return None
        self._save_expenses([e for e in expenses if e.get('id') != expense_id])
        return expense

    def get_expense_stats(self, owner_id: str = None) -> dict:
        expenses = self._load_expenses()
        if owner_id:
            expenses = [e for e in expenses if e.get('owner_id') == owner_id]
        by_category = {}
        by_mode = {}
        total_amount = 0.0
        for e in expenses:
            amount = float(e.get('amount') or 0)
            total_amount += amount
            cat = e.get('category', '其他')
            by_category[cat] = by_category.get(cat, 0) + amount
            mode = e.get('mode', 'travel')
            by_mode[mode] = by_mode.get(mode, 0) + amount
        return {
            'total_count': len(expenses),
            'total_amount': total_amount,
            'by_category': [{'category': k, 'count': v, 'amount': v} for k, v in by_category.items()],
            'by_mode': [{'mode': k, 'count': v, 'amount': v} for k, v in by_mode.items()],
        }

    # ---- Users ----
    def create_user(self, user_id: str, username: str, password_hash: str, expires_at: str = None) -> dict:
        created_at = datetime.now().isoformat()
        user = {
            'id': user_id,
            'username': username,
            'password_hash': password_hash,
            'created_at': created_at,
            'expires_at': expires_at,
        }
        users = self._load_users()
        if not users:
            self.claim_orphan_data(user_id)
        users.append(user)
        self._save_users(users)
        return user

    def get_user_by_username(self, username: str) -> Optional[dict]:
        return next((u for u in self._load_users() if u.get('username') == username), None)

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        return next((u for u in self._load_users() if u.get('id') == user_id), None)

    def claim_orphan_data(self, user_id: str) -> None:
        """把无主（旧版本导入）的记录与费用归给第一个注册用户。"""
        records = self._load()
        changed = False
        for r in records:
            if not r.get('owner_id'):
                r['owner_id'] = user_id
                changed = True
        if changed:
            self._save(records)
        expenses = self._load_expenses()
        changed = False
        for e in expenses:
            if not e.get('owner_id'):
                e['owner_id'] = user_id
                changed = True
        if changed:
            self._save_expenses(expenses)


class SQLiteRecordStore(RecordStore):
    """SQLite 记录存储，归一化模式，支持用户和费用管理。"""

    def __init__(self, db_path: str, metadata_file: str = None):
        import sqlite3
        self.sqlite3 = sqlite3
        self.db_path = db_path
        self.metadata_file = metadata_file
        self._local = threading.local()
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_tables()
        self._migrate_json_once()

    def _connect(self):
        """Get or create a connection for the current thread."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = self.sqlite3.connect(self.db_path)
            conn.row_factory = self.sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def close(self):
        """Close the current thread's connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    # ---- Migration from old payload schema ----
    def _migrate_from_payload(self):
        """Migrate from old payload-based schema to normalized schema."""
        if not os.path.exists(self.db_path):
            return
        conn = None
        try:
            conn = self.sqlite3.connect(self.db_path, isolation_level=None)
            conn.row_factory = self.sqlite3.Row
            columns = [row[1] for row in conn.execute("PRAGMA table_info(records)").fetchall()]
            if 'payload' not in columns:
                conn.close()
                return
            rows = conn.execute("SELECT id, payload FROM records").fetchall()
            if not rows:
                conn.execute("DROP TABLE IF EXISTS records")
                conn.close()
                return
            records_data = []
            for row in rows:
                payload = json.loads(row[1])
                records_data.append((
                    row[0],
                    payload.get('mode', 'travel'),
                    payload.get('title', ''),
                    payload.get('description', ''),
                    payload.get('location'),
                    payload.get('latitude'),
                    payload.get('longitude'),
                    payload.get('date'),
                    payload.get('rating'),
                    payload.get('price'),
                    json.dumps(payload.get('tags', []), ensure_ascii=False),
                    json.dumps(payload.get('metadata', {}), ensure_ascii=False),
                    json.dumps(payload.get('images', []), ensure_ascii=False),
                    payload.get('createdAt') or payload.get('created_at') or datetime.now().isoformat(),
                    payload.get('updatedAt') or payload.get('updated_at')
                ))
            conn.execute("BEGIN TRANSACTION")
            conn.execute("DROP TABLE records")
            conn.execute("""
                CREATE TABLE records (
                    id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    location TEXT,
                    latitude REAL,
                    longitude REAL,
                    date TEXT,
                    rating INTEGER,
                    price REAL,
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    images TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            conn.executemany("""
                INSERT INTO records (id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records_data)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_mode ON records(mode)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_date ON records(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_location ON records(latitude, longitude)")
            conn.commit()
        except Exception:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn:
                conn.close()

    # ---- Table initialization ----
    def _ensure_column(self, conn, table: str, column: str, ddl: str):
        """幂等添加列（旧库迁移用）。"""
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def _init_tables(self):
        self._migrate_from_payload()
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    location TEXT,
                    latitude REAL,
                    longitude REAL,
                    date TEXT,
                    rating INTEGER,
                    price REAL,
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    images TEXT DEFAULT '[]',
                    owner_id TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_records_mode ON records(mode);
                CREATE INDEX IF NOT EXISTS idx_records_date ON records(date);
                CREATE INDEX IF NOT EXISTS idx_records_location ON records(latitude, longitude);
            """)
        self._init_users_table()
        self._init_expenses_table()

    def _init_users_table(self):
        """Create users table for authentication."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    expires_at TEXT,
                    created_at TEXT NOT NULL
                )
            """)

    def _init_expenses_table(self):
        """Create expenses table."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id TEXT PRIMARY KEY,
                    record_id TEXT,
                    mode TEXT DEFAULT 'travel',
                    category TEXT DEFAULT '其他',
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'CNY',
                    description TEXT DEFAULT '',
                    date TEXT,
                    owner_id TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE SET NULL
                )
            """)
            # 旧库迁移：为已存在的表补充新增列
            self._ensure_column(conn, 'records', 'owner_id', "owner_id TEXT DEFAULT ''")
            self._ensure_column(conn, 'users', 'expires_at', "expires_at TEXT")
            self._ensure_column(conn, 'expenses', 'owner_id', "owner_id TEXT DEFAULT ''")

    def _migrate_json_once(self):
        if not self.metadata_file or not os.path.exists(self.metadata_file):
            return
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            if count:
                return
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        for record in records:
            if record.get('id'):
                self.create(record)

    # ---- Record helpers ----
    def _row_to_record(self, row) -> Dict[str, Any]:
        return {
            'id': row['id'],
            'mode': row['mode'],
            'title': row['title'],
            'description': row['description'] or '',
            'location': row['location'],
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            'date': row['date'],
            'rating': row['rating'],
            'price': row['price'],
            'tags': json.loads(row['tags']) if row['tags'] else [],
            'metadata': json.loads(row['metadata']) if row['metadata'] else {},
            'images': json.loads(row['images']) if row['images'] else [],
            'createdAt': row['created_at'],
            'updatedAt': row['updated_at'],
        }

    def _upsert(self, record: Dict[str, Any], owner_id: str = None) -> Dict[str, Any]:
        tags = record.get('tags', [])
        metadata = record.get('metadata', {})
        images = record.get('images', [])
        created_at = record.get('createdAt') or record.get('created_at') or datetime.now().isoformat()
        updated_at = record.get('updatedAt') or record.get('updated_at') or datetime.now().isoformat()
        owner = owner_id or record.get('owner_id') or ''
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO records (id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, owner_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    mode=excluded.mode,
                    title=excluded.title,
                    description=excluded.description,
                    location=excluded.location,
                    latitude=excluded.latitude,
                    longitude=excluded.longitude,
                    date=excluded.date,
                    rating=excluded.rating,
                    price=excluded.price,
                    tags=excluded.tags,
                    metadata=excluded.metadata,
                    images=excluded.images,
                    updated_at=excluded.updated_at
            """, (
                record['id'],
                record.get('mode', 'travel'),
                record.get('title', ''),
                record.get('description', ''),
                record.get('location'),
                record.get('latitude'),
                record.get('longitude'),
                record.get('date'),
                record.get('rating'),
                record.get('price'),
                json.dumps(tags, ensure_ascii=False),
                json.dumps(metadata, ensure_ascii=False),
                json.dumps(images, ensure_ascii=False),
                owner,
                created_at,
                updated_at
            ))
        return record

    # ---- CRUD ----
    def list(self, mode: str = None, owner_id: str = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if mode:
                rows = conn.execute("SELECT * FROM records WHERE mode = ? AND (owner_id = ? OR owner_id = '') ORDER BY date DESC, created_at DESC", (mode, owner_id or '')).fetchall()
            else:
                rows = conn.execute("SELECT * FROM records WHERE owner_id = ? OR owner_id = '' ORDER BY date DESC, created_at DESC", (owner_id or '',)).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get(self, record_id: str, owner_id: str = None) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM records WHERE id = ? AND (owner_id = ? OR owner_id = '')", (record_id, owner_id or '')).fetchone()
        return self._row_to_record(row) if row else None

    def create(self, record: Dict[str, Any], owner_id: str = None) -> Dict[str, Any]:
        return self._upsert(record, owner_id)

    def update(self, record_id: str, record: Dict[str, Any], owner_id: str = None) -> Optional[Dict[str, Any]]:
        if not self.get(record_id, owner_id):
            return None
        return self._upsert(record, owner_id)

    def delete(self, record_id: str, owner_id: str = None) -> Optional[Dict[str, Any]]:
        record = self.get(record_id, owner_id)
        if not record:
            return None
        with self._connect() as conn:
            conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        return record

    # ---- Expenses ----
    def list_expenses(self, record_id: str = None, owner_id: str = None) -> list:
        with self._connect() as conn:
            if record_id:
                rows = conn.execute(
                    "SELECT * FROM expenses WHERE record_id = ? AND (owner_id = ? OR owner_id = '') ORDER BY date DESC, created_at DESC",
                    (record_id, owner_id or '')
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM expenses WHERE owner_id = ? OR owner_id = '' ORDER BY date DESC, created_at DESC",
                    (owner_id or '',)
                ).fetchall()
        return [dict(row) for row in rows]

    def create_expense(self, expense: dict, owner_id: str = None) -> dict:
        expense.setdefault('id', str(uuid.uuid4()))
        expense.setdefault('created_at', datetime.now().isoformat())
        owner = owner_id or expense.get('owner_id') or ''
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO expenses (id, record_id, mode, category, amount, currency, description, date, owner_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                expense['id'],
                expense.get('record_id'),
                expense.get('mode', 'travel'),
                expense.get('category', '其他'),
                expense['amount'],
                expense.get('currency', 'CNY'),
                expense.get('description', ''),
                expense.get('date'),
                owner,
                expense['created_at']
            ))
        return expense

    def update_expense(self, expense_id: str, expense: dict, owner_id: str = None) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE id = ? AND (owner_id = ? OR owner_id = '')", (expense_id, owner_id or '')).fetchone()
            if not row:
                return None
            conn.execute("""
                UPDATE expenses SET record_id=?, mode=?, category=?, amount=?, currency=?, description=?, date=?
                WHERE id=?
            """, (
                expense.get('record_id'),
                expense.get('mode', 'travel'),
                expense.get('category', '其他'),
                expense['amount'],
                expense.get('currency', 'CNY'),
                expense.get('description', ''),
                expense.get('date'),
                expense_id
            ))
        return self._get_expense_by_id(expense_id, owner_id)

    def delete_expense(self, expense_id: str, owner_id: str = None) -> Optional[dict]:
        expense = self._get_expense_by_id(expense_id, owner_id)
        if not expense:
            return None
        with self._connect() as conn:
            conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return expense

    def _get_expense_by_id(self, expense_id: str, owner_id: str = None) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE id = ? AND (owner_id = ? OR owner_id = '')", (expense_id, owner_id or '')).fetchone()
        return dict(row) if row else None

    def get_expense_stats(self, owner_id: str = None) -> dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM expenses WHERE owner_id = ? OR owner_id = ''", (owner_id or '',)).fetchone()
            by_category = conn.execute(
                "SELECT category, COUNT(*), COALESCE(SUM(amount), 0) FROM expenses WHERE owner_id = ? OR owner_id = '' GROUP BY category ORDER BY SUM(amount) DESC",
                (owner_id or '',)
            ).fetchall()
            by_mode = conn.execute(
                "SELECT mode, COUNT(*), COALESCE(SUM(amount), 0) FROM expenses WHERE owner_id = ? OR owner_id = '' GROUP BY mode ORDER BY SUM(amount) DESC",
                (owner_id or '',)
            ).fetchall()
        return {
            'total_count': total[0],
            'total_amount': total[1],
            'by_category': [{'category': row[0], 'count': row[1], 'amount': row[2]} for row in by_category],
            'by_mode': [{'mode': row[0], 'count': row[1], 'amount': row[2]} for row in by_mode],
        }

    # ---- Users ----
    def create_user(self, user_id: str, username: str, password_hash: str, expires_at: str = None) -> dict:
        created_at = datetime.now().isoformat()
        with self._connect() as conn:
            # 第一个注册用户自动认领旧版本遗留的无主数据
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            conn.execute("""
                INSERT INTO users (id, username, password_hash, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, password_hash, expires_at, created_at))
            if count == 0:
                conn.execute("UPDATE records SET owner_id = ? WHERE owner_id = '' OR owner_id IS NULL", (user_id,))
                conn.execute("UPDATE expenses SET owner_id = ? WHERE owner_id = '' OR owner_id IS NULL", (user_id,))
        return {'id': user_id, 'username': username, 'password_hash': password_hash, 'expires_at': expires_at, 'created_at': created_at}

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def claim_orphan_data(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE records SET owner_id = ? WHERE owner_id = '' OR owner_id IS NULL", (user_id,))
            conn.execute("UPDATE expenses SET owner_id = ? WHERE owner_id = '' OR owner_id IS NULL", (user_id,))


class PostgresRecordStore(RecordStore):
    """PostgreSQL 记录存储，归一化模式，支持用户和费用管理。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._init_tables()

    def _connect(self):
        import psycopg2
        return psycopg2.connect(
            host=self.config['host'],
            port=self.config['port'],
            database=self.config['name'],
            user=self.config['user'],
            password=self.config['password']
        )

    # ---- Migration from old payload schema ----
    def _migrate_from_payload(self):
        """Migrate from old payload-based schema to normalized schema."""
        conn = None
        try:
            conn = self._connect()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
                    ('records', 'payload')
                )
                if not cursor.fetchone():
                    conn.close()
                    return
                cursor.execute("SELECT id, payload FROM records")
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute("DROP TABLE IF EXISTS records")
                    conn.commit()
                    conn.close()
                    return
                from psycopg2.extras import Json
                records_data = []
                for row in rows:
                    payload = row[1] if isinstance(row[1], dict) else json.loads(row[1])
                    records_data.append((
                        row[0],
                        payload.get('mode', 'travel'),
                        payload.get('title', ''),
                        payload.get('description', ''),
                        payload.get('location'),
                        payload.get('latitude'),
                        payload.get('longitude'),
                        payload.get('date'),
                        payload.get('rating'),
                        payload.get('price'),
                        Json(payload.get('tags', [])),
                        Json(payload.get('metadata', {})),
                        Json(payload.get('images', [])),
                        payload.get('createdAt') or payload.get('created_at') or datetime.now().isoformat(),
                        payload.get('updatedAt') or payload.get('updated_at')
                    ))
                cursor.execute("DROP TABLE records")
                cursor.execute("""
                    CREATE TABLE records (
                        id TEXT PRIMARY KEY,
                        mode TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        location TEXT,
                        latitude DOUBLE PRECISION,
                        longitude DOUBLE PRECISION,
                        date DATE,
                        rating INTEGER,
                        price REAL,
                        tags JSONB DEFAULT '[]',
                        metadata JSONB DEFAULT '{}',
                        images JSONB DEFAULT '[]',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                """)
                cursor.executemany("""
                    INSERT INTO records (id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, records_data)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_mode ON records(mode)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_date ON records(date)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_location ON records(latitude, longitude)")
                conn.commit()
        except Exception:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn:
                conn.close()

    # ---- Table initialization ----
    def _init_tables(self):
        self._migrate_from_payload()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS records (
                        id TEXT PRIMARY KEY,
                        mode TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        location TEXT,
                        latitude DOUBLE PRECISION,
                        longitude DOUBLE PRECISION,
                        date DATE,
                        rating INTEGER,
                        price REAL,
                        tags JSONB DEFAULT '[]',
                        metadata JSONB DEFAULT '{}',
                        images JSONB DEFAULT '[]',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_records_mode ON records(mode);
                    CREATE INDEX IF NOT EXISTS idx_records_date ON records(date);
                    CREATE INDEX IF NOT EXISTS idx_records_location ON records(latitude, longitude);
                """)
            conn.commit()
        self._init_users_table()
        self._init_expenses_table()

    def _init_users_table(self):
        """Create users table for authentication."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()

    def _init_expenses_table(self):
        """Create expenses table."""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS expenses (
                        id TEXT PRIMARY KEY,
                        record_id TEXT,
                        mode TEXT DEFAULT 'travel',
                        category TEXT DEFAULT '其他',
                        amount REAL NOT NULL,
                        currency TEXT DEFAULT 'CNY',
                        description TEXT DEFAULT '',
                        date DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE SET NULL
                    )
                """)
            conn.commit()

    # ---- Record helpers ----
    def _row_to_record(self, row) -> Dict[str, Any]:
        tags = row[10]
        metadata = row[11]
        images = row[12]
        return {
            'id': row[0],
            'mode': row[1],
            'title': row[2],
            'description': row[3] or '',
            'location': row[4],
            'latitude': row[5],
            'longitude': row[6],
            'date': str(row[7]) if row[7] else None,
            'rating': row[8],
            'price': row[9],
            'tags': tags if isinstance(tags, list) else json.loads(tags),
            'metadata': metadata if isinstance(metadata, dict) else json.loads(metadata),
            'images': images if isinstance(images, list) else json.loads(images),
            'createdAt': row[13].isoformat() if hasattr(row[13], 'isoformat') else str(row[13]),
            'updatedAt': row[14].isoformat() if row[14] and hasattr(row[14], 'isoformat') else str(row[14]) if row[14] else None,
        }

    def _upsert(self, record: Dict[str, Any], owner_id: str = None) -> Dict[str, Any]:
        from psycopg2.extras import Json
        tags = record.get('tags', [])
        metadata = record.get('metadata', {})
        images = record.get('images', [])
        created_at = record.get('createdAt') or record.get('created_at') or datetime.now().isoformat()
        updated_at = record.get('updatedAt') or record.get('updated_at') or datetime.now().isoformat()
        owner = owner_id or record.get('owner_id') or ''
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO records (id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, owner_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(id) DO UPDATE SET
                        mode=EXCLUDED.mode,
                        title=EXCLUDED.title,
                        description=EXCLUDED.description,
                        location=EXCLUDED.location,
                        latitude=EXCLUDED.latitude,
                        longitude=EXCLUDED.longitude,
                        date=EXCLUDED.date,
                        rating=EXCLUDED.rating,
                        price=EXCLUDED.price,
                        tags=EXCLUDED.tags,
                        metadata=EXCLUDED.metadata,
                        images=EXCLUDED.images,
                        updated_at=EXCLUDED.updated_at
                """, (
                    record['id'],
                    record.get('mode', 'travel'),
                    record.get('title', ''),
                    record.get('description', ''),
                    record.get('location'),
                    record.get('latitude'),
                    record.get('longitude'),
                    record.get('date'),
                    record.get('rating'),
                    record.get('price'),
                    Json(tags),
                    Json(metadata),
                    Json(images),
                    owner,
                    created_at,
                    updated_at
                ))
            conn.commit()
        return record

    # ---- CRUD ----
    def list(self, mode: str = None, owner_id: str = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                if mode:
                    cursor.execute(
                        "SELECT id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, owner_id, created_at, updated_at FROM records WHERE mode = %s AND (owner_id = %s OR owner_id = '') ORDER BY date DESC, created_at DESC",
                        (mode, owner_id or '')
                    )
                else:
                    cursor.execute(
                        "SELECT id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, owner_id, created_at, updated_at FROM records WHERE owner_id = %s OR owner_id = '' ORDER BY date DESC, created_at DESC",
                        (owner_id or '',)
                    )
                rows = cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    def get(self, record_id: str, owner_id: str = None) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, owner_id, created_at, updated_at FROM records WHERE id = %s AND (owner_id = %s OR owner_id = '')",
                    (record_id, owner_id or '')
                )
                row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def create(self, record: Dict[str, Any], owner_id: str = None) -> Dict[str, Any]:
        return self._upsert(record, owner_id)

    def update(self, record_id: str, record: Dict[str, Any], owner_id: str = None) -> Optional[Dict[str, Any]]:
        if not self.get(record_id, owner_id):
            return None
        return self._upsert(record, owner_id)

    def delete(self, record_id: str, owner_id: str = None) -> Optional[Dict[str, Any]]:
        record = self.get(record_id, owner_id)
        if not record:
            return None
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM records WHERE id = %s", (record_id,))
            conn.commit()
        return record

    # ---- Expenses ----
    def list_expenses(self, record_id: str = None, owner_id: str = None) -> list:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                if record_id:
                    cursor.execute(
                        "SELECT id, record_id, mode, category, amount, currency, description, date, owner_id, created_at FROM expenses WHERE record_id = %s AND (owner_id = %s OR owner_id = '') ORDER BY date DESC, created_at DESC",
                        (record_id, owner_id or '')
                    )
                else:
                    cursor.execute(
                        "SELECT id, record_id, mode, category, amount, currency, description, date, owner_id, created_at FROM expenses WHERE owner_id = %s OR owner_id = '' ORDER BY date DESC, created_at DESC",
                        (owner_id or '',)
                    )
                rows = cursor.fetchall()
        return [{'id': r[0], 'record_id': r[1], 'mode': r[2], 'category': r[3], 'amount': float(r[4]), 'currency': r[5], 'description': r[6], 'date': str(r[7]) if r[7] else None, 'owner_id': r[8], 'created_at': r[9].isoformat() if hasattr(r[9], 'isoformat') else str(r[9])} for r in rows]

    def create_expense(self, expense: dict, owner_id: str = None) -> dict:
        expense.setdefault('id', str(uuid.uuid4()))
        expense.setdefault('created_at', datetime.now().isoformat())
        owner = owner_id or expense.get('owner_id') or ''
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO expenses (id, record_id, mode, category, amount, currency, description, date, owner_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    expense['id'],
                    expense.get('record_id'),
                    expense.get('mode', 'travel'),
                    expense.get('category', '其他'),
                    expense['amount'],
                    expense.get('currency', 'CNY'),
                    expense.get('description', ''),
                    expense.get('date'),
                    owner,
                    expense['created_at']
                ))
            conn.commit()
        return expense

    def update_expense(self, expense_id: str, expense: dict, owner_id: str = None) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM expenses WHERE id = %s AND (owner_id = %s OR owner_id = '')", (expense_id, owner_id or ''))
                if not cursor.fetchone():
                    return None
                cursor.execute("""
                    UPDATE expenses SET record_id=%s, mode=%s, category=%s, amount=%s, currency=%s, description=%s, date=%s
                    WHERE id=%s
                """, (
                    expense.get('record_id'),
                    expense.get('mode', 'travel'),
                    expense.get('category', '其他'),
                    expense['amount'],
                    expense.get('currency', 'CNY'),
                    expense.get('description', ''),
                    expense.get('date'),
                    expense_id
                ))
            conn.commit()
        return self._get_expense_by_id(expense_id, owner_id)

    def delete_expense(self, expense_id: str, owner_id: str = None) -> Optional[dict]:
        expense = self._get_expense_by_id(expense_id, owner_id)
        if not expense:
            return None
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
            conn.commit()
        return expense

    def _get_expense_by_id(self, expense_id: str, owner_id: str = None) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM expenses WHERE id = %s AND (owner_id = %s OR owner_id = '')", (expense_id, owner_id or ''))
                row = cursor.fetchone()
        if not row:
            return None
        return {'id': row[0], 'record_id': row[1], 'mode': row[2], 'category': row[3], 'amount': float(row[4]), 'currency': row[5], 'description': row[6], 'date': str(row[7]) if row[7] else None, 'owner_id': row[8], 'created_at': row[9].isoformat() if hasattr(row[9], 'isoformat') else str(row[9])}

    def get_expense_stats(self, owner_id: str = None) -> dict:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM expenses WHERE owner_id = %s OR owner_id = ''", (owner_id or '',))
                total = cursor.fetchone()
                cursor.execute("SELECT category, COUNT(*), COALESCE(SUM(amount), 0) FROM expenses WHERE owner_id = %s OR owner_id = '' GROUP BY category ORDER BY SUM(amount) DESC", (owner_id or '',))
                by_category = cursor.fetchall()
                cursor.execute("SELECT mode, COUNT(*), COALESCE(SUM(amount), 0) FROM expenses WHERE owner_id = %s OR owner_id = '' GROUP BY mode ORDER BY SUM(amount) DESC", (owner_id or '',))
                by_mode = cursor.fetchall()
        return {
            'total_count': total[0],
            'total_amount': float(total[1]),
            'by_category': [{'category': r[0], 'count': r[1], 'amount': float(r[2])} for r in by_category],
            'by_mode': [{'mode': r[0], 'count': r[1], 'amount': float(r[2])} for r in by_mode],
        }

    # ---- Users ----
    def create_user(self, user_id: str, username: str, password_hash: str, expires_at: str = None) -> dict:
        created_at = datetime.now().isoformat()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users")
                count = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO users (id, username, password_hash, expires_at, created_at) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, username, password_hash, expires_at, created_at)
                )
                if count == 0:
                    cursor.execute("UPDATE records SET owner_id = %s WHERE owner_id = '' OR owner_id IS NULL", (user_id,))
                    cursor.execute("UPDATE expenses SET owner_id = %s WHERE owner_id = '' OR owner_id IS NULL", (user_id,))
            conn.commit()
        return {'id': user_id, 'username': username, 'password_hash': password_hash, 'expires_at': expires_at, 'created_at': created_at}

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cursor.fetchone()
        if not row:
            return None
        return {'id': row[0], 'username': row[1], 'password_hash': row[2], 'expires_at': row[3], 'created_at': row[4].isoformat() if hasattr(row[4], 'isoformat') else str(row[4])}

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cursor.fetchone()
        if not row:
            return None
        return {'id': row[0], 'username': row[1], 'password_hash': row[2], 'expires_at': row[3], 'created_at': row[4].isoformat() if hasattr(row[4], 'isoformat') else str(row[4])}

    def claim_orphan_data(self, user_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE records SET owner_id = %s WHERE owner_id = '' OR owner_id IS NULL", (user_id,))
                cursor.execute("UPDATE expenses SET owner_id = %s WHERE owner_id = '' OR owner_id IS NULL", (user_id,))
            conn.commit()




def create_record_store(metadata_file: str = None) -> RecordStore:
    """根据 DB_TYPE 创建记录存储。DB_TYPE=json 可强制使用旧 JSON 文件。"""
    db_type = os.environ.get('DB_TYPE', DB_CONFIG['type']).lower()
    if db_type == 'json':
        if not metadata_file:
            metadata_file = os.path.join(os.path.dirname(__file__), 'records.json')
        return JsonRecordStore(metadata_file)
    if db_type == 'sqlite':
        db_path = os.environ.get('DB_NAME', DB_CONFIG['name'])
        return SQLiteRecordStore(db_path, metadata_file)
    if db_type in ('postgres', 'postgresql'):
        config = dict(DB_CONFIG)
        config.update({
            'type': db_type,
            'host': os.environ.get('DB_HOST', config['host']),
            'port': int(os.environ.get('DB_PORT', config['port'])),
            'name': os.environ.get('DB_NAME', config['name']),
            'user': os.environ.get('DB_USER', config['user']),
            'password': os.environ.get('DB_PASSWORD', config['password']),
        })
        return PostgresRecordStore(config)
    raise ValueError(f"Unsupported DB_TYPE: {db_type}")

# ========== 云存储配置 ==========
STORAGE_CONFIG = {
    'provider': os.environ.get('STORAGE_PROVIDER', 'local'),  # local, aliyun, tencent, qiniu, aws, gcp, azure
    
    # 阿里云OSS
    'aliyun': {
        'access_key': os.environ.get('ALIYUN_ACCESS_KEY', ''),
        'secret_key': os.environ.get('ALIYUN_SECRET_KEY', ''),
        'bucket': os.environ.get('ALIYUN_BUCKET', ''),
        'endpoint': os.environ.get('ALIYUN_ENDPOINT', 'oss-cn-hangzhou.aliyuncs.com'),
        'domain': os.environ.get('ALIYUN_DOMAIN', ''),
    },
    
    # 腾讯云COS
    'tencent': {
        'secret_id': os.environ.get('TENCENT_SECRET_ID', ''),
        'secret_key': os.environ.get('TENCENT_SECRET_KEY', ''),
        'bucket': os.environ.get('TENCENT_BUCKET', ''),
        'region': os.environ.get('TENCENT_REGION', 'ap-guangzhou'),
        'domain': os.environ.get('TENCENT_DOMAIN', ''),
    },
    
    # 七牛云
    'qiniu': {
        'access_key': os.environ.get('QINIU_ACCESS_KEY', ''),
        'secret_key': os.environ.get('QINIU_SECRET_KEY', ''),
        'bucket': os.environ.get('QINIU_BUCKET', ''),
        'domain': os.environ.get('QINIU_DOMAIN', ''),
    },
    
    # AWS S3
    'aws': {
        'access_key': os.environ.get('AWS_ACCESS_KEY', ''),
        'secret_key': os.environ.get('AWS_SECRET_KEY', ''),
        'bucket': os.environ.get('AWS_BUCKET', ''),
        'region': os.environ.get('AWS_REGION', 'us-east-1'),
        'domain': os.environ.get('AWS_DOMAIN', ''),
    },
    
    # Google Cloud Storage
    'gcp': {
        'project_id': os.environ.get('GCP_PROJECT_ID', ''),
        'bucket': os.environ.get('GCP_BUCKET', ''),
        'credentials': os.environ.get('GCP_CREDENTIALS', ''),
    },
    
    # Azure Blob Storage
    'azure': {
        'account_name': os.environ.get('AZURE_ACCOUNT_NAME', ''),
        'account_key': os.environ.get('AZURE_ACCOUNT_KEY', ''),
        'container': os.environ.get('AZURE_CONTAINER', ''),
    },
}


def load_runtime_config() -> Dict[str, Any]:
    """读取设置页保存的运行时配置。"""
    if not os.path.exists(RUNTIME_CONFIG_FILE):
        return {}
    try:
        with open(RUNTIME_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_runtime_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """保存设置页同步过来的运行时配置。"""
    current = load_runtime_config()
    current.update(config)
    os.makedirs(os.path.dirname(RUNTIME_CONFIG_FILE), exist_ok=True)
    with open(RUNTIME_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return current


def get_storage_config() -> Dict[str, Any]:
    """合并环境变量和运行时配置，环境变量缺省时允许设置页配置生效。"""
    runtime = load_runtime_config()
    config = json.loads(json.dumps(STORAGE_CONFIG))
    if runtime.get('storageProvider'):
        config['provider'] = runtime['storageProvider']

    mappings = {
        'aliyun': {
            'aliyunAccessKey': 'access_key',
            'aliyunSecretKey': 'secret_key',
            'aliyunBucket': 'bucket',
            'aliyunEndpoint': 'endpoint',
            'aliyunDomain': 'domain',
        },
        'tencent': {
            'tencentSecretId': 'secret_id',
            'tencentSecretKey': 'secret_key',
            'tencentBucket': 'bucket',
            'tencentRegion': 'region',
            'tencentDomain': 'domain',
        },
        'qiniu': {
            'qiniuAccessKey': 'access_key',
            'qiniuSecretKey': 'secret_key',
            'qiniuBucket': 'bucket',
            'qiniuDomain': 'domain',
        },
        'aws': {
            'awsAccessKey': 'access_key',
            'awsSecretKey': 'secret_key',
            'awsBucket': 'bucket',
            'awsRegion': 'region',
            'awsDomain': 'domain',
        },
        'gcp': {
            'gcpProjectId': 'project_id',
            'gcpBucket': 'bucket',
            'gcpCredentials': 'credentials',
        },
        'azure': {
            'azureAccountName': 'account_name',
            'azureAccountKey': 'account_key',
            'azureContainer': 'container',
        },
    }

    for provider, provider_mapping in mappings.items():
        for runtime_key, config_key in provider_mapping.items():
            if runtime.get(runtime_key):
                config[provider][config_key] = runtime[runtime_key]
    return config

# ========== 云存储接口 ==========
class StorageProvider:
    """云存储接口基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def upload(self, file_path: str, key: str) -> str:
        """上传文件，返回访问URL"""
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        """删除文件"""
        raise NotImplementedError
    
    def get_url(self, key: str) -> str:
        """获取文件访问URL"""
        raise NotImplementedError


class LocalStorage(StorageProvider):
    """本地存储"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.upload_dir = config.get('upload_dir', 'uploads')
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def upload(self, file_path: str, key: str) -> str:
        import shutil
        dest = os.path.join(self.upload_dir, key)
        shutil.copy2(file_path, dest)
        return f'/uploads/{key}'
    
    def delete(self, key: str) -> bool:
        path = os.path.join(self.upload_dir, key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
    
    def get_url(self, key: str) -> str:
        return f'/uploads/{key}'


class AliyunOSS(StorageProvider):
    """阿里云OSS"""
    
    def upload(self, file_path: str, key: str) -> str:
        import oss2
        auth = oss2.Auth(self.config['access_key'], self.config['secret_key'])
        bucket = oss2.Bucket(auth, self.config['endpoint'], self.config['bucket'])
        
        with open(file_path, 'rb') as f:
            bucket.put_object(key, f)
        
        return self.get_url(key)
    
    def delete(self, key: str) -> bool:
        import oss2
        auth = oss2.Auth(self.config['access_key'], self.config['secret_key'])
        bucket = oss2.Bucket(auth, self.config['endpoint'], self.config['bucket'])
        bucket.delete_object(key)
        return True
    
    def get_url(self, key: str) -> str:
        domain = self.config.get('domain', f"https://{self.config['bucket']}.{self.config['endpoint']}")
        return f"{domain}/{key}"


class TencentCOS(StorageProvider):
    """腾讯云COS"""
    
    def upload(self, file_path: str, key: str) -> str:
        from qcloud_cos import CosConfig, CosS3Client
        
        config = CosConfig(
            Region=self.config['region'],
            SecretId=self.config['secret_id'],
            SecretKey=self.config['secret_key']
        )
        client = CosS3Client(config)
        
        with open(file_path, 'rb') as f:
            client.put_object(
                Bucket=self.config['bucket'],
                Body=f,
                Key=key
            )
        
        return self.get_url(key)
    
    def delete(self, key: str) -> bool:
        from qcloud_cos import CosConfig, CosS3Client
        
        config = CosConfig(
            Region=self.config['region'],
            SecretId=self.config['secret_id'],
            SecretKey=self.config['secret_key']
        )
        client = CosS3Client(config)
        client.delete_object(Bucket=self.config['bucket'], Key=key)
        return True
    
    def get_url(self, key: str) -> str:
        domain = self.config.get('domain', f"https://{self.config['bucket']}.cos.{self.config['region']}.myqcloud.com")
        return f"{domain}/{key}"


class QiniuStorage(StorageProvider):
    """七牛云存储"""
    
    def upload(self, file_path: str, key: str) -> str:
        from qiniu import Auth, put_file
        
        q = Auth(self.config['access_key'], self.config['secret_key'])
        token = q.upload_token(self.config['bucket'], key)
        
        ret, _ = put_file(token, key, file_path)
        return self.get_url(key)
    
    def delete(self, key: str) -> bool:
        from qiniu import Auth, BucketManager
        
        q = Auth(self.config['access_key'], self.config['secret_key'])
        bucket = BucketManager(q)
        bucket.delete(self.config['bucket'], key)
        return True
    
    def get_url(self, key: str) -> str:
        domain = self.config.get('domain', f"https://{self.config['bucket']}.qiniucdn.com")
        return f"{domain}/{key}"


class AWSS3(StorageProvider):
    """AWS S3"""
    
    def upload(self, file_path: str, key: str) -> str:
        import boto3
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=self.config['access_key'],
            aws_secret_access_key=self.config['secret_key'],
            region_name=self.config['region']
        )
        
        s3.upload_file(file_path, self.config['bucket'], key)
        return self.get_url(key)
    
    def delete(self, key: str) -> bool:
        import boto3
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=self.config['access_key'],
            aws_secret_access_key=self.config['secret_key'],
            region_name=self.config['region']
        )
        
        s3.delete_object(Bucket=self.config['bucket'], Key=key)
        return True
    
    def get_url(self, key: str) -> str:
        domain = self.config.get('domain', f"https://{self.config['bucket']}.s3.{self.config['region']}.amazonaws.com")
        return f"{domain}/{key}"


class GCPStorage(StorageProvider):
    """Google Cloud Storage"""
    
    def upload(self, file_path: str, key: str) -> str:
        from google.cloud import storage
        
        client = storage.Client.from_service_account_json(self.config['credentials'])
        bucket = client.bucket(self.config['bucket'])
        blob = bucket.blob(key)
        blob.upload_from_filename(file_path)
        
        return self.get_url(key)
    
    def delete(self, key: str) -> bool:
        from google.cloud import storage
        
        client = storage.Client.from_service_account_json(self.config['credentials'])
        bucket = client.bucket(self.config['bucket'])
        blob = bucket.blob(key)
        blob.delete()
        return True
    
    def get_url(self, key: str) -> str:
        return f"https://storage.googleapis.com/{self.config['bucket']}/{key}"


class AzureBlob(StorageProvider):
    """Azure Blob Storage"""
    
    def upload(self, file_path: str, key: str) -> str:
        from azure.storage.blob import BlobServiceClient
        
        connect_str = f"DefaultEndpointsProtocol=https;AccountName={self.config['account_name']};AccountKey={self.config['account_key']};EndpointSuffix=core.windows.net"
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(self.config['container'])
        
        with open(file_path, 'rb') as data:
            container_client.upload_blob(name=key, data=data)
        
        return self.get_url(key)
    
    def delete(self, key: str) -> bool:
        from azure.storage.blob import BlobServiceClient
        
        connect_str = f"DefaultEndpointsProtocol=https;AccountName={self.config['account_name']};AccountKey={self.config['account_key']};EndpointSuffix=core.windows.net"
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(self.config['container'])
        
        blob_client = container_client.get_blob_client(key)
        blob_client.delete_blob()
        return True
    
    def get_url(self, key: str) -> str:
        return f"https://{self.config['account_name']}.blob.core.windows.net/{self.config['container']}/{key}"


def create_storage(provider_override: str = None) -> StorageProvider:
    """根据配置创建存储实例"""
    storage_config = get_storage_config()
    provider = provider_override or storage_config['provider']
    
    if provider == 'local':
        return LocalStorage({'upload_dir': 'uploads'})
    elif provider == 'aliyun':
        return AliyunOSS(storage_config['aliyun'])
    elif provider == 'tencent':
        return TencentCOS(storage_config['tencent'])
    elif provider == 'qiniu':
        return QiniuStorage(storage_config['qiniu'])
    elif provider == 'aws':
        return AWSS3(storage_config['aws'])
    elif provider == 'gcp':
        return GCPStorage(storage_config['gcp'])
    elif provider == 'azure':
        return AzureBlob(storage_config['azure'])
    else:
        raise ValueError(f"Unsupported storage provider: {provider}")

