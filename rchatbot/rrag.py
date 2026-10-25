import os
import streamlit as st
from rsearch import search
import json
from dotenv import load_dotenv
from openai import OpenAI
from openai import BadRequestError
from openai import APITimeoutError
from openai import APIConnectionError
import time
import httpx
import re
import base64
from PIL import Image
from io import BytesIO
from openai import InternalServerError
import streamlit.components.v1 as components
from streamlit_geolocation import streamlit_geolocation
from geopy.geocoders import Nominatim
from pathlib import Path
import sqlite3
from datetime import datetime
from collections import Counter

DB_PATH = "/app/data/user_activity.db"
load_dotenv()
client = OpenAI(api_key=os.environ["NRP_LLM_TOKEN"],
                base_url=os.environ.get("NRP_LLM_BASE_URL", "https://ellm.nrp-nautilus.io/v1"))

st.set_page_config(page_title="Recycle Assistant", page_icon="♻️")
if st.user.is_logged_in:
    st.sidebar.write(f"Signed in as {st.user.name}")

    if st.sidebar.button("Log out"):
        st.logout()

else:
    st.sidebar.write("Sign in to save your recycling history and track your impact.")

    if st.sidebar.button("Sign in with Google"):
        st.login("google")
st.title("♻️ Recycle Assistant", anchor = False)
st.caption("Helping You Recycle Effectively Using Trusted Documentation")
main_image_status = st.empty()
if "busy" not in st.session_state:
    st.session_state.busy = False

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

geolocator = Nominatim(
    user_agent="recycle-assistant"
)


if "image_uploader_version" not in st.session_state:
    st.session_state.image_uploader_version = 0

BASE_DIR = Path(__file__).resolve().parent
LOCATION_MAP_PATH = BASE_DIR / "recycling_json" / "location_map.json"

with open(LOCATION_MAP_PATH, encoding="utf-8") as f:
    location_map = json.load(f)

def init_user_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                item TEXT,
                material TEXT,
                action TEXT,
                service_area TEXT
            )
            """
        )
        conn.commit()

init_user_db()

def save_activity(user_id, item, material, action, service_area):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO activity (
                user_id,
                timestamp,
                item,
                material,
                action,
                service_area
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                datetime.now().isoformat(),
                item,
                material,
                action,
                service_area,
            ),
        )
        conn.commit()

def get_user_activity(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                id,
                timestamp,
                item,
                material,
                action,
                service_area
            FROM activity
            WHERE user_id = ?
            ORDER BY timestamp DESC
            """,
            (user_id,),
        ).fetchall()

    return [dict(row) for row in rows]

def classify_activity(image_description, answer):
    response = client.chat.completions.create(
        model="qwen3-small",
        messages=[
            {
                "role": "system",
                "content": (
                    "/no think\n\n"
                    "Extract recycling activity data from the provided information. "
                    "Return exactly these fields:\n"
                    "Item: <short item name>\n"
                    "Material: <short material/category>\n"
                    "Action: <one of Recycle, Trash, HHW, E-waste, Compost, Reuse, Donate, Other>\n"
                    "Do not add any other text."
                ),
            },
            {
                "role": "user",
                "content": f"""
IMAGE DESCRIPTION:
{image_description or "None"}

ASSISTANT ANSWER:
{answer}
""",
            },
        ],
        temperature=0,
        timeout=30,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False
            }
        },
    )

    text = response.choices[0].message.content.strip()

    item_match = re.search(r"Item:\s*(.+)", text)
    material_match = re.search(r"Material:\s*(.+)", text)
    action_match = re.search(r"Action:\s*(.+)", text)

    return {
        "item": item_match.group(1).strip() if item_match else "Unknown",
        "material": material_match.group(1).strip() if material_match else "Unknown",
        "action": action_match.group(1).strip() if action_match else "Other",
    }

def scroll_to_bottom():
    components.html(
        """
        <script>
        setTimeout(() => {
            const container =
                window.parent.document.querySelector(
                    '[data-testid="stAppViewContainer"]'
                );

            if (container) {
                container.scrollTo({
                    top: container.scrollHeight,
                    behavior: 'smooth'
                });
            }
        }, 150);
        </script>
        """,
        height=0,
    )

