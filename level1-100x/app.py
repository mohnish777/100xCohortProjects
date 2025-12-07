import random
import os
import time
import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, APIError

load_dotenv()  # take environment variables

client = OpenAI()



def random_response(message, history):
    
    try:
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": message
                }
            ]
        )
        return completion.choices[0].message.content

    except AuthenticationError:
        return "Authentication error: Please check if your API key is valid and has the correct permissions."
    except RateLimitError:
        return "Rate limit error: Your API key might be rate limited or have insufficient quota. Please check your OpenAI account."
    except APIError as e:
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

demo = gr.ChatInterface(random_response, type="messages", autofocus=False)

if __name__ == "__main__":
    demo.launch()
