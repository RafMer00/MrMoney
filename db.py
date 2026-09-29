import sqlite3
from datetime import datetime
import pandas as pd

DB_NAME = "budget.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabella impostazioni (saldo iniziale)
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )''')
    # Tabella categorie
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                )''')
    # Tabella transazioni
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    type TEXT,  -- 'Entrata' o 'Uscita'
                    amount REAL,
                    title TEXT,
                    category TEXT
                )''')
    
    # Categorie predefinite richieste
    default_categories = ["io", "daniela", "famiglia"]
    for cat in default_categories:
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))
        
    conn.commit()
    conn.close()

def get_initial_balance():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'initial_balance'")
    row = c.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

def set_initial_balance(amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('initial_balance', ?)", (str(amount),))
    conn.commit()
    conn.close()

def add_category(name):
    if not name.strip():
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name.strip(),))
    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name FROM categories ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def add_transaction(date_str, trans_type, amount, title, category):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""INSERT INTO transactions (date, type, amount, title, category) 
                 VALUES (?, ?, ?, ?, ?)""", 
              (date_str, trans_type, amount, title.strip(), category))
    conn.commit()
    conn.close()

def get_transactions_df():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC, id DESC", conn)
    conn.close()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

def get_frequent_and_recent_titles():
    conn = sqlite3.connect(DB_NAME)
    # Più usati
    frequent = pd.read_sql_query("""
        SELECT title, COUNT(*) as cnt 
        FROM transactions 
        GROUP BY title 
        ORDER BY cnt DESC LIMIT 5
    """, conn)['title'].tolist()
    # Più recenti
    recent = pd.read_sql_query("""
        SELECT title 
        FROM transactions 
        ORDER BY id DESC LIMIT 5
    """, conn)['title'].drop_duplicates().tolist()
    conn.close()
    return frequent, recent