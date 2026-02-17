"""
app.py — Streamlit chat interface for Dublin Planning Permission AI Assistant

Works both locally (via .env file) and on Streamlit Cloud (via st.secrets).
On first run, automatically downloads data and builds the vector database.
"""

import streamlit as st
import os
from pathlib import Path

# ── Load API keys from Streamlit secrets OR .env file ──────────
# Streamlit Cloud uses st.secrets; local dev uses .env
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass  # st.secrets not available (local dev)

from dotenv import load_dotenv
load_dotenv()

# Page config
st.set_page_config(
    page_title="Dublin Planning AI Assistant",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { max-width: 900px; margin: 0 auto; }
    .source-card {
        background-color: #f0f2f6; border-radius: 8px;
        padding: 10px 15px; margin: 5px 0; font-size: 0.85em;
    }
    .header-subtitle { color: #666; font-size: 1.1em; margin-top: -10px; }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🏗️ Dublin Planning AI Assistant")
st.markdown(
    '<p class="header-subtitle">Ask questions about Dublin City Council planning '
    'applications — powered by real data</p>',
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.header("About")
    st.markdown("""
    This assistant has access to **Dublin City Council planning application data**, including:
    
    - 📋 Application details & proposals
    - ✅ Decisions (granted/refused)
    - 📍 Locations & addresses
    - ⚖️ Appeal records
    - 📅 Registration & decision dates
    
    **Data source:** Irish Planning Applications ArcGIS API (Dept. of Housing)
    """)

    st.divider()
    st.header("I am a...")
    user_role = st.radio(
        "Filter results by your role:",
        ["Everyone", "Property Developer", "Architect", "Solicitor", "Estate Agent", "Homeowner", "Journalist"],
        index=0,
        label_visibility="collapsed",
    )
    
    # Map roles to relevant filters and sample questions
    role_config = {
        "Everyone": {
            "questions": [
                "What planning applications were submitted in Drumcondra?",
                "Show me refused applications in Dublin 8",
                "Any house extensions approved in Rathmines?",
                "What large developments were proposed in the Docklands?",
                "Are there appeals for applications in Ranelagh?",
                "What developments involve demolition in Dublin city centre?",
            ],
        },
        "Property Developer": {
            "questions": [
                "What large residential developments were granted in Dublin 1?",
                "Show me sites where planning was refused — potential opportunity?",
                "What developments on public or council land were proposed recently?",
                "How many residential units were approved in the Docklands?",
            ],
        },
        "Architect": {
            "questions": [
                "What extensions were granted in Rathmines? Looking for precedent.",
                "Were any two-storey extensions refused in Dublin 6?",
                "What conditions are typically attached to house extension permissions?",
                "Show me applications for change of use in Dublin 2",
            ],
        },
        "Solicitor": {
            "questions": [
                "Are there any active appeals for applications in Ranelagh?",
                "Was planning granted for developments on Griffith Avenue?",
                "What applications are currently pending in Dublin 4?",
                "Show me applications with further information requests in Ballsbridge",
            ],
        },
        "Estate Agent": {
            "questions": [
                "What developments were approved near Portobello?",
                "Any large residential schemes proposed in Dublin 8?",
                "What demolition applications were submitted in the city centre?",
                "Show me recent granted applications in Phibsborough",
            ],
        },
        "Homeowner": {
            "questions": [
                "Were any applications refused near my area in Drumcondra?",
                "What developments are planned in Stoneybatter?",
                "Any extensions approved on my street in Glasnevin?",
                "What appeals were lodged for applications in Cabra?",
            ],
        },
        "Journalist": {
            "questions": [
                "What are the most refused areas in Dublin for planning?",
                "Show me large-scale developments on public land",
                "What planning applications involve social housing?",
                "How many applications were appealed in Dublin city centre?",
            ],
        },
    }
    
    config = role_config.get(user_role, role_config["Everyone"])
    
    st.divider()
    st.header("Sample Questions")
    for q in config["questions"]:
        if st.button(q, key=f"sample_{hash(q)}", use_container_width=True):
            st.session_state.pending_question = q

    st.divider()
    st.markdown("**Blindspot Labs** — The Strange Data Project\nNomad AI Competition 2025 🏆 2nd Place")
    show_sources = st.checkbox("Show retrieved sources", value=False)
    st.caption("Embeddings: Local (MiniLM) | Generation: Claude")


# ── Auto-setup: download data & build DB if needed ─────────────
@st.cache_resource(show_spinner="Setting up planning database (first run only, ~5 min)...")
def setup_and_load():
    """Download data, build vector DB, and return the ChromaDB collection."""
    
    # Check API key — Anthropic for generation, embeddings are local (no key needed)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None, "ANTHROPIC_API_KEY not found. Add it to .env (local) or Streamlit Secrets (cloud)."
    
    chroma_dir = Path("chroma_db")
    data_dir = Path("data")
    
    # If vector DB doesn't exist yet, build it
    if not chroma_dir.exists() or not any(chroma_dir.iterdir()):
        try:
            # Step 1: Download data
            if not (data_dir / "processed_records.json").exists():
                from download_data import download_all_data, clean_and_process_data
                
                if not download_all_data():
                    return None, "Failed to download planning data from ArcGIS API."
                
                if not clean_and_process_data():
                    return None, "Failed to process planning data."
            
            # Step 2: Build vector DB
            from build_vectordb import build_vector_database
            build_vector_database()
            
        except Exception as e:
            return None, f"Setup failed: {str(e)}"
    
    # Load the collection
    try:
        from rag_engine import get_collection
        collection = get_collection()
        return collection, None
    except Exception as e:
        return None, f"Failed to load planning database: {str(e)}"


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# Load collection
collection, error = setup_and_load()

if error:
    st.error(f"⚠️ {error}")
    if "API_KEY" in error:
        st.info(
            "**Local:** Create a `.env` file with `OPENAI_API_KEY=sk-your-key`\n\n"
            "**Streamlit Cloud:** Go to App Settings → Secrets and add:\n"
            "```\nOPENAI_API_KEY = \"sk-your-key\"\n```"
        )
    st.stop()


def get_chat_history():
    history = []
    for msg in st.session_state.messages[-6:]:
        history.append({"role": msg["role"], "content": msg["content"]})
    return history


# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if show_sources and message["role"] == "assistant" and "sources" in message:
            with st.expander("📎 Retrieved Sources", expanded=False):
                for src in message["sources"]:
                    cat_badge = f' | <strong>Type:</strong> {src.get("dev_category", "")}' if src.get("dev_category") else ''
                    land_badge = f' | <strong>Land:</strong> {src.get("land_type", "")}' if src.get("land_type") else ''
                    st.markdown(
                        f'<div class="source-card">'
                        f'<strong>Ref:</strong> {src["ref"]} | '
                        f'<strong>Location:</strong> {src["location"][:80]} | '
                        f'<strong>Decision:</strong> {src["decision"]} | '
                        f'<strong>Relevance:</strong> {src["relevance"]}'
                        f'{cat_badge}{land_badge}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

# Handle pending question from sidebar
# Always render chat_input so it never disappears
prompt = st.chat_input("Ask about Dublin planning applications...")

# Sidebar click takes priority
if st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None

# Process user input
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching planning records..."):
            try:
                from rag_engine import query_planning

                result = query_planning(
                    query=prompt,
                    chat_history=get_chat_history(),
                    collection=collection,
                )
                answer = result["answer"]
                sources = result["sources"]

                st.markdown(answer)

                if show_sources and sources:
                    with st.expander("📎 Retrieved Sources", expanded=False):
                        for src in sources:
                            cat_badge = f' | <strong>Type:</strong> {src.get("dev_category", "")}' if src.get("dev_category") else ''
                            land_badge = f' | <strong>Land:</strong> {src.get("land_type", "")}' if src.get("land_type") else ''
                            st.markdown(
                                f'<div class="source-card">'
                                f'<strong>Ref:</strong> {src["ref"]} | '
                                f'<strong>Location:</strong> {src["location"][:80]} | '
                                f'<strong>Decision:</strong> {src["decision"]} | '
                                f'<strong>Relevance:</strong> {src["relevance"]}'
                                f'{cat_badge}{land_badge}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "sources": sources}
                )

            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg, "sources": []}
                )

    st.rerun()
