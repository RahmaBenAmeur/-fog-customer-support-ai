import streamlit as st
from chatbot.pipeline1 import generate_response


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Customer Support",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation" not in st.session_state:
    st.session_state.conversation = []

if "quick_message" not in st.session_state:
    st.session_state.quick_message = None


# ============================================================
# FUNCTIONS
# ============================================================

def reset_conversation():
    st.session_state.messages = []
    st.session_state.conversation = []
    st.session_state.quick_message = None


def ask(message):
    st.session_state.quick_message = message


# ============================================================
# LIGHT NATIVE STREAMLIT STYLING
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #f6f8fb;
    }

    .block-container {
        max-width: 1180px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #cbd5e1;
    }

    [data-testid="stSidebar"] .stButton button {
        background-color: #1f2937;
        border: 1px solid #374151;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #273449;
        border-color: #64748b;
    }

    .stButton button {
        border-radius: 9px;
        min-height: 40px;
        font-weight: 500;
    }

    [data-testid="stChatMessage"] {
        border-radius: 14px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## Support")

    st.caption("Customer assistance")

    st.write("")

    # New conversation
    if st.button(
        "＋  New conversation",
        key="new_conversation",
        use_container_width=True,
    ):
        reset_conversation()
        st.rerun()

    st.write("")

    st.caption("QUICK ACTIONS")

    if st.button(
        "▣  Track an order",
        key="sidebar_track",
        use_container_width=True,
    ):
        ask("Where is my order ORD001?")
        st.rerun()

    if st.button(
        "↻  Check a refund",
        key="sidebar_refund",
        use_container_width=True,
    ):
        ask("What is the status of my refund for ORD002?")
        st.rerun()

    if st.button(
        "→  Delivery options",
        key="sidebar_delivery",
        use_container_width=True,
    ):
        ask("What are the delivery options?")
        st.rerun()

    st.write("")
    st.write("")

    st.caption("ASSISTANT")

    st.success("Online")

    st.caption(
        "Ready to help with orders, refunds and deliveries."
    )

    st.write("")

    st.caption("POWERED BY")

    st.caption(
        "Llama 3.2  •  SQLite  •  AI"
    )


# ============================================================
# TOP HEADER
# ============================================================

header_left, header_right = st.columns(
    [5.5, 1]
)

with header_left:

    st.title("Customer Support")

    st.caption(
        "Fast answers about your orders, refunds and deliveries."
    )

with header_right:

    st.success("Online")


# ============================================================
# ACTIVE CONVERSATION
# ============================================================

if st.session_state.messages:

    # --------------------------------------------------------
    # Conversation header
    # --------------------------------------------------------

    st.divider()

    conversation_col1, conversation_col2 = st.columns(
        [5, 1]
    )

    with conversation_col1:

        st.subheader("Conversation")

        st.caption(
            "Your messages are handled by the support assistant."
        )

    with conversation_col2:

        if st.button(
            "Clear",
            key="clear_chat",
            use_container_width=True,
        ):
            reset_conversation()
            st.rerun()


# ============================================================
# EMPTY STATE
# ============================================================

else:

    st.write("")

    # Main introduction
    with st.container(border=True):

        st.subheader(
            "How can we help?"
        )

        st.write(
            "Tell us what you need and we'll look into it. "
            "You can ask about an existing order, a refund, "
            "delivery, or another support question."
        )

        st.write("")


    st.write("")


    # --------------------------------------------------------
    # SERVICE CARDS
    # --------------------------------------------------------

    st.caption("WHAT DO YOU NEED HELP WITH?")

    card1, card2, card3 = st.columns(3)


    # Orders
    with card1:

        with st.container(border=True):

            st.subheader("▣  Orders")

            st.caption(
                "Track an order, check its status or find "
                "information about a purchase."
            )

            st.write("")

            if st.button(
                "Track an order",
                key="card_track",
                use_container_width=True,
            ):
                ask("Where is my order ORD001?")
                st.rerun()


    # Refunds
    with card2:

        with st.container(border=True):

            st.subheader("↻  Refunds")

            st.caption(
                "Check whether your refund has been processed "
                "and view its current status."
            )

            st.write("")

            if st.button(
                "Check a refund",
                key="card_refund",
                use_container_width=True,
            ):
                ask(
                    "What is the status of my refund for ORD002?"
                )
                st.rerun()


    # Delivery
    with card3:

        with st.container(border=True):

            st.subheader("→  Delivery")

            st.caption(
                "Find out about delivery options and "
                "information related to your order."
            )

            st.write("")

            if st.button(
                "Delivery options",
                key="card_delivery",
                use_container_width=True,
            ):
                ask(
                    "What are the delivery options?"
                )
                st.rerun()


    st.write("")
    st.write("")


    # --------------------------------------------------------
    # EXAMPLE QUESTIONS
    # --------------------------------------------------------

    st.caption("EXAMPLE QUESTIONS")

    example_col1, example_col2 = st.columns(2)


    with example_col1:

        if st.button(
            '"Where is my order ORD001?"',
            key="example_1",
            use_container_width=True,
        ):
            ask("Where is my order ORD001?")
            st.rerun()

        if st.button(
            '"Can I get a refund for my order?"',
            key="example_2",
            use_container_width=True,
        ):
            ask("Can I get a refund for my order?")
            st.rerun()


    with example_col2:

        if st.button(
            '"What is the status of ORD002?"',
            key="example_3",
            use_container_width=True,
        ):
            ask("What is the status of ORD002?")
            st.rerun()

        if st.button(
            '"What delivery options do you offer?"',
            key="example_4",
            use_container_width=True,
        ):
            ask("What delivery options do you offer?")
            st.rerun()


# ============================================================
# CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    role = message["role"]

    with st.chat_message(role):

        st.markdown(
            message["content"]
        )


# ============================================================
# USER INPUT
# ============================================================

user_message = st.chat_input(
    "Ask something about your order..."
)


# ============================================================
# QUICK ACTION INPUT
# ============================================================

if st.session_state.quick_message:

    user_message = st.session_state.quick_message

    st.session_state.quick_message = None


# ============================================================
# PROCESS MESSAGE
# ============================================================

if user_message:

    # --------------------------------------------------------
    # USER MESSAGE
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    with st.chat_message("user"):

        st.markdown(user_message)


    # --------------------------------------------------------
    # AI RESPONSE
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "Checking your request..."
        ):

            response, analysis = generate_response(
                user_message,
                st.session_state.conversation,
            )

        st.markdown(response)


    # Save assistant response

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
        }
    )


    # ========================================================
    # ORDER INFORMATION
    # ========================================================

    order = analysis.get("order")


    if order:

        st.write("")

        with st.container(border=True):

            st.subheader("Order details")

            st.caption(
                f"Information retrieved for {order['order_id']}"
            )

            st.write("")

            detail1, detail2, detail3 = st.columns(3)


            with detail1:

                st.caption("ORDER")

                st.write(
                    order["order_id"]
                )


            with detail2:

                st.caption("STATUS")

                st.write(
                    order["status"].capitalize()
                )


            with detail3:

                st.caption("AMOUNT")

                st.write(
                    f"${order['amount']:.2f}"
                )


            st.divider()


            product_col, date_col = st.columns(2)


            with product_col:

                st.caption("PRODUCT")

                st.write(
                    order["product"]
                )


            with date_col:

                st.caption("DELIVERY DATE")

                st.write(
                    order["delivery_date"]
                )


# ============================================================
# FOOTER
# ============================================================

st.write("")

st.divider()

footer_left, footer_right = st.columns(2)

with footer_left:

    st.caption(
        "Customer Support Assistant"
    )

with footer_right:

    st.caption(
        "AI-powered support"
    )