def analyze_recycling_image(uploaded_image):
    image = Image.open(uploaded_image)

    # Convert to RGB so JPEG saving works reliably
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Shrink very large photos
    image.thumbnail((1280, 1280))

    buffer = BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=80,
        optimize=True
    )
    
    image_bytes = buffer.getvalue()

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    mime_type = "image/jpeg"

    response = client.chat.completions.create(
        model="qwen3-small",
        messages=[
            {
                "role": "system",
                "content": (
                    "Identify the main waste or recycling item visible in the image. "
                    "Carefully identify the main discarded item in the image. "
                    "This image may contain crumpled, dirty, folded, or partially obscured trash. "
                    "Do not assume an item is a plastic bag simply because it contains plastic. "
                    "Consider common waste items such as diapers, wipes, food packaging, "
                    "plastic bags, bottles, cans, paper, cardboard, and sanitary products. "

                    "Return exactly these fields:\n"
                    "Object: <best identification>\n"
                    "Material: <one of Paper/Cardboard, Plastic, Glass, Metal, Electronics, Battery, Organic, Textile, Mixed Material, Other>\n"
                    "Condition: <clean, dirty, wet, contaminated, etc.>\n"
                    "Confidence: <high, medium, or low>\n"
                    "Alternative: <second most likely identification if uncertain>\n"

                    "Do NOT determine recyclability."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Identify this item for a recycling "
                            "assistant."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url":
                            f"data:{mime_type};base64,{image_base64}"
                        },
                    },
                ],
            },
        ],
        temperature=0,
        timeout=30,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False
            }
        }
    )

    return response.choices[0].message.content.strip()

def get_service_area(state, county, city):
    return (
        location_map
        .get(state, {})
        .get(county, {})
        .get(city)
    )

with st.sidebar:
    st.header("Settings")

    if st.button("🗑️ Clear chat"):
        st.session_state.pop("messages", None)
        st.session_state.pop("image_description", None)
        st.session_state.pop("last_image_id", None)
        st.session_state.pop("prompt_uses_image", None)

        st.session_state.image_uploader_version += 1

        st.session_state.pending_prompt = None
        st.session_state.busy = False
        st.rerun()

    st.divider()
    st.subheader("🌍 Your Location")
    st.write("Click to Enable Location Services")
    location = streamlit_geolocation()
    if location and location.get("latitude") is not None:

        latitude = location["latitude"]
        longitude = location["longitude"]

        result = geolocator.reverse(
            (latitude, longitude),
            exactly_one=True
        )

        if result:
            address = result.raw.get("address", {})

            state = address.get("state")

            county = address.get("county")
            if county:
                county = county.replace(" County", "")

            city = (
                address.get("city")
                or address.get("town")
                or address.get("village")
            )

            if state == "California" and city == "San Francisco" and not county:
                county = "San Francisco"

            service_area = get_service_area(state, county, city)
            st.write("State:", state)
            st.write("County:", county)
            st.write("City:", city)
            st.write("Service Area:", service_area)
            st.session_state.state = state
            st.session_state.county = county
            st.session_state.city = city
            st.session_state.service_area = service_area

    st.divider()
    st.subheader("📷 Check an Item")

    uploaded_image = st.file_uploader(
        "Upload an item to check",
        type=["jpg", "jpeg", "png"],
        key=f"recycling_image_{st.session_state.image_uploader_version}",
        disabled=st.session_state.busy
    )
    if uploaded_image is not None:
        current_image_id = (
            uploaded_image.name,
            uploaded_image.size,
        )

        if st.session_state.get("last_image_id") != current_image_id:
            st.session_state.last_image_id = current_image_id
            st.session_state.pop("image_description", None)
            st.session_state.prompt_uses_image = False

    if uploaded_image:
        st.image(
            uploaded_image,
            caption="Item to analyze",
            use_container_width=True
        )
    if st.button("🔍 Analyze Item", disabled=st.session_state.busy):
        if uploaded_image is None:
            st.error("Please upload an image before analyzing.")
        else:
            try:
                main_image_status.info("🔍 Analyzing image...")

                scroll_to_bottom()

                with st.spinner("Analyzing image..."):
                    st.session_state.image_description = (
                        analyze_recycling_image(uploaded_image)
                    )

                main_image_status.success("✅ Image analysis complete")

                st.session_state.pending_prompt = (
                    "Can this item be recycled, and how should it be disposed of?"
                )

                st.session_state.prompt_uses_image = True
                st.session_state.busy = True
                st.rerun()

            except InternalServerError:
                main_image_status.error("Image analysis failed.")
                st.error(
                    "The image-analysis service could not process this image. "
                    "Please try again or upload a different image."
            )

    if "image_description" in st.session_state:
        st.success("Image analyzed")
        # st.write(st.session_state.image_description)
    
    if st.user.is_logged_in:
        user_id = st.user.get("sub") or st.user.get("email")
        activity_rows = get_user_activity(user_id)

        st.sidebar.divider()
        st.sidebar.subheader("📊 My Impact")

        total_checked = len(activity_rows)

        recyclable = sum(
            1 for row in activity_rows
            if row["action"] == "Recycle"
        )

        special_disposal = sum(
            1 for row in activity_rows
            if row["action"] in [
                "HHW",
                "E-waste",
                "Compost",
            ]
        )

        diverted = sum(
            1 for row in activity_rows
            if row["action"] != "Trash"
        )

        st.sidebar.metric("Items Checked", total_checked)
        st.sidebar.metric("Recyclable", recyclable)
        st.sidebar.metric("Special Disposal", special_disposal)
        st.sidebar.metric("Diverted from Trash", diverted)

        st.sidebar.divider()
        st.sidebar.subheader("🕒 Recent Activity")

        if activity_rows:
            for row in activity_rows[:5]:
                st.sidebar.write(
                    f"**{row['item']}** — {row['action']}"
                )
        else:
            st.sidebar.write("No activity yet.")

        st.sidebar.divider()
        st.sidebar.subheader("♻️ Material Breakdown")

        materials = [
            row["material"]
            for row in activity_rows
            if row["material"]
        ]

        material_counts = Counter(materials)

        if material_counts:
            for material, count in material_counts.most_common():
                st.sidebar.write(f"**{material}:** {count}")
        else:
            st.sidebar.write("No material data yet.")

