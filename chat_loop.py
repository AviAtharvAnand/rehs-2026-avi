# hello_llm.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)

while True:
    question = input("Ask a question (or 'exit' to quit): ")
    if question == "exit":
        break
    response = client.chat.completions.create(
        model="minimax-m2",
        messages=[{"role": "user", "content": question}],
    )
    print("LLM: " + response.choices[0].message.content + "\n")