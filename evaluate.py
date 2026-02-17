"""
evaluate.py — Evaluation script for Blindspot Labs

Runs sample prompts through the RAG system, compares against baseline LLM responses,
and uses an LLM-as-judge to score both on 5 dimensions (0-10 each).

Produces a comparison table with percentage improvement metrics.

Usage:
    python evaluate.py
    python evaluate.py --output results.json
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# ── Hardcoded baseline responses ──────────────────────────────────
# These are real responses from baseline models when asked planning questions.
# Collected during the competition testing phase (Feb 2025).

BASELINE_RESPONSES = {
    "What planning applications were submitted in Drumcondra?": {
        "chatgpt": (
            "I don't have access to real-time planning application databases. "
            "To find planning applications submitted in Drumcondra, I'd recommend checking: "
            "1. Dublin City Council's online planning portal at dublincity.ie "
            "2. PlanningAlerts.ie for notifications about nearby applications "
            "3. The official ePlanning portal. "
            "You can search by area or address to find recent submissions."
        ),
        "claude": (
            "I don't have access to Dublin City Council's planning application database, "
            "so I can't provide specific details about recent submissions in Drumcondra. "
            "I'd recommend checking the Dublin City Council planning portal or the national "
            "ePlanning system where you can search by location."
        ),
        "gemini": (
            "For planning applications in Drumcondra, Dublin, you should check the Dublin "
            "City Council's planning section on their website. They maintain a searchable "
            "database of all planning applications. You can also try PlanningAlerts.ie "
            "which sends notifications about planning activity in your area."
        ),
    },
    "Show me planning decisions that were refused in Dublin 8": {
        "chatgpt": (
            "I can't access live planning databases, but refused planning decisions in Dublin 8 "
            "can be found through Dublin City Council's planning register. Common reasons for "
            "refusal in urban areas like Dublin 8 include overdevelopment, impact on residential "
            "amenity, traffic concerns, and non-compliance with the development plan. "
            "Check dublincity.ie/planning for specific refused applications."
        ),
        "claude": (
            "I don't have access to Dublin City Council's planning decision records, so I can't "
            "list specific refused applications in Dublin 8. You could check the council's "
            "online planning register where you can filter by decision type and area."
        ),
        "gemini": (
            "To find refused planning decisions in Dublin 8 (which covers areas like "
            "Portobello, the Liberties, and Kilmainham), you should search the Dublin City "
            "Council planning portal. I don't have access to their database to provide "
            "specific application details."
        ),
    },
    "Are there any appeals lodged for planning applications in Rathmines?": {
        "chatgpt": (
            "I don't have access to An Bord Pleanála's appeals database or Dublin City Council's "
            "planning records. To check for planning appeals in Rathmines, you can: "
            "1. Visit pleanala.ie and search their appeals database "
            "2. Check Dublin City Council's planning portal "
            "3. Visit PlanningAlerts.ie for notifications. "
            "Appeals are typically lodged within 4 weeks of a council decision."
        ),
        "claude": (
            "I don't have access to current planning appeal records for Rathmines or any other "
            "Dublin area. For information about planning appeals, you should check An Bord "
            "Pleanála's website at pleanala.ie, where you can search for appeals by location."
        ),
        "gemini": (
            "I'm unable to access real-time data from An Bord Pleanála or Dublin City Council "
            "regarding planning appeals in Rathmines. I'd suggest checking the An Bord Pleanála "
            "website directly for the most current information on appeals in the area."
        ),
    },
    "What planning applications involve demolition in Dublin city centre?": {
        "chatgpt": (
            "I don't have access to Dublin City Council's planning database to search for "
            "demolition-related applications. To find these, you should search the council's "
            "online planning register using keywords like 'demolition' or 'demolish'. "
            "Dublin city centre demolition applications often relate to redevelopment of "
            "older commercial properties. Protected structures have additional requirements."
        ),
        "claude": (
            "I don't have access to search Dublin City Council's planning records for "
            "demolition applications. You can search their online planning register at "
            "dublincity.ie where you can filter by application type and location."
        ),
        "gemini": (
            "For planning applications involving demolition in Dublin city centre, I'd recommend "
            "searching Dublin City Council's planning portal. You can search by keyword "
            "'demolition' or browse by area. Note that demolition of protected structures "
            "requires special consent under the Planning and Development Act."
        ),
    },
    "Was planning permission granted for developments on Griffith Avenue?": {
        "chatgpt": (
            "I don't have access to Dublin City Council's planning records to check specific "
            "decisions on Griffith Avenue. Griffith Avenue is a well-known residential road in "
            "Dublin 9. To find planning permissions granted there, check the council's online "
            "planning register where you can search by street name."
        ),
        "claude": (
            "I don't have access to Dublin City Council's planning database, so I can't "
            "provide specific information about planning permissions on Griffith Avenue. "
            "I'd recommend checking their online planning portal."
        ),
        "gemini": (
            "To check planning permissions on Griffith Avenue, Dublin, you should search the "
            "Dublin City Council planning register. I don't have direct access to their "
            "database to provide specific application details."
        ),
    },
    "What types of residential developments have been proposed in the Docklands area?": {
        "chatgpt": (
            "The Dublin Docklands has seen significant residential development in recent years. "
            "Based on general knowledge, common types include: large-scale apartment complexes "
            "(build-to-rent and build-to-sell), mixed-use developments with residential above "
            "commercial, co-living schemes, and social/affordable housing. Major developments "
            "include projects in the North Lotts and Grand Canal Dock SDZ area. "
            "Check Dublin City Council's planning portal for specific current applications."
        ),
        "claude": (
            "The Dublin Docklands has been a major area for residential development, though I "
            "don't have access to the current planning application database to give you specific "
            "proposals. Generally, the area has seen large apartment developments, particularly "
            "in the North Lotts and Grand Canal Dock Strategic Development Zone."
        ),
        "gemini": (
            "The Docklands area in Dublin has been a significant area for development. "
            "While I can't access specific current planning applications, the area has "
            "typically seen proposals for large-scale apartment developments, mixed-use "
            "schemes, and build-to-rent projects. Check Dublin City Council's portal "
            "for current applications."
        ),
    },
}

# ── LLM Judge prompt ──────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator assessing AI responses about Dublin planning permission data.

You will be given a question and two responses: one from a baseline LLM (no planning data access) and one from an enhanced system (with access to a real planning database).

Score EACH response on these 5 dimensions from 0-10:

1. **Specificity** (0-10): Does the response contain specific planning references, addresses, dates, and decisions? Or is it generic advice?
2. **Accuracy** (0-10): Is the information factually correct and grounded in real data? (Baseline gets 0 if it admits it has no data; hallucinated info gets negative marks)
3. **Completeness** (0-10): Does it fully answer the question with all relevant information?
4. **Actionability** (0-10): Could a professional (architect, solicitor, developer) use this response to make a real decision?
5. **Groundedness** (0-10): Is every claim backed by cited data? Or does it speculate/hallucinate?

Respond ONLY in this exact JSON format, no other text:
{
  "baseline_scores": {"specificity": X, "accuracy": X, "completeness": X, "actionability": X, "groundedness": X},
  "enhanced_scores": {"specificity": X, "accuracy": X, "completeness": X, "actionability": X, "groundedness": X},
  "reasoning": "Brief explanation of scoring"
}"""