system_prompt ={
            "role": "system", "content": 
            """
                You are a Recycling assistant, who always provides concise and accurate information.

                For every question answer from the documentation provided in the user's message.   

                Try to keep responses under 100 words and in bullet points.
            """
            }

if "messages" not in st.session_state:
    st.session_state.messages = [system_prompt]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("📚 Sources"):
                    for chunk in msg["sources"]:
                        st.markdown(
                            f"- [{chunk['title']}]({chunk['source_url']}) "
                            f"*(distance: {chunk['score']:.3f}, "
                            # f"reranked: {chunk['rank_score']:.3f})*"
                        )


STOP_WORDS = {
    "a", "an", "the", "is", "are", "i", "you", "we",
    "do", "does", "did", "can", "could", "would", "should",
    "how", "what", "where", "when", "why", "which",
    "to", "of", "for", "in", "on", "with", "and", "or",
    "my", "your", "me", "please",
}

def rerank(question: str, chunks: list[dict]) -> list[dict]:
    normalized_question = question.lower().strip()

    query_words = [
        word
        for word in re.findall(r"\b[a-z0-9]+\b", normalized_question)
        if word not in STOP_WORDS
    ]

    query_word_set = set(query_words)

    # Build general two-word and three-word phrases.
    query_phrases = []

    for size in (2, 3):
        for index in range(len(query_words) - size + 1):
            phrase = " ".join(query_words[index:index + size])
            query_phrases.append(phrase)

    for chunk in chunks:
        title = chunk["title"].lower()
        text = chunk["text"].lower()
        combined_text = f"{title} {text}"

        title_words = set(
            re.findall(r"\b[a-z0-9]+\b", title)
        )

        text_words = set(
            re.findall(r"\b[a-z0-9]+\b", text)
        )

        title_matches = len(query_word_set & title_words)
        text_matches = len(query_word_set & text_words)

        # What fraction of the important query words occur in the chunk?
        coverage = (
            text_matches / len(query_word_set)
            if query_word_set
            else 0
        )

        # Reward matching any query phrase, not specific commands.
        phrase_matches = sum(
            1 for phrase in query_phrases
            if phrase in combined_text
        )

        chunk["rank_score"] = (
            chunk["score"]
            - title_matches * 0.08
            - text_matches * 0.03
            - coverage * 0.15
            - phrase_matches * 0.08
        )
        if chunk.get("location_level") == "service_area":
            chunk["rank_score"] -= 0.20

        elif chunk.get("location_level") == "county":
            chunk["rank_score"] -= 0.10

        elif chunk.get("location_level") == "state":
            chunk["rank_score"] -= 0.05

    return sorted(chunks, key=lambda chunk: chunk["rank_score"])


