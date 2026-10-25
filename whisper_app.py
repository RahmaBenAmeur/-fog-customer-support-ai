import streamlit as st

from whisper_service import transcribe_audio
from chatbot.whisper_pipeline import generate_response


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

if "last_audio_identifier" not in st.session_state:
    st.session_state.last_audio_identifier = None


# ============================================================
# FUNCTIONS
# ============================================================

def reset_conversation():

    st.session_state.messages = []

    st.session_state.conversation = []

    st.session_state.last_audio_identifier = None


def process_message(user_message, input_type):

    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
            "type": input_type,
        }
    )

    # --------------------------------------------------------
    # Generate response
    # --------------------------------------------------------

    response, analysis = generate_response(
        user_message,
        st.session_state.conversation,
    )

    # --------------------------------------------------------
    # Save assistant response
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "type": "text",
        }
    )

    return response, analysis


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

    st.caption(
        "Customer assistance"
    )

    st.write("")


    # --------------------------------------------------------
    # New conversation
    # --------------------------------------------------------

    if st.button(
        "＋  New conversation",
        key="new_conversation",
        use_container_width=True,
    ):

        reset_conversation()

        st.rerun()


    st.write("")

    st.caption("INPUT METHODS")


    # --------------------------------------------------------
    # Voice
    # --------------------------------------------------------

    st.info(
        "Voice input\n\n"
        "Record your message and Whisper "
        "will convert it to text."
    )


    # --------------------------------------------------------
    # Text
    # --------------------------------------------------------

    st.info(
        "Text input\n\n"
        "You can also type your message normally."
    )


    st.write("")

    st.caption("ASSISTANT")

    st.success("Online")

    st.caption(
        "Ready to handle voice or text requests."
    )


    st.write("")

    st.caption("POWERED BY")

    st.caption(
        "Whisper  •  Llama 3.2  •  SQLite  •  AI"
    )


# ============================================================
# TOP HEADER
# ============================================================

header_left, header_right = st.columns(
    [5.5, 1]
)

with header_left:

    st.title(
        "Customer Support"
    )

    st.caption(
        "Ask by voice or text — switch between them anytime."
    )


with header_right:

    st.success("Online")


# ============================================================
# EMPTY STATE
# ============================================================

if not st.session_state.messages:

    st.write("")

    with st.container(border=True):

        st.subheader(
            "How can we help?"
        )

        st.write(
            "You can type your question or record a voice message. "
            "Both methods use the same customer support assistant."
        )

        st.write("")

        voice_col, text_col = st.columns(2)


        with voice_col:

            st.caption(
                "VOICE"
            )

            st.write(
                "Record your request and Whisper "
                "will transcribe it automatically."
            )


        with text_col:

            st.caption(
                "TEXT"
            )

            st.write(
                "Type your request directly "
                "using the message box below."
            )


# ============================================================
# CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    role = message["role"]

    with st.chat_message(role):

        if role == "user":

            if message.get("type") == "voice":

                st.caption(
                    "Voice message"
                )

            else:

                st.caption(
                    "Text message"
                )

        st.markdown(
            message["content"]
        )


# ============================================================
# INPUT AREA
# ============================================================

st.write("")

st.divider()

st.subheader(
    "Send a message"
)

st.caption(
    "Choose voice or text. You can switch between them for every message."
)


# ============================================================
# TWO INPUT METHODS
# ============================================================

voice_col, text_col = st.columns(
    [1, 2]
)


# ============================================================
# VOICE INPUT
# ============================================================

with voice_col:

    st.caption(
        "VOICE"
    )

    audio_value = st.audio_input(
        "Record a message",
        key="voice_input",
    )


# ============================================================
# TEXT INPUT
# ============================================================

with text_col:

    st.caption(
        "TEXT"
    )

    text_message = st.chat_input(
        "Type your message..."
    )


# ============================================================
# VOICE PROCESSING
# ============================================================

