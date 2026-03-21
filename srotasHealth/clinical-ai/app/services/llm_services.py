import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def call_llm(prompt: str) -> str:
    response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents = prompt
)
    return response.text

"""
if __name__ == "__main__":
    print(call_llm(""))
"""




"""
client = genai.Client(api_key='GEMINI_API_KEY')
response_1 = client.models.generate_content(
    model=MODEL_ID,
    contents='Hello',
)
client.close()
"""
