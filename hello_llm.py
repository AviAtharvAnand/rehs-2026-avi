# hello_llm.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)
response = client.chat.completions.create(
    model="gpt-oss",
    messages=[{"role": "user", "content": "What is the National Research Platform?"}],
)
print(response.choices[0].message.content)