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
    messages=[{"role": "user", 
        "content": "Three people A, B, and C each wear either a red or blue hat. They can see the others' \
        hats but not their own. They are told: At least one of you has a red hat.\
        A looks at B and C and says, I don’t know my hat color.\
        B then says, I don’t know my hat color.\
        C then says, I know my hat color.\
        What color is C’s hat, and why?"
    }],

    extra_body = {"reasoning_effort": "high"}
)

print(response.choices[0].message.content)