def rewrite_single_query(question: str) -> str:
    query = question.lower().strip()

    query = re.sub(
        r"^(?:how\s+(?:do|can|could|would)\s+(?:i|you)\s+|"
        r"how\s+to\s+)",
        "",
        query,
    )

    query = re.sub(r"[?.!,;:]+$", "", query)

    return " ".join(query.split()) or question


def rewrite_search_query(question: str) -> str:
    questions = question.splitlines()

    rewritten_questions = [
        rewrite_single_query(item)
        for item in questions
        if item.strip()
    ]

    return " ".join(rewritten_questions)

def token_stream(messages):
    request_start = time.time()

    print("Sending request to LLM...", flush=True)

    
    stream = client.chat.completions.create(
        model="qwen3-small",
        messages=messages,
        stream=True,
        timeout=60,
        temperature=0.2,
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

def rewrite_follow_up_with_ai(messages, current_question):
    recent_history = [
        message
        for message in messages
        if message["role"] in {"user", "assistant"}
    ][-4:]

    rewrite_messages = [
        {
            "role": "system",
            "content": (
                "/no think\n\n"
                "Rewrite the latest user question as a standalone search query. "
                "Use conversation history only to resolve references such as "
                "'it', 'them', 'that', or 'there'. "
                "If the latest question is independent, return it unchanged. "
                "Do not answer the question. "
                "Return only the rewritten query."
            ),
        },
        *recent_history,
        {
            "role": "user",
            "content": current_question,
        },
    ]

    response = client.chat.completions.create(
        model="qwen3-small",
        messages=rewrite_messages,
        temperature=0,
        timeout=30,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False
            }
        },
    )

    return response.choices[0].message.content.strip()

typed_prompt = st.chat_input(
    "Ask about Recycling...",
    disabled=st.session_state.busy
)

if typed_prompt:
    st.session_state.pending_prompt = typed_prompt
    st.session_state.busy = True
    st.session_state.scroll_after_submit = True
    st.rerun()

prompt = st.session_state.pending_prompt

