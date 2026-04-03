from app.services.llm_services import call_llm
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import os
import uuid
load_dotenv()


def generate_summary_llm(agent_result):
    prompt = f"""
    Summarize this in a professional medical tone:

    {agent_result}
    """
    return call_llm(prompt)


def generate_summary(agent_result):
    top = agent_result["top_matches"]

    if not top:
        return "No eligible patients found for this trial."

    best = top[0]

    return f"""
        We found {len(top)} eligible patients.

        The best match has a score of {best['score']} percent.

        Key reasons include:
        {", ".join(best['reasons'][:2])}
        """


def text_to_speech(text):

    elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    )

    audio_stream = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",  # "George" - browse voices at elevenlabs.io/app/voice-library
        model_id="eleven_v3",
        output_format="mp3_44100_128",
    )

    # 2. Convert the generator to a single bytes object so we can use it twice
    # IMPORTANT: Once you iterate through audio_stream, it is "consumed"
    audio_data = b"".join(audio_stream)

    folder_name = "my_audio_files"
    os.makedirs(folder_name, exist_ok=True)
    filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(folder_name, filename)
    
    with open(file_path, "wb") as f:
        f.write(audio_data)

    return f"/media/{filename}"
