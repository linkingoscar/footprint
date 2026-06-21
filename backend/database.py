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

    def list(self, mode: str = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def update(self, record_id: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def delete(self, record_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    # ---- Expenses ----
    def list_expenses(self, record_id: str = None) -> list:
        raise NotImplementedError

    def create_expense(self, expense: dict) -> dict:
        raise NotImplementedError

    def update_expense(self, expense_id: str, expense: dict) -> Optional[dict]:
        raise NotImplementedError

    def delete_expense(self, expense_id: str) -> Optional[dict]:
        raise NotImplementedError

    def get_expense_stats(self) -> dict:
        raise NotImplementedError

    # ---- Users ----
    def create_user(self, user_id: str, username: str, password_hash: str) -> dict:
        raise NotImplementedError

    def get_user_by_username(self, username: str) -> Optional[dict]:
        raise NotImplementedError

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        raise NotImplementedError


class JsonRecordStore(RecordStore):
    """向后兼容的 JSON 文件存储。"""

    def __init__(self, metadata_file: str):
        self.metadata_file = metadata_file
        os.makedirs(os.path.dirname(metadata_file), exist_ok=True)

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save(self, records: List[Dict[str, Any]]):
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def list(self, mode: str = None) -> List[Dict[str, Any]]:
        records = self._load()
        if mode:
            records = [r for r in records if r.get('mode') == mode]
        return records

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        return next((r for r in self._load() if r.get('id') == record_id), None)

    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        records = self._load()
        records.insert(0, record)
        self._save(records)
        return record

    def update(self, record_id: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        records = self._load()
        for i, existing in enumerate(records):
            if existing.get('id') == record_id:
                records[i] = record
                self._save(records)
                return record
        return None

    def delete(self, record_id: str) -> Optional[Dict[str, Any]]:
        records = self._load()
        record = next((r for r in records if r.get('id') == record_id), None)
        if not record:
            return None
        self._save([r for r in records if r.get('id') != record_id])
        return record


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
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE SET NULL
                )
            """)

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

    def _upsert(self, record: Dict[str, Any]) -> Dict[str, Any]:
        tags = record.get('tags', [])
        metadata = record.get('metadata', {})
        images = record.get('images', [])
        created_at = record.get('createdAt') or record.get('created_at') or datetime.now().isoformat()
        updated_at = record.get('updatedAt') or record.get('updated_at') or datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO records (id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                created_at,
                updated_at
            ))
        return record

    # ---- CRUD ----
    def list(self, mode: str = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if mode:
                rows = conn.execute("SELECT * FROM records WHERE mode = ? ORDER BY date DESC, created_at DESC", (mode,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM records ORDER BY date DESC, created_at DESC").fetchall()
        return [self._row_to_record(row) for row in rows]

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return self._upsert(record)

    def update(self, record_id: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.get(record_id):
            return None
        return self._upsert(record)

    def delete(self, record_id: str) -> Optional[Dict[str, Any]]:
        record = self.get(record_id)
        if not record:
            return None
        with self._connect() as conn:
            conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        return record

    # ---- Expenses ----
    def list_expenses(self, record_id: str = None) -> list:
        with self._connect() as conn:
            if record_id:
                rows = conn.execute(
                    "SELECT * FROM expenses WHERE record_id = ? ORDER BY date DESC, created_at DESC",
                    (record_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM expenses ORDER BY date DESC, created_at DESC"
                ).fetchall()
        return [dict(row) for row in rows]

    def create_expense(self, expense: dict) -> dict:
        expense.setdefault('id', str(uuid.uuid4()))
        expense.setdefault('created_at', datetime.now().isoformat())
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO expenses (id, record_id, mode, category, amount, currency, description, date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                expense['id'],
                expense.get('record_id'),
                expense.get('mode', 'travel'),
                expense.get('category', '其他'),
                expense['amount'],
                expense.get('currency', 'CNY'),
                expense.get('description', ''),
                expense.get('date'),
                expense['created_at']
            ))
        return expense

    def update_expense(self, expense_id: str, expense: dict) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
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
        return self._get_expense_by_id(expense_id)

    def delete_expense(self, expense_id: str) -> Optional[dict]:
        expense = self._get_expense_by_id(expense_id)
        if not expense:
            return None
        with self._connect() as conn:
            conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return expense

    def _get_expense_by_id(self, expense_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return dict(row) if row else None

    def get_expense_stats(self) -> dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM expenses").fetchone()
            by_category = conn.execute(
                "SELECT category, COUNT(*), COALESCE(SUM(amount), 0) FROM expenses GROUP BY category ORDER BY SUM(amount) DESC"
            ).fetchall()
            by_mode = conn.execute(
                "SELECT mode, COUNT(*), COALESCE(SUM(amount), 0) FROM expenses GROUP BY mode ORDER BY SUM(amount) DESC"
            ).fetchall()
        return {
            'total_count': total[0],
            'total_amount': total[1],
            'by_category': [{'category': row[0], 'count': row[1], 'amount': row[2]} for row in by_category],
            'by_mode': [{'mode': row[0], 'count': row[1], 'amount': row[2]} for row in by_mode],
        }

    # ---- Users ----
    def create_user(self, user_id: str, username: str, password_hash: str) -> dict:
        created_at = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO users (id, username, password_hash, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, password_hash, created_at))
        return {'id': user_id, 'username': username, 'password_hash': password_hash, 'created_at': created_at}

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


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

    def _upsert(self, record: Dict[str, Any]) -> Dict[str, Any]:
        from psycopg2.extras import Json
        tags = record.get('tags', [])
        metadata = record.get('metadata', {})
        images = record.get('images', [])
        created_at = record.get('createdAt') or record.get('created_at') or datetime.now().isoformat()
        updated_at = record.get('updatedAt') or record.get('updated_at') or datetime.now().isoformat()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO records (id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    created_at,
                    updated_at
                ))
            conn.commit()
        return record

    # ---- CRUD ----
    def list(self, mode: str = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                if mode:
                    cursor.execute(
                        "SELECT id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, created_at, updated_at FROM records WHERE mode = %s ORDER BY date DESC, created_at DESC",
                        (mode,)
                    )
                else:
                    cursor.execute(
                        "SELECT id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, created_at, updated_at FROM records ORDER BY date DESC, created_at DESC"
                    )
                rows = cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, mode, title, description, location, latitude, longitude, date, rating, price, tags, metadata, images, created_at, updated_at FROM records WHERE id = %s",
                    (record_id,)
                )
                row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return self._upsert(record)

    def update(self, record_id: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.get(record_id):
            return None
        return self._upsert(record)

    def delete(self, record_id: str) -> Optional[Dict[str, Any]]:
        record = self.get(record_id)
        if not record:
            return None
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM records WHERE id = %s", (record_id,))
            conn.commit()
        return record

    # ---- Expenses ----
    def list_expenses(self, record_id: str = None) -> list:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                if record_id:
                    cursor.execute("SELECT * FROM expenses WHERE record_id = %s ORDER BY date DESC, created_at DESC", (record_id,))
                else:
                    cursor.execute("SELECT * FROM expenses ORDER BY date DESC, created_at DESC")
                rows = cursor.fetchall()
        return [{'id': r[0], 'record_id': r[1], 'mode': r[2], 'category': r[3], 'amount': float(r[4]), 'currency': r[5], 'description': r[6], 'date': str(r[7]) if r[7] else None, 'created_at': r[8].isoformat() if hasattr(r[8], 'isoformat') else str(r[8])} for r in rows]

    def create_expense(self, expense: dict) -> dict:
        expense.setdefault('id', str(uuid.uuid4()))
        expense.setdefault('created_at', datetime.now().isoformat())
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO expenses (id, record_id, mode, category, amount, currency, description, date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    expense['id'],
                    expense.get('record_id'),
                    expense.get('mode', 'travel'),
                    expense.get('category', '其他'),
                    expense['amount'],
                    expense.get('currency', 'CNY'),
                    expense.get('description', ''),
                    expense.get('date'),
                    expense['created_at']
                ))
            conn.commit()
        return expense

    def update_expense(self, expense_id: str, expense: dict) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
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
        return self._get_expense_by_id(expense_id)

    def delete_expense(self, expense_id: str) -> Optional[dict]:
        expense = self._get_expense_by_id(expense_id)
        if not expense:
            return None
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
            conn.commit()
        return expense

    def _get_expense_by_id(self, expense_id: str) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
                row = cursor.fetchone()
        if not row:
            return None
        return {'id': row[0], 'record_id': row[1], 'mode': row[2], 'category': row[3], 'amount': float(row[4]), 'currency': row[5], 'description': row[6], 'date': str(row[7]) if row[7] else None, 'created_at': row[8].isoformat() if hasattr(row[8], 'isoformat') else str(row[8])}

    def get_expense_stats(self) -> dict:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM expenses")
                total = cursor.fetchone()
                cursor.execute("SELECT category, COUNT(*), COALESCE(SUM(amount), 0) FROM expenses GROUP BY category ORDER BY SUM(amount) DESC")
                by_category = cursor.fetchall()
                cursor.execute("SELECT mode, COUNT(*), COALESCE(SUM(amount), 0) FROM expenses GROUP BY mode ORDER BY SUM(amount) DESC")
                by_mode = cursor.fetchall()
        return {
            'total_count': total[0],
            'total_amount': float(total[1]),
            'by_category': [{'category': r[0], 'count': r[1], 'amount': float(r[2])} for r in by_category],
            'by_mode': [{'mode': r[0], 'count': r[1], 'amount': float(r[2])} for r in by_mode],
        }

    # ---- Users ----
    def create_user(self, user_id: str, username: str, password_hash: str) -> dict:
        created_at = datetime.now().isoformat()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (id, username, password_hash, created_at) VALUES (%s, %s, %s, %s)",
                    (user_id, username, password_hash, created_at)
                )
            conn.commit()
        return {'id': user_id, 'username': username, 'password_hash': password_hash, 'created_at': created_at}

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cursor.fetchone()
        if not row:
            return None
        return {'id': row[0], 'username': row[1], 'password_hash': row[2], 'created_at': row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3])}

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cursor.fetchone()
        if not row:
            return None
        return {'id': row[0], 'username': row[1], 'password_hash': row[2], 'created_at': row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3])}




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

# ========== 数据库表结构 ==========
DATABASE_SCHEMA = """
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    avatar_url VARCHAR(500),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 记录表
CREATE TABLE IF NOT EXISTS records (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id),
    mode VARCHAR(20) NOT NULL,  -- travel, food, love
    title VARCHAR(200) NOT NULL,
    description TEXT,
    location VARCHAR(500),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    date DATE,
    rating INTEGER,
    price DECIMAL(10,2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 图片表
CREATE TABLE IF NOT EXISTS images (
    id VARCHAR(36) PRIMARY KEY,
    record_id VARCHAR(36) REFERENCES records(id) ON DELETE CASCADE,
    user_id VARCHAR(36) REFERENCES users(id),
    url VARCHAR(1000) NOT NULL,
    storage_key VARCHAR(500),
    storage_provider VARCHAR(20),
    original_name VARCHAR(200),
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    exif_data JSONB DEFAULT '{}',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    color VARCHAR(20),
    user_id VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 记录-标签关联表
CREATE TABLE IF NOT EXISTS record_tags (
    record_id VARCHAR(36) REFERENCES records(id) ON DELETE CASCADE,
    tag_id VARCHAR(36) REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (record_id, tag_id)
);

-- 成就表
CREATE TABLE IF NOT EXISTS achievements (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_records_user_id ON records(user_id);
CREATE INDEX IF NOT EXISTS idx_records_mode ON records(mode);
CREATE INDEX IF NOT EXISTS idx_records_date ON records(date);
CREATE INDEX IF NOT EXISTS idx_records_location ON records(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_images_record_id ON images(record_id);
CREATE INDEX IF NOT EXISTS idx_images_user_id ON images(user_id);
"""

# ========== 数据库接口 ==========
class Database:
    """数据库接口基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    def connect(self):
        raise NotImplementedError
    
    def disconnect(self):
        raise NotImplementedError
    
    def execute(self, query: str, params: tuple = None):
        raise NotImplementedError
    
    def fetchone(self, query: str, params: tuple = None):
        raise NotImplementedError
    
    def fetchall(self, query: str, params: tuple = None):
        raise NotImplementedError
    
    def init_tables(self):
        raise NotImplementedError


class SQLiteDatabase(Database):
    """SQLite数据库"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_path = config.get('name', 'footprint.db')
    
    def connect(self):
        import sqlite3
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
    
    def execute(self, query: str, params: tuple = None):
        cursor = self.connection.cursor()
        cursor.execute(query, params or ())
        self.connection.commit()
        return cursor
    
    def fetchone(self, query: str, params: tuple = None):
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetchall(self, query: str, params: tuple = None):
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def init_tables(self):
        # SQLite 版本的建表语句
        sqlite_schema = """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            avatar_url TEXT,
            settings TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            mode TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            date TEXT,
            rating INTEGER,
            price REAL,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            record_id TEXT REFERENCES records(id) ON DELETE CASCADE,
            user_id TEXT REFERENCES users(id),
            url TEXT NOT NULL,
            storage_key TEXT,
            storage_provider TEXT,
            original_name TEXT,
            file_size INTEGER,
            width INTEGER,
            height INTEGER,
            exif_data TEXT DEFAULT '{}',
            latitude REAL,
            longitude REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS tags (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT,
            user_id TEXT REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS record_tags (
            record_id TEXT REFERENCES records(id) ON DELETE CASCADE,
            tag_id TEXT REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (record_id, tag_id)
        );
        
        CREATE TABLE IF NOT EXISTS achievements (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_records_user_id ON records(user_id);
        CREATE INDEX IF NOT EXISTS idx_records_mode ON records(mode);
        CREATE INDEX IF NOT EXISTS idx_records_date ON records(date);
        CREATE INDEX IF NOT EXISTS idx_images_record_id ON images(record_id);
        CREATE INDEX IF NOT EXISTS idx_images_user_id ON images(user_id);
        """
        self.connection.executescript(sqlite_schema)


class PostgresDatabase(Database):
    """PostgreSQL数据库"""
    
    def connect(self):
        import psycopg2
        self.connection = psycopg2.connect(
            host=self.config['host'],
            port=self.config['port'],
            database=self.config['name'],
            user=self.config['user'],
            password=self.config['password']
        )
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
    
    def execute(self, query: str, params: tuple = None):
        cursor = self.connection.cursor()
        cursor.execute(query, params or ())
        self.connection.commit()
        return cursor
    
    def fetchone(self, query: str, params: tuple = None):
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetchall(self, query: str, params: tuple = None):
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def init_tables(self):
        self.connection.executescript(DATABASE_SCHEMA)


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


# ========== 工厂函数 ==========
def create_database() -> Database:
    """根据配置创建数据库实例"""
    db_type = DB_CONFIG['type']
    
    if db_type == 'sqlite':
        return SQLiteDatabase(DB_CONFIG)
    elif db_type == 'postgres':
        return PostgresDatabase(DB_CONFIG)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


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


# ========== 数据访问层 ==========
class RecordRepository:
    """记录数据访问"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """创建记录"""
        query = """
            INSERT INTO records (id, user_id, mode, title, description, location, latitude, longitude, date, rating, price, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(query, (
            record['id'],
            record.get('user_id'),
            record['mode'],
            record['title'],
            record.get('description'),
            record.get('location'),
            record.get('latitude'),
            record.get('longitude'),
            record.get('date'),
            record.get('rating'),
            record.get('price'),
            json.dumps(record.get('metadata', {}))
        ))
        return record
    
    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取记录"""
        query = "SELECT * FROM records WHERE id = ?"
        row = self.db.fetchone(query, (record_id,))
        return dict(row) if row else None
    
    def get_by_user(self, user_id: str, mode: str = None) -> List[Dict[str, Any]]:
        """获取用户记录"""
        if mode:
            query = "SELECT * FROM records WHERE user_id = ? AND mode = ? ORDER BY date DESC"
            rows = self.db.fetchall(query, (user_id, mode))
        else:
            query = "SELECT * FROM records WHERE user_id = ? ORDER BY date DESC"
            rows = self.db.fetchall(query, (user_id,))
        return [dict(row) for row in rows]
    
    def update(self, record_id: str, data: Dict[str, Any]) -> bool:
        """更新记录"""
        fields = []
        values = []
        for key, value in data.items():
            if key not in ('id', 'user_id', 'created_at'):
                fields.append(f"{key} = ?")
                values.append(value)
        
        values.append(record_id)
        query = f"UPDATE records SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self.db.execute(query, tuple(values))
        return True
    
    def delete(self, record_id: str) -> bool:
        """删除记录"""
        query = "DELETE FROM records WHERE id = ?"
        self.db.execute(query, (record_id,))
        return True


class ImageRepository:
    """图片数据访问"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create(self, image: Dict[str, Any]) -> Dict[str, Any]:
        """创建图片记录"""
        query = """
            INSERT INTO images (id, record_id, user_id, url, storage_key, storage_provider, original_name, file_size, exif_data, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(query, (
            image['id'],
            image.get('record_id'),
            image.get('user_id'),
            image['url'],
            image.get('storage_key'),
            image.get('storage_provider'),
            image.get('original_name'),
            image.get('file_size'),
            json.dumps(image.get('exif_data', {})),
            image.get('latitude'),
            image.get('longitude')
        ))
        return image
    
    def get_by_record(self, record_id: str) -> List[Dict[str, Any]]:
        """获取记录的所有图片"""
        query = "SELECT * FROM images WHERE record_id = ? ORDER BY created_at"
        rows = self.db.fetchall(query, (record_id,))
        return [dict(row) for row in rows]
    
    def delete(self, image_id: str) -> bool:
        """删除图片"""
        query = "DELETE FROM images WHERE id = ?"
        self.db.execute(query, (image_id,))
        return True
