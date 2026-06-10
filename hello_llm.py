# hello_llm.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)

models = ["gpt-oss", "qwen3-small", "gemma"]
questions = [
    "What is the National Research Platform in 10 words or less?",
    "What are you in 10 words or less?",
    "What is the difference between neutrophils and macrophages in 10 words or less?",
    "Describe why one would use the NRP in 10 words or less?",
    "What is the most popular fruit in 10 words or less?",
]

for model in models:
    print(f"\n=== Model: {model} ===")
    for question in questions:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}],
        )
        answer = response.choices[0].message.content
        print(f"Q: {question}\nA: {answer}\n")
