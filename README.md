# Blindspot Labs: Dublin Planning Permission AI Assistant

## 🏗️ The Strange Data Project — Nomad AI Competition

An AI-powered planning permission assistant for Dublin City that gives LLMs access to data they've never seen: **20+ years of Dublin City Council planning applications, decisions, appeals, and zoning data**.

Baseline models (ChatGPT, Claude, Gemini) hallucinate or refuse when asked about specific Dublin planning applications. **This system answers accurately using real data.**

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

Create a `.env` file:

```
OPENAI_API_KEY=sk-your-key-here
```

Or use Anthropic:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_PROVIDER=anthropic
```

### 3. Download and process the data

```bash
python download_data.py
```

This downloads the official Dublin City Council open data CSVs and processes them into the vector database. Takes ~5-10 minutes depending on your connection.

### 4. Run the chat interface

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## How It Works

```
Dublin City Council Open Data (CSVs)
        │
        ▼
   download_data.py
   (Download + Clean + Structure)
        │
        ▼
   build_vectordb.py  
   (Chunk + Embed + Store in ChromaDB)
        │
        ▼
   rag_engine.py
   (Query → Retrieve → Augment → Generate)
        │
        ▼
   app.py (Streamlit Chat Interface)
```

### Data Sources
- **DCC_DUBLINK_BASE.csv** — All planning applications from 2003-present (reference, dates, location, proposal, decision, stage)
- **DCC_DUBLINK_APPEAL.csv** — Appeal records for contested decisions
- **DCC_DUBLINK_FURINFO.csv** — Further information requests
- **DCC_PlanApps.csv** — Spatial/coordinate data for applications

### Pipeline
1. **Download**: Fetch latest CSVs from Dublin City Council's Smart Dublin open data portal
2. **Clean**: Parse dates, normalize text, merge spatial data with application records
3. **Chunk**: Create semantically meaningful chunks combining application details
4. **Embed**: Generate embeddings using OpenAI `text-embedding-3-small`
5. **Store**: Index in ChromaDB for fast similarity search
6. **Retrieve**: Top-k semantic search on user queries
7. **Generate**: LLM synthesizes answer grounded in retrieved planning records

---

## Sample Test Prompts

Try these in the chat interface:

1. "What planning applications were submitted in Drumcondra in January 2025?"
2. "Was planning permission granted for a two-storey extension at any address on Griffith Avenue?"
3. "Show me recent planning decisions that were refused in Dublin 8"
4. "What types of developments have been proposed in the Docklands area recently?"
5. "Are there any appeals lodged for planning applications in Rathmines?"
6. "What planning applications involve demolition in Dublin city centre?"
7. "Tell me about large-scale residential developments proposed in Dublin 1"
8. "What conditions are typically attached to planning permissions for house extensions?"

---

## Project Structure

```
blindspot-labs/
├── README.md
├── requirements.txt
├── .env.example
├── download_data.py      # Data acquisition & cleaning
├── build_vectordb.py     # Embedding & ChromaDB indexing
├── rag_engine.py         # RAG pipeline & LLM integration
├── app.py                # Streamlit chat interface
├── data/                 # Downloaded CSVs (created by download_data.py)
└── chroma_db/            # Vector database (created by build_vectordb.py)
```

---

## Evaluation: Why This Beats Baseline

| Question | Baseline (ChatGPT/Claude) | This System |
|----------|--------------------------|-------------|
| "Planning apps in Drumcondra Jan 2025?" | ❌ Refuses or hallucinates | ✅ Lists actual applications with refs |
| "Was 1234/24 granted?" | ❌ Cannot access | ✅ Returns decision + conditions |
| "Refused applications in Dublin 8?" | ❌ Generic advice | ✅ Specific refusals with reasons |
| "Appeals in Rathmines?" | ❌ No data | ✅ Real appeal records |

---

## License

Data: Creative Commons Attribution (Dublin City Council Open Data)
Code: MIT
