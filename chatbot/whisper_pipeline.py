"""
chatbot/whisper_pipeline.py  -  used by whisper_app.py (voice + text).

Steps for each message:
  1. intent + sentiment + priority   (the three small models, shown in the UI)
  2. support logic + LLM answer      (chatbot/support_context.py)

To change the LLM model or the email verification, edit the settings at the top
of chatbot/support_context.py.
"""

import sys
from pathlib import Path

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(PROJECT_ROOT))


# ============================================================
# IMPORTS
# ============================================================

import joblib
import torch

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)

from chatbot.support_context import generate_support_reply


# ============================================================
# MODEL PATHS
# ============================================================

INTENT_MODEL_PATH = (
    PROJECT_ROOT
    / "Intent_Classification"
    / "intent_classifier.pkl"
)

SENTIMENT_MODEL_PATH = (
    PROJECT_ROOT
    / "Sentiment_Classification"
    / "amazon_distilbert"
)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print(f"AI Pipeline device: {DEVICE}")


# ============================================================
# LOAD INTENT CLASSIFIER
# ============================================================

print("Loading intent classifier...")

intent_model = joblib.load(
    INTENT_MODEL_PATH
)

print("Intent classifier loaded successfully.")


# ============================================================
# LOAD SENTIMENT MODEL
# ============================================================

print("Loading sentiment model...")

sentiment_tokenizer = AutoTokenizer.from_pretrained(
    SENTIMENT_MODEL_PATH,
    local_files_only=True
)

sentiment_model = AutoModelForSequenceClassification.from_pretrained(
    SENTIMENT_MODEL_PATH,
    local_files_only=True
)

sentiment_model.to(DEVICE)
sentiment_model.eval()

print("Sentiment model loaded successfully.")


# ============================================================
# INTENT PREDICTION
# ============================================================

def predict_intent(text):

    prediction = intent_model.predict(
        [text]
    )[0]

    confidence = None

    try:

        probabilities = intent_model.predict_proba(
            [text]
        )[0]

        confidence = float(
            probabilities.max()
        )

    except Exception:
        pass

    return prediction, confidence


# ============================================================
# SENTIMENT PREDICTION
# ============================================================

def predict_sentiment(text):

    inputs = sentiment_tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=128
    )

    inputs = {
        key: value.to(DEVICE)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        outputs = sentiment_model(
            **inputs
        )

        probabilities = torch.softmax(
            outputs.logits,
            dim=-1
        )

    prediction = torch.argmax(
        probabilities,
        dim=-1
    ).item()

    confidence = probabilities[
        0
    ][prediction].item()

    sentiment = sentiment_model.config.id2label[
        prediction
    ]

    return sentiment, confidence


# ============================================================
# PRIORITY
# ============================================================

HIGH_INTENTS = {
    "complaint",
    "payment_issue",
    "get_refund",
    "track_refund",
    "cancel_order",
    "contact_human_agent",
    "contact_customer_service"
}


MEDIUM_INTENTS = {
    "track_order",
    "change_shipping_address",
    "change_order",
    "delivery_period",
    "delivery_options",
    "check_cancellation_fee"
}


def calculate_priority(intent, sentiment):

    if intent in HIGH_INTENTS:

        priority = 3

    elif intent in MEDIUM_INTENTS:

        priority = 2

    else:

        priority = 1


    # Negative sentiment increases priority

    if sentiment == "negative":

        priority = min(
            priority + 1,
            3
        )


    priority_labels = {
        1: "LOW",
        2: "MEDIUM",
        3: "HIGH"
    }

    return priority_labels[
        priority
    ]


# ============================================================
# MESSAGE ANALYSIS
# ============================================================

def analyze_message(text):

    intent, intent_confidence = (
        predict_intent(text)
    )

    sentiment, sentiment_confidence = (
        predict_sentiment(text)
    )

    priority = calculate_priority(
        intent,
        sentiment
    )

    return {
        "intent": intent,

        "intent_confidence": (
            round(
                intent_confidence,
                4
            )
            if intent_confidence is not None
            else None
        ),

        "sentiment": sentiment,

        "sentiment_confidence": round(
            sentiment_confidence,
            4
        ),

        "priority": priority
    }


# ============================================================
# MAIN PIPELINE
# ============================================================

def generate_response(
    user_message,
    conversation
):

    print("\n================================")
    print("AI PIPELINE")
    print("================================")


    # 1. INTENT + SENTIMENT + PRIORITY

    analysis = analyze_message(
        user_message
    )

    print(f"Intent: {analysis['intent']}")
    print(f"Intent confidence: {analysis['intent_confidence']}")
    print(f"Sentiment: {analysis['sentiment']}")
    print(f"Sentiment confidence: {analysis['sentiment_confidence']}")
    print(f"Priority: {analysis['priority']}")


    # 2. SUPPORT LOGIC + LLM
    #    (the intent is NOT sent to the LLM: the classifier is not reliable
    #     enough, and the order data decides the answer. The sentiment is
    #     only used to set the tone.)

    print("Generating response...")

    bot_message, info = generate_support_reply(
        user_message,
        conversation,
        sentiment=analysis["sentiment"]
    )

    print(f"Assistant: {bot_message}")


    # 3. COMPLETE ANALYSIS FOR THE UI
    #    adds: order_id, order, refund, escalated, state

    analysis.update(info)

    print("================================")
    print("PIPELINE COMPLETE")
    print("================================")

    return bot_message, analysis
