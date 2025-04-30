# common/db.py
import sqlite3
import hashlib
from pathlib import Path

# 数据库文件存放在项目根目录
DB_PATH = Path(__file__).parent.parent / 'mia.db'


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    """创建 users 表（如果不存在）"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
              CREATE TABLE IF NOT EXISTS users
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  username
                  VARCHAR
                  UNIQUE
                  NOT
                  NULL,
                  password
                  CHAR
              (
                  8
              ) NOT NULL
                  )
              ''')
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """对明文密码做 SHA-256 哈希"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def add_user(username: str, password: str) -> bool:
    """注册新用户，用户名重复返回 False"""
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
    """验证用户名+密码是否匹配"""
    print("Checking user:", username)
    conn = get_connection()
    cur = conn.execute('SELECT password FROM users WHERE username = ?', (username,))
    row = cur.fetchone()
    conn.close()
    if row and row['password'] == hash_password(password):
        return True
    return False
