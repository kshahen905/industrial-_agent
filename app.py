import streamlit as st
import requests
import json
import uuid
import time
from feedback_db import log_feedback

# API configuration
API_URL = "http://localhost:8000/chat"

# Set page config
st.set_page_config(
    page_title="DevOps Log Analyzer",
    page_icon="🛠️",
    layout="wide"
)

# Custom styling
st.markdown("""
<style>
    .reportview-container {
        margin-top: -2em;
    }
    .stChatFloatingInputContainer {
        bottom: 20px;
    }
    .feedback-container {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛠️ DevOps Log Analyzer")
st.markdown("Analyze your infrastructure logs and get actionable solutions.")

# Initialize session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "awaiting_feedback_for" not in st.session_state:
    # Stores the index of the message we are currently asking feedback for
    st.session_state.awaiting_feedback_for = None

# Sidebar
with st.sidebar:
    st.header("Session Info")
    st.write(f"**Thread ID:** `{st.session_state.thread_id[:8]}...`")
    if st.button("Start New Session"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.awaiting_feedback_for = None
        st.rerun()
    
    st.divider()
    st.markdown("### How to use")
    st.markdown("1. Paste your error log below.")
    st.markdown("2. Wait for the agent to analyze it.")
    st.markdown("3. Provide feedback (👍 / 👎) on the solution.")

# Display chat messages
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # If this is the last agent response and it needs feedback
        if message["role"] == "assistant" and i == st.session_state.awaiting_feedback_for:
            st.markdown("---")
            st.markdown("**How was this response?**")
            
            # Using Streamlit form to capture optional comments without immediate rerun
            with st.form(key=f"feedback_form_{i}"):
                col1, col2 = st.columns([1, 4])
                with col1:
                    feedback_val = st.radio("Rating", ["👍 Helpful", "👎 Not Helpful"], horizontal=True, label_visibility="collapsed")
                with col2:
                    comment = st.text_input("Optional comment / reasoning", placeholder="Tell us why...")
                
                submit_button = st.form_submit_button("Submit Feedback")
                
                if submit_button:
                    score = 1 if feedback_val == "👍 Helpful" else -1
                    user_msg_idx = i - 1 if i > 0 else 0
                    user_msg = st.session_state.messages[user_msg_idx]["content"] if st.session_state.messages[user_msg_idx]["role"] == "user" else "Unknown input"
                    
                    # Log to DB
                    log_feedback(
                        thread_id=st.session_state.thread_id,
                        user_input=user_msg,
                        agent_response=message["content"],
                        feedback_score=score,
                        optional_comment=comment
                    )
                    
                    st.success("Feedback submitted! Thank you.")
                    st.session_state.awaiting_feedback_for = None
                    time.sleep(1)
                    st.rerun()

# Chat input
if prompt := st.chat_input("Paste your error log here..."):
    # Clear any pending feedback request
    st.session_state.awaiting_feedback_for = None
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Analyzing log... ⏳")
        
        # Call API
        try:
            payload = {
                "message": prompt,
                "thread_id": st.session_state.thread_id
            }
            response = requests.post(API_URL, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                final_answer = data.get("final_answer", "No answer provided.")
                message_placeholder.markdown(final_answer)
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
                st.session_state.awaiting_feedback_for = len(st.session_state.messages) - 1
                st.rerun()
            else:
                error_msg = f"API Error ({response.status_code}): {response.text}"
                message_placeholder.markdown(f"**Error:** {error_msg}")
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                
        except requests.exceptions.ConnectionError:
            error_msg = "Could not connect to the API. Make sure the backend is running on http://localhost:8000."
            message_placeholder.markdown(f"**Error:** {error_msg}")
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
