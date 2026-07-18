import os
import streamlit as st
from search import search
from dotenv import load_dotenv
from openai import OpenAI
from openai import BadRequestError
from openai import APITimeoutError
from openai import APIConnectionError
import time
import httpx
import re


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

STOP_WORDS = {
    "a", "an", "the", "is", "are", "i", "do", "does",
    "how", "what", "where", "when", "why", "to", "of",
    "for", "in", "on", "with", "and", "or",
}

def rerank(question: str, chunks: list[dict]) -> list[dict]:
    question_words = set(
        re.findall(r"\b[a-z0-9]+\b", question.lower())
    )
    keywords = question_words - STOP_WORDS

    for chunk in chunks:
        title_words = set(
            re.findall(r"\b[a-z0-9]+\b", chunk["title"].lower())
        )
        text_words = set(
            re.findall(r"\b[a-z0-9]+\b", chunk["text"].lower())
        )

        title_matches = len(keywords & title_words)
        text_matches = len(keywords & text_words)

        chunk["rank_score"] = (
            chunk["score"]
            - title_matches * 0.06
            - text_matches * 0.03
        )

    return sorted(chunks, key=lambda chunk: chunk["rank_score"])


def rewrite_search_query(question: str) -> str:
    query = question.lower().strip()

    query = re.sub(
        r"^(?:how\s+(?:do|can|could|would)\s+(?:i|you)\s+|how\s+to\s+)",
        "",
        query,
    )

    query = re.sub(r"\bon nrp\b", "", query)

    return " ".join(query.split()) or question

def token_stream(messages):
    request_start = time.time()

    print("Sending request to LLM...", flush=True)

    
    stream = client.chat.completions.create(
        model="qwen3-small",
        messages=messages,
        stream=True,
        timeout=60,
        temperature=0.1,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False
            }
        },
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

if prompt := st.chat_input("Ask about NRP..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    try:
        with st.spinner("Searching NRP docs..."):
            search_query = rewrite_search_query(prompt)
            retrieved = search(search_query, k=20)
            reranked = rerank(search_query, retrieved)

            print("All retrieved and reranked chunks:", flush=True)
            for index, chunk in enumerate(reranked, start=1):
                print(
                    f"{index}. {chunk['title']} | "
                    f"distance: {chunk['score']:.3f} | "
                    f"reranked: {chunk['rank_score']:.3f}",
                    flush=True,
                )
            chunks = reranked[:2]

            print(f"Original question: {prompt}", flush=True)
            print(f"Rewritten search query: {search_query}", flush=True)

            for index, chunk in enumerate(chunks, start=1):
                print(
                    f"{index}. {chunk['title']} | "
                    f"distance: {chunk['score']:.3f} | "
                    f"reranked: {chunk['rank_score']:.3f}",
                    flush=True,
                )

    except BadRequestError as error:
        print(f"Embedding gateway error: {error}", flush=True)
        st.error(
            "The NRP embedding service is currently unavailable. "
            "Please try again shortly."
        )
        st.stop()
    
    context = "\n\n---\n\n".join(f"[Source: {c['title']}]\n{c['text']}" for c in chunks)
    grounded = f"""
    Use only the NRP documentation below to answer the question.

    If the documentation does not contain the answer, respond exactly:
    "The provided documentation does not contain enough information to answer this question."

    Do not use outside knowledge.
    Do not guess.

    /no_think

    DOCUMENTATION:
    {context}

    QUESTION:
    {prompt}
    """
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
        try:
            with st.spinner("Generating answer..."):
                answer = st.write_stream(token_stream(messages_for_llm))

        except (APITimeoutError, httpx.ReadTimeout) as error:
            print(f"LLM timeout: {error}", flush=True)
            st.error(
                "The model stopped responding before completing the answer. "
                "Please try again."
            )
            st.stop()

        except APIConnectionError as error:
            print(f"LLM connection error: {error}", flush=True)
            st.error("Could not connect to the LLM service.")
            st.stop()
        print("LLM finished", flush=True)

        with st.expander("📚 Sources"):
            for chunk in chunks:
                st.markdown(
                    f"- [{chunk['title']}]({chunk['source_url']}) "
                    f"*(distance: {chunk['score']:.3f}, "
                    f"reranked: {chunk['rank_score']:.3f})*"
                )

    st.session_state.messages.append({"role": "assistant", "content": answer})