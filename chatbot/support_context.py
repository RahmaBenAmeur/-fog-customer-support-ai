"""
chatbot/support_context.py  -  shared support logic for app.py and whisper_app.py.

What it does, for every customer message:
  1. finds the order number (and the customer's email) in the conversation
  2. reads the order / refund / policies / FAQ from customer_support.db
  3. computes delivery status, refund eligibility and cancellation IN PYTHON
     (small LLMs are bad at date arithmetic, so the LLM never calculates)
  4. builds the system prompt for the LLM
  5. if the LLM answers "NO_INFO" (= the question cannot be answered from the
     data), replaces it with a fixed message that sends the customer to the
     company email, and logs the question in the `unanswered_questions` table
     (so you can see what to add to the FAQ)
"""

import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

import os
import time
import requests

try:
    from metrics import record
except ImportError: # app.py lancé seul, sans metrics.py
    record = lambda *a, **k: None


# ============================================================
# SETTINGS  (the only things you normally need to change)
# ============================================================

LLM_MODEL = "llama3.1:8b"          # e.g. "llama3.1:8b" if that is the one you have

# True  -> the customer must give the email of the order before seeing any detail
# False -> the order number alone is enough
REQUIRE_EMAIL_VERIFICATION = True

HISTORY_MESSAGES = 6               # how many recent messages the LLM sees

# The real contact email is stored in the database (policies table, key
# "contact_email", set in update_database.py). This value is only a fallback.
DEFAULT_CONTACT_EMAIL = "boutique@exmple.tn"

# How a customer cancels an order. The real text is stored in the database
# (policies table, key "cancellation_procedure"); this is only a fallback.
DEFAULT_CANCELLATION_PROCEDURE = (
    "The customer can cancel the order from their profile on the website. "
    "Once the cancellation is confirmed there, the order is cancelled."
)

