import sys
from pathlib import Path

# Allow imports from project root
sys.path.append(str(Path(__file__).resolve().parent.parent))

import ollama

from database.database import get_order, get_refund
from database.extractor import extract_order_id


# =========================
# Generate response
# =========================

def generate_response(user_message, conversation):

    # =========================
    # Extract order ID
    # =========================

    order_id = extract_order_id(user_message)

    order_information = None
    refund_information = None

    if order_id:

        order_information = get_order(order_id)

        if order_information:
            refund_information = get_refund(order_id)


    # =========================
    # Database information
    # =========================

    database_information = "No order information was found."

    if order_information:

        database_information = f"""
Order information:

Order ID: {order_information['order_id']}
Customer ID: {order_information['customer_id']}
Product: {order_information['product']}
Status: {order_information['status']}
Delivery date: {order_information['delivery_date']}
Amount: ${order_information['amount']:.2f}
"""

        if refund_information:

            database_information += f"""
Refund information:

Refund ID: {refund_information['refund_id']}
Refund status: {refund_information['status']}
Refund amount: ${refund_information['amount']:.2f}
"""


    # =========================
    # Add conversation
    # =========================

    conversation.append({
        "role": "user",
        "content": user_message
    })


    # =========================
    # System prompt
    # =========================

    system_message = f"""
You are a helpful customer support assistant.

Customer message:
{user_message}

Database information:
{database_information}

Rules:

1. Understand the customer's request yourself.
2. You may infer their intent and sentiment from their message.
3. Use database information when available.
4. Never invent order or refund information.
5. If an order was not found, say that you could not find it.
6. Do not mention internal system details.
7. Respond empathetically when the customer is frustrated.
8. Keep responses concise and useful.
"""


    # =========================
    # Messages for Ollama
    # =========================

    messages = [
        {
            "role": "system",
            "content": system_message
        }
    ]

    # Keep recent conversation only
    messages.extend(conversation[-6:])


    # =========================
    # LLM
    # =========================

    response = ollama.chat(
        model="llama3.2:3b",
        messages=messages
    )

    bot_message = response["message"]["content"]


    # =========================
    # Save response
    # =========================

    conversation.append({
        "role": "assistant",
        "content": bot_message
    })


    # =========================
    # Analysis information
    # =========================

    analysis = {
        "order_id": order_id,
        "order": order_information,
        "refund": refund_information
    }

    return bot_message, analysis