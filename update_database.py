"""
update_database.py  -  rebuilds customer_support.db with a richer demo dataset.

Run it from the project root (venv activated):

    python update_database.py

What it does
  1. Copies customer_support.db to customer_support.backup.db (only the first time,
     so your original data is never overwritten by a second run).
  2. Recreates the tables: customers, orders, refunds, policies, faq.
  3. Creates the unanswered_questions table if it does not exist (rows are kept).
     The assistant writes there every question it could not answer.
  4. Fills everything with sample data. ALL DATES ARE RELATIVE TO TODAY, so run the
     script again whenever you want fresh dates.

The policy values below are SAMPLE values. Change them to your real store policy.
"""

import shutil
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

DB_PATH = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(__file__).resolve().parent / "customer_support.db"
)

TODAY = date.today()

# The company contact email given to customers (stored in the database).
CONTACT_EMAIL = "boutique@exmple.tn"


def d(offset):
    """Date as text, `offset` days from today (negative = in the past)."""
    if offset is None:
        return None
    return (TODAY + timedelta(days=offset)).isoformat()


# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------

CUSTOMERS = [
    ("C001", "Alice", "alice@example.com"),
    ("C002", "Bob", "bob@example.com"),
    ("C003", "Charlie", "charlie@example.com"),
    ("C004", "Diana", "diana@example.com"),
    ("C005", "Omar", "omar@example.com"),
]

# order_id, customer, product, category, status, amount,
# order_offset, shipped_offset, delivered_offset, expected_offset, carrier, tracking
ORDERS = [
    # on its way, arrives in 2 days
    ("ORD001", "C001", "Wireless Headphones", "electronics", "shipped", 79.99,
     -6, -4, None, 2, "DHL", "DHL4471920"),
    # delivered 9 days ago, refund already in progress (REF001)
    ("ORD002", "C001", "Laptop Stand", "accessories", "delivered", 39.99,
     -14, -12, -9, -9, "DHL", "DHL3382110"),
    # not shipped yet -> can still be cancelled
    ("ORD003", "C002", "Mechanical Keyboard", "electronics", "processing", 89.99,
     -2, None, None, 5, None, None),
    # delivered 30 days ago, refund already completed (REF002)
    ("ORD004", "C003", "USB Microphone", "electronics", "delivered", 59.99,
     -35, -33, -30, -30, "FedEx", "FX771204"),
    # delivered 5 days ago -> refund ELIGIBLE (25 days left)
    ("ORD005", "C002", "Gaming Mouse", "electronics", "delivered", 49.99,
     -11, -9, -5, -5, "Aramex", "AR330145"),
    # delivered 45 days ago -> refund NOT eligible (window exceeded)
    ("ORD006", "C003", "Bluetooth Speaker", "electronics", "delivered", 69.90,
     -52, -50, -45, -45, "DHL", "DHL2290871"),
    # shipped but LATE (expected 3 days ago)
    ("ORD007", "C004", "Phone Case", "accessories", "shipped", 14.50,
     -12, -10, None, -3, "FedEx", "FX880213"),
    # delivered 2 days ago but non-returnable category (software)
    ("ORD008", "C004", "Photo Editing Software", "software", "delivered", 129.00,
     -2, -2, -2, -2, None, None),
    # out for delivery, arrives today
    ("ORD009", "C005", "Office Chair", "furniture", "out_for_delivery", 189.00,
     -8, -6, None, 0, "Aramex", "AR552910"),
    # cancelled, refund in progress (REF003)
    ("ORD010", "C005", "HD Webcam", "electronics", "cancelled", 45.00,
     -4, None, None, None, None, None),
    # gift card delivered yesterday -> non-returnable
    ("ORD011", "C001", "Gift Card 50", "gift_card", "delivered", 50.00,
     -1, -1, -1, -1, None, None),
    # delivered 29 days ago -> eligible, last day tomorrow (1 day left)
    ("ORD012", "C002", "4K Monitor", "electronics", "delivered", 299.00,
     -35, -33, -29, -29, "DHL", "DHL9981204"),
]

# refund_id, order_id, status, amount, requested_offset, reason, estimated_completion_offset
REFUNDS = [
    ("REF001", "ORD002", "processing", 39.99, -3, "Item no longer needed", 4),
    ("REF002", "ORD004", "completed", 59.99, -25, "Defective item", -18),
    ("REF003", "ORD010", "processing", 45.00, -3, "Order cancelled by customer", 4),
]

POLICIES = [
    ("return_window_days", "30"),
    ("non_returnable_categories", "gift_card, software"),
    ("refund_processing", "Refunds are processed within 5 to 7 business days after approval."),
    ("cancellation_rule", "An order can be cancelled only while its status is 'processing' (before it ships)."),
    ("cancellation_procedure", "The customer can cancel an eligible order from their profile on the website. Once the cancellation is confirmed there, the order is cancelled."),
    ("delivery_options", "Standard delivery takes 3 to 5 business days. Express delivery takes 1 to 2 business days. Fees are shown at checkout."),
    ("contact_email", CONTACT_EMAIL),
]

