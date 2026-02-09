"""
build_vectordb.py — Build ChromaDB vector database from processed planning records

Takes the cleaned JSON records and:
1. Creates semantically meaningful text chunks for each application
2. Generates embeddings using OpenAI text-embedding-3-small
3. Stores everything in a local ChromaDB collection
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data")
CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "dublin_planning"
BATCH_SIZE = 100  # ChromaDB batch size for adding documents
EMBEDDING_MODEL = "text-embedding-3-small"


def create_document_text(record: dict) -> str:
    """Create a rich text document from a planning record for embedding."""
    parts = []
    
    # Header
    ref = record.get('ref', 'Unknown')
    parts.append(f"Planning Application Reference: {ref}")
    
    # Location
    location = record.get('location', '')
    if location:
        parts.append(f"Location: {location}")
    
    # Proposal description (use long proposal if available, else short)
    long_proposal = record.get('long_proposal', '')
    proposal = record.get('proposal', '')
    if long_proposal and long_proposal != proposal:
        parts.append(f"Proposal: {long_proposal}")
    elif proposal:
        parts.append(f"Proposal: {proposal}")
    
    # Application type
    app_type = record.get('app_type', '')
    if app_type:
        parts.append(f"Application Type: {app_type}")
    
    # Dates
    reg_date = record.get('reg_date', '')
    if reg_date:
        parts.append(f"Registration Date: {reg_date}")
    
    app_date = record.get('app_date', '')
    if app_date:
        parts.append(f"Application Date: {app_date}")
    
    # Decision
    decision = record.get('decision', '')
    if decision:
        parts.append(f"Decision: {decision}")
    
    dec_date = record.get('dec_date', '')
    if dec_date:
        parts.append(f"Decision Date: {dec_date}")
    
    grant_date = record.get('grant_date', '')
    if grant_date:
        parts.append(f"Final Grant Date: {grant_date}")
    
    # Stage
    stage = record.get('stage', '')
    if stage:
        parts.append(f"Current Stage: {stage}")
    
    # Coordinates
    lat = record.get('lat', '')
    lon = record.get('lon', '')
    if lat and lon and lat != 'nan' and lon != 'nan':
        parts.append(f"Coordinates: {lat}, {lon}")
    
    # Appeals
    if record.get('has_appeal'):
        parts.append("Status: This application has been appealed")
        appeal_details = record.get('appeal_details', [])
        if appeal_details:
            for i, appeal in enumerate(appeal_details[:3]):  # Limit to 3 appeals
                appeal_text = "; ".join(f"{k}: {v}" for k, v in appeal.items() if v and v != 'nan')
                if appeal_text:
                    parts.append(f"Appeal {i+1}: {appeal_text}")
    
    return "\n".join(parts)


def create_metadata(record: dict) -> dict:
    """Create metadata dict for ChromaDB storage."""
    metadata = {
        "ref": record.get('ref', ''),
        "location": record.get('location', '')[:500],  # ChromaDB metadata size limit
        "decision": record.get('decision', ''),
        "reg_date": record.get('reg_date', ''),
        "dec_date": record.get('dec_date', ''),
        "app_type": record.get('app_type', ''),
        "stage": record.get('stage', ''),
        "has_appeal": str(record.get('has_appeal', False)),
        "proposal_short": record.get('proposal', '')[:500],
    }
    
    # Add coordinates if available
    lat = record.get('lat', '')
    lon = record.get('lon', '')
    if lat and lon and lat != 'nan' and lon != 'nan':
        try:
            metadata['lat'] = float(lat)
            metadata['lon'] = float(lon)
        except (ValueError, TypeError):
            pass
    
    # Clean: ChromaDB doesn't allow None values in metadata
    return {k: v for k, v in metadata.items() if v is not None and v != ''}


def build_vector_database():
    """Main function to build the ChromaDB vector database."""
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ✗ OPENAI_API_KEY not found in .env file")
        print("    OpenAI API key is required for generating embeddings.")
        print("    Create a .env file with: OPENAI_API_KEY=sk-your-key-here")
        sys.exit(1)
    
    # Load processed records
    records_path = DATA_DIR / "processed_records.json"
    if not records_path.exists():
        print("  ✗ processed_records.json not found. Run download_data.py first.")
        sys.exit(1)
    
    print("  Loading processed records...")
    with open(records_path, 'r', encoding='utf-8') as f:
        records = json.load(f)
    print(f"    Loaded {len(records):,} records")
    
    # Import ChromaDB
    import chromadb
    from chromadb.utils import embedding_functions
    
    # Set up OpenAI embedding function
    print(f"  Setting up embeddings ({EMBEDDING_MODEL})...")
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL
    )
    
    # Create/reset ChromaDB
    print(f"  Initializing ChromaDB at {CHROMA_DIR}...")
    CHROMA_DIR.mkdir(exist_ok=True)
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    # Delete existing collection if it exists
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"    Deleted existing '{COLLECTION_NAME}' collection")
    except Exception:
        pass
    
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=openai_ef,
        metadata={"description": "Dublin City Council Planning Applications"}
    )
    print(f"    Created collection '{COLLECTION_NAME}'")
    
    # Create documents and add to ChromaDB in batches
    print(f"\n  Embedding and indexing {len(records):,} records...")
    print(f"    Batch size: {BATCH_SIZE}")
    print(f"    Estimated batches: {(len(records) + BATCH_SIZE - 1) // BATCH_SIZE}")
    print()
    
    total_added = 0
    errors = 0
    
    for batch_start in range(0, len(records), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(records))
        batch = records[batch_start:batch_end]
        
        documents = []
        metadatas = []
        ids = []
        
        for i, record in enumerate(batch):
            doc_text = create_document_text(record)
            metadata = create_metadata(record)
            doc_id = f"plan_{record.get('ref', f'unknown_{batch_start + i}')}"
            
            # Skip empty documents
            if len(doc_text.strip()) < 20:
                continue
            
            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(doc_id)
        
        if not documents:
            continue
        
        try:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            total_added += len(documents)
            pct = (batch_end / len(records)) * 100
            print(f"\r    Progress: {pct:.1f}% — {total_added:,} records indexed", end="")
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"\n    Warning: Batch {batch_start}-{batch_end} failed: {e}")
            elif errors == 6:
                print(f"\n    (Suppressing further error messages...)")
    
    print(f"\n\n  ✓ Vector database built!")
    print(f"    Total indexed: {total_added:,} records")
    if errors > 0:
        print(f"    Failed batches: {errors}")
    print(f"    Database location: {CHROMA_DIR}")
    
    # Quick test query
    print("\n  Running test query: 'house extension Rathmines'...")
    results = collection.query(
        query_texts=["house extension Rathmines"],
        n_results=3
    )
    
    if results and results['documents'] and results['documents'][0]:
        print(f"    Found {len(results['documents'][0])} results:")
        for i, doc in enumerate(results['documents'][0][:2]):
            # Show first 150 chars of each result
            preview = doc[:150].replace('\n', ' ')
            print(f"      {i+1}. {preview}...")
    else:
        print("    Warning: Test query returned no results")
    
    return True


if __name__ == "__main__":
    print()
    print("Building vector database from processed planning records...")
    print()
    build_vector_database()
