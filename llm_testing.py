import os
from dotenv import load_dotenv
from openai import OpenAI

MODEL = ['gpt-oss', 'gemma-small', 'qwen3-small']

load_dotenv()
client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)
for i in range(len(MODEL)):
    try:
        response = client.chat.completions.create(model=MODEL[i], messages=[{"role": "user", "content": "Hello"}])
    except Exception as e:
        print(f"Something went wrong!")

    print(response.choices[0].message.content)
