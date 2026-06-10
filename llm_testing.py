import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)
response = client.chat.completions.create(
    model="qwen3",
    messages=[
        {"role": "user", 
        
            "content": [
                {
                    "type": "text",
                    "text": "Describe the image provided in 20 words or less. \
                    'image_url': 'https://stellwagen.noaa.gov/media/img/20210810-breach-behavior-1000.jpg'"
                },
            ]
        }
    
    ],
)


print(response.choices[0].message.content)
