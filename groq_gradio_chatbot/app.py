import random
import gradio as gr
import os
from groq import Groq


client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


def random_response(message, history):
    chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": message,
        }
    ],
    model="meta-llama/llama-4-maverick-17b-128e-instruct",
)
    return chat_completion.choices[0].message.content

demo = gr.ChatInterface(random_response, type="messages", autofocus=True)

if __name__ == "__main__":
    demo.launch()