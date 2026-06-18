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
from rich.markdown import Markdown
from rich.console import Console
from rich.live import Live

console = Console()
MODEL = "gpt-oss"

load_dotenv()
client = OpenAI(
    api_key = os.environ["NRP_LLM_TOKEN"],
    base_url = os.environ["NRP_LLM_BASE_URL"]
)


print(Panel("[blue]NRP chat. Press e to exit"), end = '')

with open('history.json', 'r') as f:
    history = json.load(f)

while True:
    hist = ''
    question = input("\nYou: ")
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
        messages = history,
        stream = True
    )

    with Live(Panel(Markdown(hist)), console = console, refresh_per_second = 10) as live:
        for chunk in response: 
            if chunk.choices and len(chunk.choices) > 0:
                delta = getattr(chunk.choices[0], 'delta', None)
                content = getattr(delta, 'content', None)
                if content:
                    hist += content
                    live.update(Panel(Markdown(hist)))
    history.append({"role": "assistant", "content": hist})