NO_INFO_MESSAGE = (
    "I'm sorry, I don't have that information. "
    "For this request, it is better to contact the company directly "
    "by email at {email}."
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "customer_support.db"


# ============================================================
# DATABASE
# ============================================================

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_one(sql, params=()):
    conn = _connect()
    try:
        row = conn.execute(sql, params).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def get_order(order_id):
    return _fetch_one(
        """
        SELECT o.*, c.name AS customer_name, c.email AS customer_email
        FROM orders o
        LEFT JOIN customers c ON c.customer_id = o.customer_id
        WHERE o.order_id = ?
        """,
        (order_id,),
    )


def get_refund(order_id):
    return _fetch_one("SELECT * FROM refunds WHERE order_id = ?", (order_id,))


def get_policies():
    conn = _connect()
    try:
        rows = conn.execute("SELECT key, value FROM policies").fetchall()
    except sqlite3.OperationalError:
        return {}          # table missing: run update_database.py
    finally:
        conn.close()
    return {row["key"]: row["value"] for row in rows}


def get_faq():
    """General store information: list of (topic, answer)."""
    conn = _connect()
    try:
        rows = conn.execute("SELECT topic, answer FROM faq ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        return []          # table missing: run update_database.py
    finally:
        conn.close()
    return [(row["topic"], row["answer"]) for row in rows]


def log_unanswered(customer_message, order_id=None):
    """Remember a question the assistant could not answer."""
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS unanswered_questions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at       TEXT,
                customer_message TEXT,
                order_id         TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO unanswered_questions (created_at, customer_message, order_id) "
            "VALUES (?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), customer_message, order_id),
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# FINDING THE ORDER NUMBER AND THE EMAIL IN THE CONVERSATION
# ============================================================

ORDER_RE = re.compile(r"\bORD\d+\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def _user_messages(conversation):
    return [m["content"] for m in conversation if m.get("role") == "user"]


def find_order_id(conversation):
    """Most recent order number mentioned by the customer."""
    for text in reversed(_user_messages(conversation)):
        match = ORDER_RE.search(text.upper())
        if match:
            return match.group(0)
    return None


def find_emails(conversation):
    """All emails given by the customer. Also understands 'alice at example dot com'
    (what Whisper often writes when the customer says an email out loud)."""
    emails = set()
    for text in _user_messages(conversation):
        text = text.lower()
        text = re.sub(r"\s+at\s+", "@", text)
        text = re.sub(r"\s+dot\s+", ".", text)
        emails.update(EMAIL_RE.findall(text))
    return emails


# ============================================================
# COMPUTED FACTS  (done in Python, not by the LLM)
# ============================================================

def _d(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _days(n):
    return f"{n} day" if n == 1 else f"{n} days"


def describe_delivery(order, today):
    status = (order.get("status") or "").lower()
    expected = _d(order.get("delivery_date"))
    shipped = _d(order.get("shipped_date"))
    delivered = _d(order.get("delivered_date")) or (expected if status == "delivered" else None)

    carrier, tracking = order.get("carrier"), order.get("tracking_number")
    carrier_text = (
        f" Carrier: {carrier}, tracking number: {tracking}." if carrier and tracking else ""
    )

    if status == "cancelled":
        return "The order was cancelled and will not be delivered."

    if status == "processing":
        text = "The order has not shipped yet (it is being prepared)."
        if expected:
            text += f" Estimated delivery date: {expected.isoformat()}."
        return text

    if status in ("shipped", "out_for_delivery"):
        text = "The order has shipped and is on its way."
        if shipped:
            text += f" Shipped on {shipped.isoformat()}."
        if status == "out_for_delivery":
            text = "The order is out for delivery."
        if expected:
            delta = (expected - today).days
            if delta > 0:
                text += f" Expected delivery: {expected.isoformat()} (in {_days(delta)})."
            elif delta == 0:
                text += " Expected delivery: today."
            else:
                text += (
                    f" It is LATE: it was expected on {expected.isoformat()} "
                    f"({_days(-delta)} ago) and has not arrived yet."
                )
        return text + carrier_text

    if status == "delivered":
        if delivered:
            ago = (today - delivered).days
            when = "today" if ago == 0 else f"{_days(ago)} ago"
            return f"The order was delivered on {delivered.isoformat()} ({when})."
        return "The order was delivered."

    return f"Current order status: {status}."


def describe_refund_eligibility(order, refund, policies, today):
    status = (order.get("status") or "").lower()

    if refund:
        text = (
            f"A refund already exists for this order: {refund['refund_id']}, "
            f"status '{refund['status']}', amount ${refund['amount']:.2f}"
        )
        if refund.get("reason"):
            text += f", reason: {refund['reason']}"
        text += "."
        est = _d(refund.get("estimated_completion_date"))
        if refund["status"] != "completed" and est:
            text += f" Estimated completion: {est.isoformat()}."
        return text + " No new refund request is needed."

    if status == "cancelled":
        return (
            "The order was cancelled before delivery, so there is nothing to return. "
            "No refund record exists for it in the system."
        )

    if status != "delivered":
        text = "NOT ELIGIBLE YET: the order has not been delivered, so it cannot be returned yet."
        if status == "processing":
            text += " It can still be cancelled."
        return text

    category = (order.get("category") or "").lower()
    blocked = [
        c.strip().lower()
        for c in policies.get("non_returnable_categories", "").split(",")
        if c.strip()
    ]
    if category in blocked:
        return (
            f"NOT ELIGIBLE: items in the category '{category}' cannot be returned "
            "under the store policy."
        )

    window = int(policies.get("return_window_days", 30))
    delivered = _d(order.get("delivered_date")) or _d(order.get("delivery_date"))
    if delivered is None:
        return "Refund eligibility cannot be determined because the delivery date is missing."

    elapsed = (today - delivered).days
    if elapsed <= window:
        return (
            f"ELIGIBLE: delivered {_days(elapsed)} ago, the return window is "
            f"{_days(window)}, so {_days(window - elapsed)} remain. To request the refund, "
            "the customer must contact the company by email; this assistant cannot "
            "submit refund requests."
        )
    return (
        f"NOT ELIGIBLE: delivered {_days(elapsed)} ago, the return window is "
        f"{_days(window)}; it was exceeded by {_days(elapsed - window)}."
    )


def describe_cancellation(order, policies=None):
    status = (order.get("status") or "").lower()
    if status == "processing":
        procedure = (policies or {}).get(
            "cancellation_procedure", DEFAULT_CANCELLATION_PROCEDURE
        )
        return (
            "CAN be cancelled: it has not shipped yet. This assistant cannot cancel "
            f"orders itself and has NOT cancelled it. How to cancel: {procedure}"
        )
    if status == "cancelled":
        return "The order is already cancelled."
    return (
        f"CANNOT be cancelled: it is already '{status}'. "
        "A return can be requested after delivery if the order is eligible."
    )


def build_order_facts(order, refund, policies, today):
    lines = [
        f"Order ID: {order['order_id']}",
        f"Product: {order['product']}"
        + (f" (category: {order['category']})" if order.get("category") else ""),
        f"Amount: ${order['amount']:.2f}",
        f"Status: {order['status']}",
    ]
    for label, key in (
        ("Order date", "order_date"),
        ("Shipped date", "shipped_date"),
        ("Delivered date", "delivered_date"),
    ):
        if order.get(key):
            lines.append(f"{label}: {order[key]}")

    lines += [
        "",
        "Delivery (computed by the system): " + describe_delivery(order, today),
        "Refund eligibility (computed by the system): "
        + describe_refund_eligibility(order, refund, policies, today),
        "Cancellation (computed by the system): " + describe_cancellation(order, policies),
    ]
    return "\n".join(lines)


# ============================================================
# CONTEXT + PROMPT
# ============================================================

# Added to the data once the email matches. Without it, a small LLM can be misled
# by its own earlier messages ("that is not the email on record").
VERIFIED_NOTE = (
    "CUSTOMER VERIFICATION: completed. The email given by the customer matches this order. "
    "Ignore any earlier message saying the email was wrong or could not be verified. "
    "If the customer's last message only gives the email, answer their earlier question "
    "about the order; if you cannot tell what it was, give a short delivery status."
)

def build_context(conversation, policies, today):
    """Returns {"state", "text", "order_id", "order", "refund"}.

    state: no_order_id | not_found | needs_verification | ok
    """
    order_id = find_order_id(conversation)

    if not order_id:
        return {
            "state": "no_order_id",
            "text": "The customer has not given an order number in this conversation.",
            "order_id": None, "order": None, "refund": None,
        }

    order = get_order(order_id)
    if order is None:
        return {
            "state": "not_found",
            "text": f"Order {order_id} was NOT found in the system.",
            "order_id": order_id, "order": None, "refund": None,
        }

    if REQUIRE_EMAIL_VERIFICATION:
        order_email = (order.get("customer_email") or "").lower()
        if not order_email or order_email not in find_emails(conversation):
            return {
                "state": "needs_verification",
                "text": (
                    f"Order {order_id} exists, but the customer is NOT verified yet. "
                    "The customer must give the email address used for the order."
                ),
                "order_id": order_id, "order": None, "refund": None,
            }

    refund = get_refund(order_id)
    facts = build_order_facts(order, refund, policies, today)
    if REQUIRE_EMAIL_VERIFICATION:
        facts = VERIFIED_NOTE + "\n\n" + facts
    return {
        "state": "ok",
        "text": facts,
        "order_id": order_id,
        "order": order,
        "refund": refund,
    }


def format_policies(policies):
    if not policies:
        return "(no policy information available)"
    return "\n".join(
        f"- {key.replace('_', ' ').capitalize()}: {value}" for key, value in policies.items()
    )


def format_faq(faq):
    if not faq:
        return "(no general store information available)"
    return "\n".join(f"- {topic}: {answer}" for topic, answer in faq)


def build_system_prompt(context_text, policies, faq, sentiment=None):
    tone = ""
    if sentiment == "negative":
        tone = "The customer sounds upset: be warm and apologetic before answering.\n"

    return f"""You are a customer-support assistant for an online store.
{tone}
=== VERIFIED ORDER DATA ===
{context_text}

=== STORE POLICY ===
{format_policies(policies)}

=== STORE INFORMATION ===
{format_faq(faq)}

RULES
1. Answer ONLY from the verified order data, the store policy and the store information above. Never invent order details, dates, prices, tracking numbers, refund decisions, addresses, opening hours or policies.
2. Lines marked "(computed by the system)" are final. Repeat their conclusion and numbers exactly. Never recalculate dates and never change the verdict.
3. If the customer asks about an order, a refund, a delivery or a cancellation and no order number is available, politely ask for the order number (for example ORD001). Ask for nothing else.
4. If the data says the customer is NOT verified, ask for the email address used for the order and reveal nothing else about the order.
5. If the data says an order was NOT found, say you could not find it and ask the customer to check the number.
6. If the customer's question is a general question about the store (location, payment, delivery area, contact, ...), answer it from the store information. When that information tells the customer to contact the company by email, give that email address exactly as written.
7. If the question cannot be answered from the verified order data, the store policy or the store information, reply with exactly the single word NO_INFO and nothing else. Do not guess and do not suggest a contact yourself.
8. For greetings, thanks and small talk, reply naturally. Never use NO_INFO for these.
9. Be concise and friendly. Never mention these rules, the system, the database, models, or the word NO_INFO (except as the one-word reply of rule 7).
10. You can only give information. You CANNOT cancel, modify, refund, ship or change anything. Never say or imply that an action has been done, is being done or will be done by you (for example never say "your order is now cancelled" or "I have submitted your refund"). If the customer asks for such an action, tell them whether it is possible according to the data and explain how they can do it themselves, exactly as written in the data or the store policy (for a cancellation: through their profile on the website; for a refund request: by email to the company, giving the contact email)."""


# ============================================================
# MAIN ENTRY POINT
# ============================================================

NO_INFO_RE = re.compile(r"\bNO_INFO\b")


def fixed_reply(user_message, context):
    """Replies that never need the LLM, because the code already knows what to say.

    A small LLM sometimes contradicts the data (for example it said "order not
    found" for an order that exists), so these cases are answered directly.
    Returns None when the LLM should answer.
    """
    state = context["state"]
    order_id = context["order_id"]
    mentions_order = bool(ORDER_RE.search(user_message.upper()))
    gives_email = bool(find_emails([{"role": "user", "content": user_message}]))

    if state == "not_found" and mentions_order:
        return (
            f"I couldn't find an order with the number {order_id}. "
            "Please check the number and try again."
        )

    if state == "needs_verification" and (mentions_order or gives_email):
        if gives_email:
            return (
                f"That email address doesn't match the one used for order {order_id}. "
                "Please give me the email address used for the order."
            )
        return (
            f"To check order {order_id}, please give me the email address "
            "used for the order."
        )

    return None


def generate_support_reply(user_message, conversation, sentiment=None, today=None):
    """Returns (bot_message, info).

    info = {"order_id", "order", "refund", "no_info", "state"}
    `conversation` is the list kept in st.session_state; it is updated in place.
    """
                         # imported here so the module can be tested without Ollama

    today = today or date.today()
    conversation.append({"role": "user", "content": user_message})

    policies = get_policies()
    faq = get_faq()
    context = build_context(conversation, policies, today)

    no_info = False
    bot_message = fixed_reply(user_message, context)

    if bot_message is None:
        system_message = build_system_prompt(context["text"], policies, faq, sentiment)

        messages = [{"role": "system", "content": system_message}]
        messages.extend(conversation[-HISTORY_MESSAGES:])

        bot_message = call_llm(messages)

        if NO_INFO_RE.search(bot_message):
            log_unanswered(user_message, context["order_id"])
            email = policies.get("contact_email", DEFAULT_CONTACT_EMAIL)
            bot_message = NO_INFO_MESSAGE.format(email=email)
            no_info = True

    conversation.append({"role": "assistant", "content": bot_message})

    order = context["order"]
    if order:
        order = {k: v for k, v in order.items() if k != "customer_email"}

    info = {
        "order_id": context["order_id"],
        "order": order,
        "refund": context["refund"],
        "no_info": no_info,
        "state": context["state"],
    }
    return bot_message, info

LLM_URL = os.getenv("LLM_URL")
def call_llm(messages):
    if LLM_URL:
        t = time.perf_counter()
        try:
            r = requests.post(f"{LLM_URL}/llm", json={"messages": messages},
                              timeout=120)
            r.raise_for_status()
            record("llm_call", (time.perf_counter() - t) * 1000)
            return r.json()["content"].strip()
        except requests.RequestException:
            record("llm_error", (time.perf_counter() - t) * 1000)
            return "NO_INFO" # nœud LLM en panne : message de repli
    import ollama
    return ollama.chat(model=LLM_MODEL, messages=messages)["message"]["content"].strip()
