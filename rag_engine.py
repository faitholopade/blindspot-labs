"""
rag_engine.py — Retrieval-Augmented Generation engine for planning queries

Handles:
1. Query embedding and semantic search against ChromaDB
2. Context assembly from retrieved planning records
3. LLM generation with grounded responses (OpenAI or Anthropic)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Also try Streamlit secrets (for cloud deployment)
try:
    import streamlit as st
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    if "LLM_PROVIDER" in st.secrets:
        os.environ["LLM_PROVIDER"] = st.secrets["LLM_PROVIDER"]
except Exception:
    pass

CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "dublin_planning"
EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 10  # Number of results to retrieve

# System prompt for the planning assistant
SYSTEM_PROMPT = """You are an expert Dublin City Council planning permission assistant. You have access to a database of real planning applications from Dublin City Council, covering applications from 2003 to the present day.

Your role is to answer questions about Dublin planning applications accurately using ONLY the planning records provided to you. Follow these rules:

1. ONLY use information from the provided planning records. Do not make up or hallucinate planning references, addresses, or decisions.
2. When referencing specific applications, always cite the planning reference number (e.g., "Ref: 2458/24").
3. If the provided records don't contain enough information to fully answer the question, say so honestly and explain what information you do have.
4. When listing applications, format them clearly with reference number, location, proposal summary, and decision status.
5. For questions about trends or patterns, summarize what the data shows.
6. If asked about zoning or development plan policies, note that you have access to planning application records but not the full Development Plan text — recommend checking dublincity.ie for zoning specifics.
7. Be precise with dates and decisions. Don't guess about outcomes.
8. You cover Dublin City Council area only (Dublin 1-24 roughly, not Fingal, DLR, or South Dublin).

Remember: You are providing factual information from real public records. Be helpful, accurate, and thorough."""


def get_collection():
    """Get the ChromaDB collection."""
    import chromadb
    from chromadb.utils import embedding_functions
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")
    
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL
    )
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=openai_ef
    )
    
    return collection


def retrieve_context(query: str, collection=None, top_k: int = TOP_K) -> tuple[str, list[dict]]:
    """
    Retrieve relevant planning records for a query.
    
    Returns:
        context_text: Formatted string of retrieved records
        raw_results: List of result dicts with metadata
    """
    if collection is None:
        collection = get_collection()
    
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    if not results or not results['documents'] or not results['documents'][0]:
        return "No relevant planning records found.", []
    
    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    
    # Format context
    context_parts = []
    raw_results = []
    
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        context_parts.append(f"--- Planning Record {i+1} (relevance: {1-dist:.2f}) ---")
        context_parts.append(doc)
        context_parts.append("")
        
        raw_results.append({
            "document": doc,
            "metadata": meta,
            "distance": dist,
            "relevance": 1 - dist
        })
    
    context_text = "\n".join(context_parts)
    return context_text, raw_results


def generate_response_openai(query: str, context: str, chat_history: list = None) -> str:
    """Generate response using OpenAI."""
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add chat history if provided
    if chat_history:
        for msg in chat_history[-6:]:  # Keep last 6 messages for context
            messages.append(msg)
    
    # Create the user message with context
    user_message = f"""Based on the following Dublin City Council planning records, please answer this question:

**Question:** {query}

**Retrieved Planning Records:**
{context}

Please provide a clear, accurate answer based on these records. Cite specific planning reference numbers where relevant."""
    
    messages.append({"role": "user", "content": user_message})
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1,
        max_tokens=2000
    )
    
    return response.choices[0].message.content


def generate_response_anthropic(query: str, context: str, chat_history: list = None) -> str:
    """Generate response using Anthropic Claude."""
    from anthropic import Anthropic
    
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    messages = []
    
    # Add chat history if provided
    if chat_history:
        for msg in chat_history[-6:]:
            messages.append(msg)
    
    # Create the user message with context
    user_message = f"""Based on the following Dublin City Council planning records, please answer this question:

**Question:** {query}

**Retrieved Planning Records:**
{context}

Please provide a clear, accurate answer based on these records. Cite specific planning reference numbers where relevant."""
    
    messages.append({"role": "user", "content": user_message})
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        system=SYSTEM_PROMPT,
        messages=messages,
        temperature=0.1,
        max_tokens=2000
    )
    
    return response.content[0].text


def query_planning(query: str, chat_history: list = None, collection=None) -> dict:
    """
    Full RAG pipeline: retrieve context and generate response.
    
    Args:
        query: User's question
        chat_history: Previous conversation messages
        collection: ChromaDB collection (optional, will create if not provided)
    
    Returns:
        dict with 'answer', 'sources', and 'context'
    """
    # Retrieve relevant records
    context, raw_results = retrieve_context(query, collection=collection)
    
    # Determine which LLM to use
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY not found. Set it in .env or switch LLM_PROVIDER to openai.")
        answer = generate_response_anthropic(query, context, chat_history)
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found. Set it in .env.")
        answer = generate_response_openai(query, context, chat_history)
    
    # Extract source references for citation
    sources = []
    for result in raw_results[:5]:  # Top 5 sources
        meta = result['metadata']
        sources.append({
            "ref": meta.get('ref', 'Unknown'),
            "location": meta.get('location', 'Unknown'),
            "decision": meta.get('decision', 'Unknown'),
            "relevance": f"{result['relevance']:.2f}"
        })
    
    return {
        "answer": answer,
        "sources": sources,
        "context": context,
        "num_results": len(raw_results)
    }


# Quick test
if __name__ == "__main__":
    print("Testing RAG engine...")
    print()
    
    test_queries = [
        "What planning applications were submitted in Drumcondra recently?",
        "Were any applications refused in Dublin 8?",
        "Tell me about extensions in Rathmines",
    ]
    
    collection = get_collection()
    
    for query in test_queries:
        print(f"Q: {query}")
        print("-" * 50)
        result = query_planning(query, collection=collection)
        print(f"A: {result['answer'][:500]}...")
        print(f"Sources: {len(result['sources'])} records retrieved")
        print()
