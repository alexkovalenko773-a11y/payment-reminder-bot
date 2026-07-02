import sqlite3

DB_NAME = "payments.db"


def connect():
    return sqlite3.connect(DB_NAME)


def create_tables():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        amount INTEGER,
        day INTEGER,
        category TEXT,
        link TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminder_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id INTEGER,
        reminder_date TEXT,
        reminder_type TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paid_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id INTEGER,
        paid_month TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT
    )
    """)

    conn.commit()
    conn.close()


def ensure_default_categories(user_id):
    default_categories = ["🏠 Дом", "💼 Бизнес", "📱 Подписки", "🚗 Авто", "➕ Другое"]

    existing = get_categories(user_id)

    if existing:
        return

    conn = connect()
    cursor = conn.cursor()

    for category in default_categories:
        cursor.execute("""
        INSERT INTO categories (user_id, name)
        VALUES (?, ?)
        """, (user_id, category))

    conn.commit()
    conn.close()


def get_categories(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, name
    FROM categories
    WHERE user_id = ?
    ORDER BY id
    """, (user_id,))

    result = cursor.fetchall()
    conn.close()
    return result


def add_category(user_id, name):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO categories (user_id, name)
    VALUES (?, ?)
    """, (user_id, name))

    conn.commit()
    conn.close()


def delete_category(category_id, user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM categories
    WHERE id = ? AND user_id = ?
    """, (category_id, user_id))

    conn.commit()
    conn.close()


def add_payment(user_id, name, amount, day, category, link):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO payments (user_id, name, amount, day, category, link)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, name, amount, day, category, link))

    conn.commit()
    conn.close()


def get_payments(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, name, amount, day, category, link
    FROM payments
    WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchall()
    conn.close()
    return result


def get_payments_by_category(user_id, category):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, name, amount, day, category, link
    FROM payments
    WHERE user_id = ? AND category = ?
    """, (user_id, category))

    result = cursor.fetchall()
    conn.close()
    return result


def get_all_payments():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, user_id, name, amount, day, category, link
    FROM payments
    """)

    result = cursor.fetchall()
    conn.close()
    return result


def reminder_was_sent(payment_id, reminder_date, reminder_type):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id FROM reminder_log
    WHERE payment_id = ? AND reminder_date = ? AND reminder_type = ?
    """, (payment_id, reminder_date, reminder_type))

    result = cursor.fetchone()
    conn.close()
    return result is not None


def save_reminder(payment_id, reminder_date, reminder_type):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reminder_log (payment_id, reminder_date, reminder_type)
    VALUES (?, ?, ?)
    """, (payment_id, reminder_date, reminder_type))

    conn.commit()
    conn.close()


def mark_as_paid(payment_id, paid_month):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO paid_log (payment_id, paid_month)
    VALUES (?, ?)
    """, (payment_id, paid_month))

    conn.commit()
    conn.close()


def is_paid(payment_id, paid_month):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id FROM paid_log
    WHERE payment_id = ? AND paid_month = ?
    """, (payment_id, paid_month))

    result = cursor.fetchone()
    conn.close()
    return result is not None


def delete_payment(payment_id, user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM payments
    WHERE id = ? AND user_id = ?
    """, (payment_id, user_id))

    conn.commit()
    conn.close()


def get_payment_by_id(payment_id, user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, name, amount, day, category, link
    FROM payments
    WHERE id = ? AND user_id = ?
    """, (payment_id, user_id))

    result = cursor.fetchone()
    conn.close()
    return result


def update_payment_field(payment_id, user_id, field, value):
    allowed_fields = ["name", "amount", "day", "category", "link"]

    if field not in allowed_fields:
        return

    conn = connect()
    cursor = conn.cursor()

    cursor.execute(f"""
    UPDATE payments
    SET {field} = ?
    WHERE id = ? AND user_id = ?
    """, (value, payment_id, user_id))

    conn.commit()
    conn.close()