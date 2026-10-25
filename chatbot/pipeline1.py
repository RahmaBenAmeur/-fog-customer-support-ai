"""
chatbot/pipeline1.py  -  used by app.py (text only).

All the logic lives in chatbot/support_context.py.
To change the LLM model or the email verification, edit the settings at the top
of that file.
"""

import sys
from pathlib import Path

# Allow imports from project root
sys.path.append(str(Path(__file__).resolve().parent.parent))

from chatbot.support_context import generate_support_reply


def generate_response(user_message, conversation):

    bot_message, info = generate_support_reply(
        user_message,
        conversation,
    )

    # info = {"order_id", "order", "refund", "escalated", "state"}
    return bot_message, info
