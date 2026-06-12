# hello_llm.py
import os
from dotenv import load_dotenv
from openai import OpenAI
model="minimax-m2"

load_dotenv()
client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)

print(f"Start chatting with the {model} (type 'e' to exit)")
while True:
    question = input("You: ")
    if question == "e":
        break
    response = client.chat.completions.create(
        model="minimax-m2",
        messages=[{"role": "user", "content": question}],
    )
    print(response.choices[0].message.content.lstrip("\n"))