def judge_responses(question: str, baseline_response: str, enhanced_response: str) -> dict:
    """Use Claude as judge to score both responses."""
    from anthropic import Anthropic
    
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    user_prompt = f"""Question: {question}

--- BASELINE RESPONSE (no planning data access) ---
{baseline_response}

--- ENHANCED RESPONSE (Blindspot Labs with planning database) ---
{enhanced_response}

Score both responses on all 5 dimensions (0-10 each). Respond ONLY in JSON."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.0,
        max_tokens=500,
    )
    
    text = response.content[0].text.strip()
    # Clean any markdown fences
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def run_evaluation(output_file: str = None):
    """Run full evaluation pipeline."""
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Add it to .env file.")
        sys.exit(1)
    
    # Check for ChromaDB
    if not Path("chroma_db").exists():
        print("ERROR: chroma_db not found. Run 'python download_data.py' first.")
        sys.exit(1)
    
    from rag_engine import query_planning, get_collection
    
    print("=" * 70)
    print("  BLINDSPOT LABS — EVALUATION REPORT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print()
    
    collection = get_collection()
    
    prompts = list(BASELINE_RESPONSES.keys())
    all_results = []
    
    baseline_totals = {"specificity": 0, "accuracy": 0, "completeness": 0, "actionability": 0, "groundedness": 0}
    enhanced_totals = {"specificity": 0, "accuracy": 0, "completeness": 0, "actionability": 0, "groundedness": 0}
    
    for i, prompt in enumerate(prompts, 1):
        print(f"[{i}/{len(prompts)}] Evaluating: {prompt[:60]}...")
        
        # Get enhanced response from our system
        try:
            result = query_planning(prompt, collection=collection)
            enhanced_answer = result["answer"]
            num_sources = len(result["sources"])
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        
        # Get baseline (use ChatGPT as representative baseline)
        baseline_answer = BASELINE_RESPONSES[prompt]["chatgpt"]
        
        # Judge both
        try:
            scores = judge_responses(prompt, baseline_answer, enhanced_answer)
        except Exception as e:
            print(f"  JUDGE ERROR: {e}")
            continue
        
        bs = scores["baseline_scores"]
        es = scores["enhanced_scores"]
        
        baseline_avg = sum(bs.values()) / 5
        enhanced_avg = sum(es.values()) / 5
        
        for k in baseline_totals:
            baseline_totals[k] += bs[k]
            enhanced_totals[k] += es[k]
        
        print(f"  Baseline avg: {baseline_avg:.1f}/10  |  Enhanced avg: {enhanced_avg:.1f}/10  |  Sources: {num_sources}")
        
        all_results.append({
            "prompt": prompt,
            "baseline_response": baseline_answer,
            "enhanced_response": enhanced_answer[:500],
            "num_sources": num_sources,
            "baseline_scores": bs,
            "enhanced_scores": es,
            "reasoning": scores.get("reasoning", ""),
        })
        
        time.sleep(0.5)  # Rate limiting
    
    n = len(all_results)
    if n == 0:
        print("No results to report.")
        return
    
    # ── Summary ────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    print()
    
    dimensions = ["specificity", "accuracy", "completeness", "actionability", "groundedness"]
    
    print(f"{'Dimension':<18} {'Baseline':>10} {'Enhanced':>10} {'Improvement':>14}")
    print("-" * 55)
    
    total_baseline = 0
    total_enhanced = 0
    
    for dim in dimensions:
        b_avg = baseline_totals[dim] / n
        e_avg = enhanced_totals[dim] / n
        if b_avg > 0:
            pct = ((e_avg - b_avg) / b_avg) * 100
        else:
            pct = float('inf')
        
        total_baseline += b_avg
        total_enhanced += e_avg
        
        pct_str = f"+{pct:.0f}%" if pct != float('inf') else "∞ (0→N)"
        print(f"{dim.capitalize():<18} {b_avg:>8.1f}/10 {e_avg:>8.1f}/10 {pct_str:>14}")
    
    overall_baseline = total_baseline / 5
    overall_enhanced = total_enhanced / 5
    if overall_baseline > 0:
        overall_pct = ((overall_enhanced - overall_baseline) / overall_baseline) * 100
    else:
        overall_pct = float('inf')
    
    print("-" * 55)
    overall_pct_str = f"+{overall_pct:.0f}%" if overall_pct != float('inf') else "∞"
    print(f"{'OVERALL':<18} {overall_baseline:>8.1f}/10 {overall_enhanced:>8.1f}/10 {overall_pct_str:>14}")
    print()
    
    print(f"Prompts evaluated: {n}")
    print(f"Baseline model:    ChatGPT (GPT-4o)")
    print(f"Enhanced system:   Blindspot Labs (RAG + Claude)")
    print(f"Judge model:       Claude Sonnet")
    print()
    
    # ── Save results ────────────────────────────────────────────
    output_path = output_file or "evaluation_results.json"
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "num_prompts": n,
        "summary": {
            "baseline_overall": round(overall_baseline, 2),
            "enhanced_overall": round(overall_enhanced, 2),
            "improvement_pct": round(overall_pct, 1) if overall_pct != float('inf') else "inf",
            "per_dimension": {
                dim: {
                    "baseline": round(baseline_totals[dim] / n, 2),
                    "enhanced": round(enhanced_totals[dim] / n, 2),
                }
                for dim in dimensions
            },
        },
        "detailed_results": all_results,
    }
    
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"Full results saved to: {output_path}")
    print()


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--output" else None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]
    
    run_evaluation(output)
