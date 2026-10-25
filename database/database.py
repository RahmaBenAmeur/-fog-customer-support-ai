import sqlite3

DB_PATH = "customer_support.db"


def get_order(order_id):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    row = cursor.execute(
        """
        SELECT order_id, customer_id, product, status, delivery_date, amount
        FROM orders
        WHERE order_id = ?
        """,
        (order_id,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return {
        "order_id": row[0],
        "customer_id": row[1],
        "product": row[2],
        "status": row[3],
        "delivery_date": row[4],
        "amount": row[5]
    }


def get_refund(order_id):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    row = cursor.execute(
        """
        SELECT refund_id, order_id, status, amount
        FROM refunds
        WHERE order_id = ?
        """,
        (order_id,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return {
        "refund_id": row[0],
        "order_id": row[1],
        "status": row[2],
        "amount": row[3]
    }


def get_customer(customer_id):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    row = cursor.execute(
        """
        SELECT customer_id, name, email
        FROM customers
        WHERE customer_id = ?
        """,
        (customer_id,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return {
        "customer_id": row[0],
        "name": row[1],
        "email": row[2]
    }