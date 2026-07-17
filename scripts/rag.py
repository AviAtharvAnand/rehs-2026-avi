import os
import streamlit as st
from search import search
from dotenv import load_dotenv
from openai import OpenAI
from openai import BadRequestError
import time

load_dotenv()
client = OpenAI(api_key=os.environ["NRP_LLM_TOKEN"],
                base_url=os.environ.get("NRP_LLM_BASE_URL", "https://ellm.nrp-nautilus.io/v1"))

st.set_page_config(page_title="NRP Helper", page_icon="🤖")
st.title("🤖 NRP Helper")

with st.sidebar:
    st.header("Settings")
    if st.button("🗑️ Clear chat"):
        st.session_state.pop("messages", None)
        st.rerun()

system_prompt ={
            "role": "system", "content": 
            """
                You are an NRP documentation assistant.

                You answer ONLY from the documentation provided in the user's message.

                Never use prior knowledge.
                Never guess.
                Never infer.
                Never add information that is not explicitly stated in the documentation.
                If the documentation does not contain the answer, say:
                "The provided documentation does not contain enough information to answer this question."
            """
            }

if "messages" not in st.session_state:
    st.session_state.messages = [system_prompt]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

# def token_stream(messages):
#     stream = client.chat.completions.create(model="gpt-oss", messages=messages, stream=True)
#     for chunk in stream:
#         if not chunk.choices:              # last chunk = usage only
#             continue
#         yield chunk.choices[0].delta.content or ""

def token_stream(messages):
    request_start = time.time()

    print("Sending request to LLM...", flush=True)

    stream = client.chat.completions.create(
        model="gpt-oss",
        messages=messages,
        stream=True,
        timeout=60,
    )

    print(
        f"LLM request returned stream object after "
        f"{time.time() - request_start:.2f} seconds",
        flush=True,
    )

    first_token_received = False

    for chunk in stream:
        if not chunk.choices:
            continue

        content = chunk.choices[0].delta.content

        if content:
            if not first_token_received:
                print(
                    f"First token received after "
                    f"{time.time() - request_start:.2f} seconds",
                    flush=True,
                )
                first_token_received = True

            yield content

def call_llm(messages):
    response = client.chat.completions.create(
        model="gpt-oss",
        messages=messages,
        stream=False,
        timeout=60,
    )

    return response.choices[0].message.content

if prompt := st.chat_input("Ask about NRP..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    try:
        with st.spinner("Searching NRP docs..."):
            chunks = search(prompt, k=2)

    except BadRequestError as error:
        print(f"Embedding gateway error: {error}", flush=True)
        st.error(
            "The NRP embedding service is currently unavailable. "
            "Please try again shortly."
        )
        st.stop()
    
    context = "\n\n---\n\n".join(f"[Source: {c['title']}]\n{c['text']}" for c in chunks)
    grounded = f"""Use the NRP documentation below to answer. If the docs don't contain the
        answer, say so honestly.
        DOCS: {context}
        QUESTION: {prompt}"""
    messages_for_llm = [
        system_prompt,
        {
            "role": "user",
            "content": grounded,
        },
    ]

    with st.chat_message("assistant"):
        print("Calling LLM...", flush=True)
        prompt_characters = sum(
            len(message.get("content", ""))
            for message in messages_for_llm
        )

        print(f"Messages sent: {len(messages_for_llm)}", flush=True)

        print(f"Total prompt size: {prompt_characters} characters", flush=True)
        answer = st.write_stream(token_stream(messages_for_llm))
        # answer = call_llm(messages_for_llm)
        # st.markdown(answer)
        print("LLM finished", flush=True)

        with st.expander("📚 Sources"):
            for c in chunks:
                st.markdown(
                    f"- [{c['title']}]({c['source_url']}) "
                    f"*(distance: {c['score']:.3f})*"
                )

    st.session_state.messages.append({"role": "assistant", "content": answer})