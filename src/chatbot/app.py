"""Streamlit UI for the parking chatbot."""
import uuid

import httpx
import streamlit as st

import os

_API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="CityPark Chatbot", page_icon="🅿️")
st.title("🅿️ CityPark Assistant")
st.caption("Ask me anything about parking, prices, hours, or to make a reservation.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "history" not in st.session_state:
    st.session_state.history = []

for role, content in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)

user_input = st.chat_input("Type your message…")

if user_input:
    st.session_state.history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                resp = httpx.post(
                    f"{_API_BASE}/chat",
                    json={"session_id": st.session_state.session_id, "message": user_input},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data["response"]
            except Exception as exc:
                answer = f"⚠️ Error: {exc}"
        st.markdown(answer)

    st.session_state.history.append(("assistant", answer))
