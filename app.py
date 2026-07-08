import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)

st.title("🤖 NRP Helper")
st.caption("Your friendly guide to the National Research Platform")
selected_model = st.sidebar.selectbox("Model", ["gpt-oss", "qwen3-small", "gemma"])
selected_temp = st.sidebar.slider("Temperature", 0.0, 1.5, 0.7)    

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful NRP support assistant. Be concise."}
    ]

# Show conversation so far
for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

# Get new user input
if prompt := st.chat_input("Ask about NRP..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""
        stream = client.chat.completions.create(
            model=selected_model,
            messages=st.session_state.messages,
            temperature = selected_temp,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            print(delta, end="")
            full += delta
            placeholder.markdown(full + "▌")
        placeholder.markdown(full)
    st.session_state.messages.append({"role": "assistant", "content": full})