"""
app.py — Streamlit chat interface for Dublin Planning Permission AI Assistant

A simple, clean chat interface that lets users ask questions about
Dublin City Council planning applications and get accurate, grounded answers.
"""

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Page config
st.set_page_config(
    page_title="Dublin Planning AI Assistant",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for a clean look
st.markdown("""
<style>
    .stApp {
        max-width: 900px;
        margin: 0 auto;
    }
    .source-card {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 10px 15px;
        margin: 5px 0;
        font-size: 0.85em;
    }
    .header-subtitle {
        color: #666;
        font-size: 1.1em;
        margin-top: -10px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🏗️ Dublin Planning AI Assistant")
st.markdown('<p class="header-subtitle">Ask questions about Dublin City Council planning applications — powered by real data from 2003 to present</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("About")
    st.markdown("""
    This assistant has access to **20+ years** of Dublin City Council planning application data, including:
    
    - 📋 Application details & proposals
    - ✅ Decisions (granted/refused)
    - 📍 Locations & coordinates
    - ⚖️ Appeal records
    - 📅 Registration & decision dates
    
    **Data source:** Dublin City Council Open Data via Smart Dublin
    """)
    
    st.divider()
    
    st.header("Sample Questions")
    sample_questions = [
        "What planning applications were submitted in Drumcondra in January 2025?",
        "Show me refused applications in Dublin 8",
        "Any house extensions approved in Rathmines?",
        "What large developments were proposed in the Docklands?",
        "Are there appeals for planning applications in Ranelagh?",
        "What types of developments are common in Dublin 7?",
    ]
    
    for q in sample_questions:
        if st.button(q, key=f"sample_{hash(q)}", use_container_width=True):
            st.session_state.pending_question = q
    
    st.divider()
    
    st.markdown("""
    **Blindspot Labs** — The Strange Data Project  
    Nomad AI Competition 2025
    """)
    
    # Show sources toggle
    show_sources = st.checkbox("Show retrieved sources", value=False)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "collection" not in st.session_state:
    st.session_state.collection = None

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


@st.cache_resource
def load_collection():
    """Load ChromaDB collection (cached)."""
    try:
        from rag_engine import get_collection
        return get_collection()
    except Exception as e:
        st.error(f"Failed to load planning database: {e}")
        st.info("Make sure you've run `python download_data.py` first to set up the database.")
        return None


def get_chat_history():
    """Convert session messages to chat history format."""
    history = []
    for msg in st.session_state.messages[-6:]:  # Last 6 messages
        history.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    return history


# Load the collection
collection = load_collection()

if collection is None:
    st.warning("⚠️ Planning database not found. Please run the setup first:")
    st.code("python download_data.py", language="bash")
    st.stop()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show sources if enabled and available
        if show_sources and message["role"] == "assistant" and "sources" in message:
            with st.expander("📎 Retrieved Sources", expanded=False):
                for src in message["sources"]:
                    st.markdown(f"""
                    <div class="source-card">
                        <strong>Ref:</strong> {src['ref']} | 
                        <strong>Location:</strong> {src['location'][:80]} | 
                        <strong>Decision:</strong> {src['decision']} |
                        <strong>Relevance:</strong> {src['relevance']}
                    </div>
                    """, unsafe_allow_html=True)


# Handle pending question from sidebar
if st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None
else:
    prompt = st.chat_input("Ask about Dublin planning applications...")

# Process user input
if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Searching planning records..."):
            try:
                from rag_engine import query_planning
                
                result = query_planning(
                    query=prompt,
                    chat_history=get_chat_history(),
                    collection=collection
                )
                
                answer = result["answer"]
                sources = result["sources"]
                
                st.markdown(answer)
                
                # Show sources if enabled
                if show_sources and sources:
                    with st.expander("📎 Retrieved Sources", expanded=False):
                        for src in sources:
                            st.markdown(f"""
                            <div class="source-card">
                                <strong>Ref:</strong> {src['ref']} | 
                                <strong>Location:</strong> {src['location'][:80]} | 
                                <strong>Decision:</strong> {src['decision']} |
                                <strong>Relevance:</strong> {src['relevance']}
                            </div>
                            """, unsafe_allow_html=True)
                
                # Save to session
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "sources": []
                })