# General store information. SAMPLE ANSWERS: replace them with the real ones
# (the assistant repeats exactly what is written here, and nothing else).
FAQ = [
    ("Physical store (for example: do you have a store in Tunis?)",
     "We are an online store and we do not have a physical shop. "
     "All orders are placed on our website and delivered to the customer's address."),
    ("Delivery area",
     "We deliver across Tunisia."),
    ("Payment methods",
     "Customers can pay by bank card or cash on delivery."),
    ("Contact and customer service",
     f"The company can be contacted by email at {CONTACT_EMAIL}. "
     "The team replies within 1 to 2 business days."),
    ("Changing the delivery address",
     "Delivery addresses cannot be changed through this assistant. "
     f"Please email {CONTACT_EMAIL} with your order number as soon as possible."),
    ("Payment problems (charged twice, failed payment)",
     "This assistant cannot see payment details. "
     f"Please email {CONTACT_EMAIL} with your order number and the payment details."),
    ("Modifying an order (items, quantity)",
     "Orders cannot be modified through this assistant. If the order has not shipped yet, "
     "it can be cancelled from the customer's profile on the website and a new one placed; "
     f"otherwise please email {CONTACT_EMAIL}."),
    ("Product information (specifications, compatibility, features)",
     "This assistant does not have detailed product specifications. "
     f"Please check the product page on our website or email {CONTACT_EMAIL}."),
]


# ---------------------------------------------------------------------------
# BUILD
# ---------------------------------------------------------------------------

def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run this script from the project root, or pass the path as an argument.")
        sys.exit(1)

    backup = DB_PATH.with_name(DB_PATH.stem + ".backup.db")
    if not backup.exists():
        shutil.copy2(DB_PATH, backup)
        print(f"Backup created: {backup.name}")
    else:
        print(f"Backup already exists, kept as is: {backup.name}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript(
        """
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS refunds;
        DROP TABLE IF EXISTS policies;
        DROP TABLE IF EXISTS faq;

        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            name        TEXT,
            email       TEXT
        );

        CREATE TABLE orders (
            order_id        TEXT PRIMARY KEY,
            customer_id     TEXT,
            product         TEXT,
            status          TEXT,
            delivery_date   TEXT,   -- expected date, or the real date once delivered
            amount          REAL,
            order_date      TEXT,
            shipped_date    TEXT,
            delivered_date  TEXT,
            carrier         TEXT,
            tracking_number TEXT,
            category        TEXT
        );

        CREATE TABLE refunds (
            refund_id                 TEXT PRIMARY KEY,
            order_id                  TEXT,
            status                    TEXT,
            amount                    REAL,
            requested_date            TEXT,
            reason                    TEXT,
            estimated_completion_date TEXT
        );

        CREATE TABLE policies (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE faq (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            topic  TEXT,
            answer TEXT
        );

        CREATE TABLE IF NOT EXISTS unanswered_questions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at       TEXT,
            customer_message TEXT,
            order_id         TEXT
        );
        """
    )

    cur.executemany("INSERT INTO customers VALUES (?, ?, ?)", CUSTOMERS)

    for (oid, cid, product, category, status, amount,
         o_off, s_off, dl_off, exp_off, carrier, tracking) in ORDERS:
        cur.execute(
            """
            INSERT INTO orders
            (order_id, customer_id, product, status, delivery_date, amount,
             order_date, shipped_date, delivered_date, carrier, tracking_number, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (oid, cid, product, status, d(exp_off), amount,
             d(o_off), d(s_off), d(dl_off), carrier, tracking, category),
        )

    for rid, oid, status, amount, req_off, reason, est_off in REFUNDS:
        cur.execute(
            "INSERT INTO refunds VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rid, oid, status, amount, d(req_off), reason, d(est_off)),
        )

    cur.executemany("INSERT INTO policies VALUES (?, ?)", POLICIES)
    cur.executemany("INSERT INTO faq (topic, answer) VALUES (?, ?)", FAQ)

    conn.commit()
    conn.close()

    print(f"\nDatabase updated (today = {TODAY.isoformat()}).")
    print(f"  customers: {len(CUSTOMERS)} | orders: {len(ORDERS)} | "
          f"refunds: {len(REFUNDS)} | policies: {len(POLICIES)} | faq: {len(FAQ)}")

    print("\nTEST CASES (the assistant will ask for the order's email first)")
    print("-" * 78)
    cases = [
        ("ORD001", "alice@example.com", "shipped, arrives in 2 days (DHL tracking)"),
        ("ORD002", "alice@example.com", "refund already in progress (REF001)"),
        ("ORD003", "bob@example.com", "not shipped yet, can be cancelled"),
        ("ORD004", "charlie@example.com", "refund already completed (REF002)"),
        ("ORD005", "bob@example.com", "refund ELIGIBLE (25 days left)"),
        ("ORD006", "charlie@example.com", "refund NOT eligible (window exceeded)"),
        ("ORD007", "diana@example.com", "shipped but LATE by 3 days"),
        ("ORD008", "diana@example.com", "software, not returnable"),
        ("ORD009", "omar@example.com", "out for delivery, arrives today"),
        ("ORD010", "omar@example.com", "cancelled, refund in progress (REF003)"),
        ("ORD011", "alice@example.com", "gift card, not returnable"),
        ("ORD012", "bob@example.com", "refund eligible, 1 day left"),
    ]
    for oid, email, note in cases:
        print(f"{oid}  {email:<22} {note}")
    print("-" * 78)
    print(f"Anything not covered by the orders, policies or FAQ gets the 'contact us at {CONTACT_EMAIL}' answer.")
    print("Unknown order (e.g. ORD999): the assistant asks the customer to check the number.")


if __name__ == "__main__":
    main()