if audio_value:

    audio_bytes = audio_value.getvalue()

    audio_identifier = hash(
        audio_bytes
    )


    # --------------------------------------------------------
    # Avoid processing the same recording twice
    # --------------------------------------------------------

    if (
        st.session_state.last_audio_identifier
        != audio_identifier
    ):

        st.session_state.last_audio_identifier = (
            audio_identifier
        )


        # ----------------------------------------------------
        # Whisper
        # ----------------------------------------------------

        with st.status(
            "Processing voice message...",
            expanded=True,
        ):

            st.write(
                "Transcribing with Whisper..."
            )

            try:

                user_message = transcribe_audio(
                    audio_bytes,
                    file_extension=".wav",
                )

            except TypeError:

                # Compatible with the older
                # transcribe_audio(audio_bytes)
                # version

                user_message = transcribe_audio(
                    audio_bytes
                )


            # ------------------------------------------------
            # Empty transcription
            # ------------------------------------------------

            if not user_message:

                st.warning(
                    "I couldn't understand the recording. "
                    "Please try again."
                )

                st.stop()


            st.write(
                "Transcription completed."
            )

            st.write(
                "Running the customer support pipeline..."
            )


            # ------------------------------------------------
            # Pipeline
            # ------------------------------------------------

            response, analysis = process_message(
                user_message,
                "voice",
            )


            st.write(
                "Response generated."
            )


        st.rerun()


# ============================================================
# TEXT PROCESSING
# ============================================================

if text_message:

    with st.status(
        "Processing your message...",
        expanded=True,
    ):

        st.write(
            "Running the customer support pipeline..."
        )

        response, analysis = process_message(
            text_message,
            "text",
        )

        st.write(
            "Response generated."
        )


    st.rerun()


# ============================================================
# LAST ANALYSIS / ORDER DETAILS
# ============================================================

if st.session_state.messages:

    # --------------------------------------------------------
    # Find last assistant response
    # --------------------------------------------------------

    last_assistant_index = None

    for i in range(
        len(st.session_state.messages) - 1,
        -1,
        -1,
    ):

        if (
            st.session_state.messages[i]["role"]
            == "assistant"
        ):

            last_assistant_index = i

            break


    # --------------------------------------------------------
    # Only display details if we have
    # a current analysis
    # --------------------------------------------------------

    if "analysis" in locals():

        st.write("")

        # ----------------------------------------------------
        # AI analysis
        # ----------------------------------------------------

        with st.container(border=True):

            st.subheader(
                "Request analysis"
            )

            analysis_col1, analysis_col2, analysis_col3 = (
                st.columns(3)
            )


            with analysis_col1:

                st.caption(
                    "INTENT"
                )

                st.write(
                    analysis.get(
                        "intent",
                        "Unknown",
                    )
                )


            with analysis_col2:

                st.caption(
                    "SENTIMENT"
                )

                st.write(
                    analysis.get(
                        "sentiment",
                        "Unknown",
                    ).capitalize()
                )


            with analysis_col3:

                st.caption(
                    "PRIORITY"
                )

                st.write(
                    analysis.get(
                        "priority",
                        "Unknown",
                    )
                )


        # ----------------------------------------------------
        # Order information
        # ----------------------------------------------------

        order = analysis.get(
            "order"
        )


        if order:

            st.write("")

            with st.container(border=True):

                st.subheader(
                    "Order details"
                )

                st.caption(
                    f"Information retrieved for "
                    f"{order['order_id']}"
                )

                st.write("")


                detail1, detail2, detail3 = (
                    st.columns(3)
                )


                with detail1:

                    st.caption(
                        "ORDER"
                    )

                    st.write(
                        order["order_id"]
                    )


                with detail2:

                    st.caption(
                        "STATUS"
                    )

                    st.write(
                        order["status"].capitalize()
                    )


                with detail3:

                    st.caption(
                        "AMOUNT"
                    )

                    st.write(
                        f"${order['amount']:.2f}"
                    )


                st.divider()


                product_col, date_col = (
                    st.columns(2)
                )


                with product_col:

                    st.caption(
                        "PRODUCT"
                    )

                    st.write(
                        order["product"]
                    )


                with date_col:

                    st.caption(
                        "DELIVERY DATE"
                    )

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
        "Voice + Text • Whisper • Llama 3.2"
    )