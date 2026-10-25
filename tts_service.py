import edge_tts
import asyncio
import tempfile


VOICE = "en-US-AriaNeural"


async def generate_audio(text, output_path):

    communicate = edge_tts.Communicate(
        text,
        VOICE
    )

    await communicate.save(output_path)


def text_to_speech(text):

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )

    audio_path = temp_file.name
    temp_file.close()

    asyncio.run(
        generate_audio(
            text,
            audio_path
        )
    )

    return audio_path