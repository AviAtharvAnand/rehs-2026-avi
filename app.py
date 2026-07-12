import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ["NRP_LLM_TOKEN"],
                base_url=os.environ.get("NRP_LLM_BASE_URL", "https://ellm.nrp-nautilus.io/v1"))

st.set_page_config(page_title="NRP Helper", page_icon="🤖")
st.title("🤖 NRP Helper")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful, concise NRP support assistant."},
    ]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

def token_stream(messages):
    stream = client.chat.completions.create(model="gemma", messages=messages, stream=True)
    for chunk in stream:
        if not chunk.choices:              # last chunk = usage only
            continue
        yield chunk.choices[0].delta.content or ""

if prompt := st.chat_input("Ask about NRP..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        answer = st.write_stream(token_stream(st.session_state.messages))
    st.session_state.messages.append({"role": "assistant", "content": answer})
