import os
from dotenv import load_dotenv
from google import genai
import re
import json

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None


def get_client():
    global client
    if client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY must be set before calling the LLM.")
        client = genai.Client(api_key=GEMINI_API_KEY)
    return client

def call_llm(prompt: str) -> str:
    response = get_client().models.generate_content(
    model="gemini-2.5-flash",
    contents = prompt)

    return response.text

def extract_with_retry(prompt, max_retries=2):
    for i in range(max_retries):
        try:
            response = call_llm(prompt)
            parsed = extract_json(response)
            if validate_criteria(parsed) and (
                parsed.get("inclusion_criteria") or parsed.get("exclusion_criteria")):
                return parsed
            
        except Exception as e:
            if i == max_retries - 1:
                return {"inclusion_criteria": [], "exclusion_criteria": []}
            print(f"Retrying after error: {e}")

    # NEW: if we get here, we never returned inside the loop
    print("prompt")
    return {"inclusion_criteria": [], "exclusion_criteria": []}
            


def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}

def validate_criteria(data):
    print("inclusion:",isinstance(data.get("inclusion_criteria"), list))
    print("exclusion:", isinstance(data.get("exclusion_criteria"), list))
    return (
        isinstance(data.get("inclusion_criteria"), list) and
        isinstance(data.get("exclusion_criteria"), list)
    )