if prompt:
    image_description = st.session_state.get(
        "image_description",
        None
    )

    if uploaded_image is not None and image_description is None:
        with st.spinner("Analyzing uploaded image..."):
            image_description = analyze_recycling_image(uploaded_image)
            st.session_state.image_description = image_description

    if uploaded_image is not None:
        st.session_state.prompt_uses_image = True

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if st.session_state.get("scroll_after_submit"):
        scroll_to_bottom()
        st.session_state.scroll_after_submit = False

    try:
        with st.spinner("Searching Recycling docs..."):
            if image_description:
                question_for_rag = f"""
                The user uploaded an image.

                IMAGE DESCRIPTION:
                {image_description}

                USER QUESTION:
                {prompt}
                """
            else:
                question_for_rag = prompt

            # st.write("Image analysis:", image_description)
            # st.write(
            #     "LOCATION FILTER:",
            #     st.session_state.get("state"),
            #     st.session_state.get("county"),
            #     st.session_state.get("service_area"),
            #     flush=True,
            # )
            standalone_query = rewrite_follow_up_with_ai(
                st.session_state.messages[:-1],
                question_for_rag,
            )
            search_query = rewrite_search_query(standalone_query)
            retrieved = search(
                search_query,
                state=st.session_state.get("state"),
                county=st.session_state.get("county"),
                service_area=st.session_state.get("service_area"),
            )
            # reranked = rerank(search_query, retrieved)
            # st.session_state.debug_retrieved = retrieved


            # print("All retrieved and reranked chunks:", flush=True)
            # for index, chunk in enumerate(reranked, start=1):
            #     print(
            #         f"{index}. {chunk['title']} | "
            #         f"distance: {chunk['score']:.3f} | "
            #         f"reranked: {chunk['rank_score']:.3f}",
            #         flush=True,
            #     )

            if not retrieved:
                st.error("No documentation chunks were returned by search.")
                st.stop()

            chunks = retrieved

            # print(f"Original question: {prompt}", flush=True)
            # print(f"Rewritten search query: {search_query}", flush=True)
            # print(f"Standalone query: {standalone_query}")

            # print("\nChunks being sent to the LLM:", flush=True)

            # for index, chunk in enumerate(chunks, start=1):
            #     print(
            #         f"\n===== Chunk {index}: {chunk['title']} =====\n"
            #         f"Source: {chunk['source_url']}\n"
            #         f"Distance: {chunk['score']:.3f}\n"
            #         f"Reranked: {chunk['rank_score']:.3f}\n\n"
            #         f"{chunk['text']}\n",
            #         flush=True,
            #     )

    except BadRequestError as error:
        print(f"Embedding gateway error: {error}", flush=True)
        st.error(
            "The NRP embedding service is currently unavailable. "
            "Please try again shortly."
        )
        st.stop()
    
    context = "\n\n---\n\n".join(f"[Source: {c['title']}]\n{c['text']}" for c in chunks)
    # print("\n" + "=" * 80, flush=True)
    # print("FULL CONTEXT SENT TO LLM", flush=True)
    # print("=" * 80, flush=True)
    # print(context, flush=True)
    # print("=" * 80 + "\n", flush=True)

    grounded = f"""

    /no think

    DOCUMENTATION:
    {context}

    LOCATION:
    State: {st.session_state.get("state")}
    County: {st.session_state.get("county")}
    Service Area: {st.session_state.get("service_area")}

    IMAGE DESCRIPTION:
    {image_description if image_description else "No image provided"}

    USER QUESTION:
    {prompt}

    Use the IMAGE DESCRIPTION only to understand what object
    the user is referring to.

    Determine whether and how the item should be recycled or
    disposed of from the DOCUMENTATION.

    Answer based on the user's location
    Mention the location in your answer.
    Prefer the most location-specific applicable guidance:
    1. Service-area guidance
    2. County guidance
    3. State guidance
    4. General guidance

    If more specific local guidance conflicts with broader guidance,
    follow the more specific local guidance.

    Do not use recycling rules for a different service area,
    county, or state.
    """
    conversation_history = [
        message
        for message in st.session_state.messages[1:-1]
        if message["role"] in {"user", "assistant"}
    ]

    messages_for_llm = [
        system_prompt,
        *conversation_history,
        {
            "role": "user",
            "content": grounded,
        },
    ]

    with st.chat_message("assistant"):
        print("Calling LLM...", flush=True)

        scroll_to_bottom()
        
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
                    # f"reranked: {chunk['rank_score']:.3f})*"
                )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": chunks
        }
    )

    if st.user.is_logged_in and image_description:
        activity = classify_activity(image_description, answer)

        user_id = st.user.get("sub") or st.user.get("email")

        save_activity(
            user_id=user_id,
            item=activity["item"],
            material=activity["material"],
            action=activity["action"],
            service_area=st.session_state.get("service_area"),
        )

    st.session_state.pending_prompt = None
    st.session_state.busy = False

    if st.session_state.get("prompt_uses_image", False):
        st.session_state.prompt_uses_image = False

    st.rerun()
# if st.session_state.get("debug_retrieved"):
#     st.subheader("Debug retrieval")

#     for i, chunk in enumerate(st.session_state.debug_retrieved, start=1):
#         st.write(
#             i,
#             chunk["title"],
#             chunk.get("service_area"),
#             chunk.get("location_level"),
#             chunk["score"],
#         )