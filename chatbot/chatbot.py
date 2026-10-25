import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
import ollama
import joblib

from transformers import pipeline

from database.database import get_order, get_refund
from database.extractor import extract_order_id


# =========================
# Load AI models
# =========================

SENTIMENT_MODEL_PATH = "Sentiment_Classification/amazon_distilbert"
INTENT_MODEL_PATH = "Intent_Classification/intent_classifier.pkl"

print("Loading sentiment model...")

sentiment_model = pipeline(
    "sentiment-analysis",
    model=SENTIMENT_MODEL_PATH,
    tokenizer=SENTIMENT_MODEL_PATH
)

print("Loading intent model...")

intent_model = joblib.load(INTENT_MODEL_PATH)


# =========================
# Start chatbot
# =========================

print("\n🤖 Customer Support Chatbot")
print("Type 'exit' to quit.\n")

conversation = []


while True:

    user_message = input("You: ")

    if user_message.lower() == "exit":
        print("Goodbye!")
        break


    # =========================
    # Sentiment
    # =========================

    sentiment_result = sentiment_model(user_message)[0]

    sentiment = sentiment_result["label"]
    sentiment_confidence = sentiment_result["score"]


    # =========================
    # Intent
    # =========================

    intent = intent_model.predict([user_message])[0]

    intent_probabilities = intent_model.predict_proba([user_message])[0]

    intent_confidence = max(intent_probabilities)


    # =========================
    # Order ID extraction
    # =========================

    order_id = extract_order_id(user_message)

    order_information = None
    refund_information = None


    if order_id:

        print(f"🔎 Order detected: {order_id}")

        order_information = get_order(order_id)

        if order_information:

            print(
                f"📦 Order status: "
                f"{order_information['status']}"
            )

            print(
                f"📅 Delivery date: "
                f"{order_information['delivery_date']}"
            )

            # Check refund information
            refund_information = get_refund(order_id)

            if refund_information:
                print(
                    f"💰 Refund status: "
                    f"{refund_information['status']}"
                )

        else:

            print("⚠️ Order not found in database.")


    # =========================
    # Display AI analysis
    # =========================

    print(
        f"📊 Sentiment: "
        f"{sentiment} ({sentiment_confidence:.2f})"
    )

    print(
        f"🎯 Intent: "
        f"{intent} ({intent_confidence:.2f})"
    )


    # =========================
    # Intent information
    # =========================

    if intent_confidence >= 0.50:

        intent_information = (
            f"The detected intent is '{intent}' "
            f"with confidence {intent_confidence:.2f}."
        )

    else:

        intent_information = (
            f"The classifier predicted '{intent}', "
            f"but confidence is only "
            f"{intent_confidence:.2f}. "
            f"Treat this intent as uncertain."
        )


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
    # Conversation memory
    # =========================

    conversation.append({
        "role": "user",
        "content": user_message
    })


    # =========================
    # LLM prompt
    # =========================

    system_message = f"""
You are a helpful customer support assistant.

Customer sentiment:
{sentiment} (confidence {sentiment_confidence:.2f})

Intent analysis:
{intent_information}

Database information:
{database_information}

Rules:

1. Use the database information when available.
2. Never invent order or refund information.
3. If an order was not found, say that you could not find it.
4. Do not mention internal AI models or confidence scores.
5. If the intent is uncertain, rely on the customer's actual message.
6. If the customer is frustrated, respond empathetically.
7. Keep responses concise and useful.
"""


    messages = [
        {
            "role": "system",
            "content": system_message
        }
    ]

    messages.extend(conversation)


    # =========================
    # Generate response
    # =========================

    response = ollama.chat(
        model="llama3.1:8b",
        messages=messages
    )

    bot_message = response["message"]["content"]


    # =========================
    # Save conversation
    # =========================

    conversation.append({
        "role": "assistant",
        "content": bot_message
    })


    print(f"Bot: {bot_message}\n")