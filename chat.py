"""
Create history.json to store the conversation history and
add [{"role": "system", "content": "normal"}] to 
history.json before running this code for the first time.
"""
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from rich import print
from rich.panel import Panel

MODEL = "gpt-oss"

load_dotenv()
client = OpenAI(
    api_key = os.environ["NRP_LLM_TOKEN"],
    base_url = os.environ["NRP_LLM_BASE_URL"]
)


print(Panel("[blue]NRP chat. Press e to exit"))

with open('history.json', 'r') as f:
    history = json.load(f)

while True:
    question = input("You: ")
    print()
    user_input = {"role": "user", "content": question}
    history.append(user_input)
    if question == "e":
        with open('history.json', 'w') as f:
            json.dump(history, f)
        print(Panel("[green]Bye!"))
        break

    response = client.chat.completions.create(
        model = MODEL,
        messages = history
    )
    reply = {"role": "assistant", "content": response.choices[0].message.content}
    history.append(reply)

    print(Panel(f"[green]{MODEL}: {response.choices[0].message.content}"))
    print()



