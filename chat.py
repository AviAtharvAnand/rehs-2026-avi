import os
from dotenv import load_dotenv
from openai import OpenAI
MODEL = "gpt-oss"

load_dotenv()
client = OpenAI(
    api_key = os.environ["NRP_LLM_TOKEN"],
    base_url = os.environ["NRP_LLM_BASE_URL"]
)

print("NRP chat. Press e to exit\n")

history = [
        {"role": "system", "content": "normal"},
    ]

while True:
    question = input("You: ")
    print()
    user_input = {"role": "user", "content": question}
    history.append(user_input)
    if question == "e":
        print("Bye!")
        break

    response = client.chat.completions.create(
        model = MODEL,
        messages = history
    )
    reply = {"role": "user", "content": response.choices[0].message.content}
    history.append(reply)

    print(f"{MODEL}: {response.choices[0].message.content}")
    print()