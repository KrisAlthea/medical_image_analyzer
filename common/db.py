import hashlib
import sqlite3
from pathlib import Path

# 数据库文件放在项目根目录
DB_PATH = Path(__file__).parent.parent / 'mia.db'


def get_connection() -> sqlite3.Connection:
    """获得一个 sqlite3 连接，row_factory 设置为 sqlite3.Row 以便以 dict 方式访问字段。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    """
    创建 users 表和 history 表（如果不存在）。
    请在应用启动时调用一次。
    """
    conn = get_connection()
    c = conn.cursor()

    # 1. 用户表
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER   PRIMARY KEY AUTOINCREMENT,
            username     VARCHAR   UNIQUE NOT NULL,
            password     CHAR(64)   NOT NULL
        )
    ''')

    # 2. 历史记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id              INTEGER   PRIMARY KEY AUTOINCREMENT,
            original_path   TEXT      NOT NULL,
            processed_path  TEXT      NOT NULL,
            timestamp       DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
            operator_id     INTEGER   NOT NULL,
            is_retina       BOOLEAN   NOT NULL CHECK(is_retina IN (0,1)),
            FOREIGN KEY(operator_id)  REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """对明文密码做 SHA-256 哈希，返回 64 字符十六进制字符串。"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def add_user(username: str, password: str) -> bool:
    """注册新用户，用户名重复返回 False。"""
    try:
        conn = get_connection()
        conn.execute(
            'INSERT INTO users (username, password) VALUES (?, ?)',
            (username, hash_password(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def check_user(username: str, password: str) -> bool:
    """验证用户名+密码是否匹配。"""
    conn = get_connection()
    cur = conn.execute(
        'SELECT password FROM users WHERE username = ?',
        (username,)
    )
    row = cur.fetchone()
    conn.close()
    return bool(row and row['password'] == hash_password(password))


def get_user_id(username: str) -> int | None:
    conn = get_connection()
    cur  = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
    row  = cur.fetchone()
    conn.close()
    return row["id"] if row else None


def add_history_record(
    original_path: str,
    processed_path: str,
    operator_id: int,
    is_retina: bool
):
    """
    插入一条历史记录。is_retina: True=视网膜, False=晶状体。
    timestamp 使用 CURRENT_TIMESTAMP。
    """
    conn = get_connection()
    conn.execute(
        '''
        INSERT INTO history
            (original_path, processed_path, operator_id, is_retina)
        VALUES (?, ?, ?, ?)
        ''',
        (original_path, processed_path, operator_id, int(is_retina))
    )
    conn.commit()
    conn.close()


def get_history_records() -> list[sqlite3.Row]:
    """
    按时间倒序取出所有历史记录，返回字段包括 is_retina。
    """
    conn = get_connection()
    cur = conn.execute(
        '''
        SELECT
            h.id,
            h.original_path,
            h.processed_path,
            h.timestamp,
            h.operator_id,
            h.is_retina
        FROM history h
        ORDER BY h.timestamp DESC
        '''
    )
    rows = cur.fetchall()
    conn.close()
    return rows



def clear_history():
    """删除所有历史记录。"""
    conn = get_connection()
    conn.execute('DELETE FROM history')
    conn.commit()
    conn.close()
