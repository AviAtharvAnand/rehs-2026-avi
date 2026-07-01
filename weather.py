# Setup — run this every time you open the notebook.
import os, json
from dotenv import load_dotenv
from openai import OpenAI
import urllib.request
import urllib.parse



# load_dotenv()  # reads your .env file

client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)

MODEL = "gpt-oss" 

def multiply(a, b):
    return a * b

# import asyncio, nest_asyncio
# import python_weather

# nest_asyncio.apply()  # lets us call async code from inside the notebook

# async def _fetch_weather(city):
#     async with python_weather.Client(unit=python_weather.IMPERIAL) as wclient:
#         w = await wclient.get(city)
#         return {
#             "city": city,
#             "temperature": w.temperature,
#             "feels_like": w.feels_like,
#             "description": w.description,
#             "humidity": w.humidity,
#             "wind_speed": w.wind_speed,
#         }

def get_weather(city):
    geo_url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + urllib.parse.urlencode({
            "name": city,
            "count": 1
        })
    )

    response = urllib.request.urlopen(geo_url)
    geo_data = json.loads(response.read().decode())

    place = geo_data["results"][0]
    lat = place["latitude"]
    lon = place["longitude"]

    weather_url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m",
            "temperature_unit": "fahrenheit"
        })
    )

    response = urllib.request.urlopen(weather_url)
    data = json.loads(response.read().decode())

    return data["current"]["temperature_2m"]

tools = [
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two numbers and return the exact result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city anywhere in the world.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "the city name, e.g. 'Tokyo'"},
                },
                "required": ["city"],
            },
        },
    },
]

# A lookup from tool name -> the real Python function.
available = {"multiply": multiply, "get_weather": get_weather}

def chat_with_tools(user_message):
    # Send a message; let the model call tools as many times as it needs.
    messages = [{"role": "user", "content": user_message}]
    while True:
        response = client.chat.completions.create(
            model="gpt-oss", messages=messages, tools=tools
        )
        msg = response.choices[0].message

        if not msg.tool_calls:        # model is done — return its answer
            return msg.content

        messages.append(msg)
        for call in msg.tool_calls:
            fn = available[call.function.name]
            args = json.loads(call.function.arguments)
            result = fn(**args)
            print("  [called %s(%s) -> %s]" % (call.function.name, args, result))
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def home():
    return "Weather app is running"

@app.route("/weather")
def weather():
    city = request.args.get("city", "Tokyo")
    return chat_with_tools(f"What's the weather in {city} right now?")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)