from faster_whisper import WhisperModel
import tempfile
import os

from transcript_cleanup import normalize_transcript


# ============================================================
# WHISPER MODEL
# ============================================================

print("Loading Whisper model...")

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("Whisper loaded successfully!")


# ============================================================
# TRANSCRIPTION
# ============================================================

def transcribe_audio(
    audio_bytes,
    file_extension=".webm"
):

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=file_extension
    ) as temp_audio:

        temp_audio.write(audio_bytes)

        audio_path = temp_audio.name


    try:

        segments, info = model.transcribe(
            audio_path,
            beam_size=5
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
        )

        # "ORD 001" -> "ORD001", "alice at example dot com" -> "alice@example.com"
        return normalize_transcript(text.strip())


    finally:

        if os.path.exists(audio_path):
            os.remove(audio_path)
