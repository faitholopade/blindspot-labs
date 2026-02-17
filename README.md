# Blindspot Labs: Dublin Planning Permission AI Assistant

## 🏆 Awards & Recognition
- **2nd Place Winner** — [Nomad AI Competition 2025](http://nomadai.ie/events/nomad-ai-competition-2025)
- **Prize:** €1,500

## 🏗️ The Strange Data Project — Nomad AI Competition

An AI-powered planning permission assistant for Dublin that gives LLMs access to data they've never seen: **20+ years of Dublin City Council planning applications, decisions, appeals, and zoning data** from the Dept. of Housing ArcGIS API.

Baseline models (ChatGPT, Claude, Gemini) hallucinate or refuse when asked about specific Dublin planning applications. **This system answers accurately using real data.**

**Powered by Anthropic Claude.** Embeddings are local (sentence-transformers, no API key needed). Only one key required: `ANTHROPIC_API_KEY`.

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
Dept. of Housing ArcGIS API (Public, no auth)
  → download_data.py (fetch + clean + classify)
  → build_vectordb.py (embed locally with MiniLM + index in ChromaDB)
  → rag_engine.py (query → retrieve → augment → generate with Claude)
  → app.py (Streamlit chat interface with stakeholder roles)
```

### Data Source
- **Irish Planning Applications API** — ArcGIS Feature Service, Dept. of Housing
- Public, no authentication required
- We filter to Dublin City Council; one parameter change covers all 31 Irish local authorities

### Data Classification

Each record is automatically classified during processing:

- **Development category**: residential, commercial, industrial, education, public/institutional, modification, demolition
- **Land type**: public land, public housing, private land
- **Development scale**: single, small multi-unit, medium (10+), large (50+)

This classification enables targeted access for different stakeholders — a developer looking at large-scale opportunities on public land sees different data than a homeowner checking extensions on their street.

### Stakeholder Roles

The app includes an "I am a..." selector that tailors sample questions by role:

| Role | Focus |
|------|-------|
| Property Developer | Large sites, refused applications (opportunity), public land |
| Architect | Precedent for extensions, conditions, change of use |
| Solicitor | Appeals, pending applications, due diligence |
| Estate Agent | Nearby developments, approved schemes |
| Homeowner | What's happening on my street |
| Journalist | Trends, public land, social housing |

---

## Evaluation

Run `python evaluate.py` to reproduce. Uses Claude as LLM-as-judge scoring both baseline and enhanced responses (0-10) across 5 dimensions:

| Dimension | Baseline (ChatGPT) | Blindspot Labs | Improvement |
|-----------|:------------------:|:--------------:|:-----------:|
| Specificity | ~1/10 | ~8/10 | +700% |
| Accuracy | ~2/10 | ~9/10 | +350% |
| Completeness | ~2/10 | ~8/10 | +300% |
| Actionability | ~1/10 | ~8/10 | +700% |
| Groundedness | ~1/10 | ~9/10 | +800% |
| **Overall** | **~1.4/10** | **~8.4/10** | **+500%** |

---

## Project Structure

```
blindspot-labs/
├── README.md
├── requirements.txt
├── download_data.py      # Data acquisition + cleaning + classification
├── build_vectordb.py     # Local embedding (MiniLM) + ChromaDB indexing
├── rag_engine.py         # RAG pipeline (retrieve + generate with Claude)
├── app.py                # Streamlit chat interface with stakeholder roles
├── evaluate.py           # LLM-as-judge evaluation (Claude)
├── data/                 # Downloaded + classified records
└── chroma_db/            # Vector database
```

---

## Future Potential

- **Today**: Dublin City Council (thousands of records, 20+ years)
- **Next**: All of Ireland — one API parameter change, 31 local authorities
- **Vision**: SaaS for property professionals. Public planning data + private datasets (valuations, zoning, development plan policies). Targeted subscriptions by stakeholder role. €30B Irish property market.