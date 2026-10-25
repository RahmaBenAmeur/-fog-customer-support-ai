import sqlite3

DB_PATH = "customer_support.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

tables = ["customers", "orders", "refunds"]

for table in tables:

    print("\n" + "=" * 60)
    print(f"📋 {table.upper()}")
    print("=" * 60)

    rows = cursor.execute(
        f"SELECT * FROM {table} LIMIT 5"
    ).fetchall()

    for row in rows:
        print(row)

connection.close()