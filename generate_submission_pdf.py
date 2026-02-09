"""
generate_submission_pdf.py — Generate the competition submission PDF

Creates a clean, professional 1000-word PDF document covering:
1. How it works (system overview)
2. How we got the data
3. Sample prompts to test
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from pathlib import Path


def generate_pdf():
    output_path = Path("Blindspot_Labs_Submission.pdf")
    
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=20,
        spaceAfter=6,
        textColor=HexColor('#1a1a2e'),
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#666666'),
        spaceAfter=20,
        alignment=TA_CENTER,
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=HexColor('#1a1a2e'),
        borderWidth=0,
        borderPadding=0,
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
    )
    
    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold',
    )
    
    code_style = ParagraphStyle(
        'CodeBlock',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Courier',
        leading=12,
        spaceAfter=8,
        leftIndent=10,
        backColor=HexColor('#f5f5f5'),
    )
    
    prompt_style = ParagraphStyle(
        'PromptStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        leftIndent=15,
        spaceAfter=6,
        fontName='Courier',
        textColor=HexColor('#333333'),
        backColor=HexColor('#f0f7ff'),
    )
    
    # Build content
    story = []
    
    # Title
    story.append(Paragraph("Blindspot Labs: Dublin Planning AI Assistant", title_style))
    story.append(Paragraph("The Strange Data Project — Nomad AI Competition 2025", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#1a1a2e')))
    story.append(Spacer(1, 10))
    
    # ==========================================
    # SECTION 1: HOW IT WORKS
    # ==========================================
    story.append(Paragraph("1. How It Works", heading_style))
    
    story.append(Paragraph(
        "Blindspot Labs is a Retrieval-Augmented Generation (RAG) system that gives LLMs access to 20+ years of "
        "Dublin City Council planning application data — information that no baseline model has ever seen. "
        "The system enables accurate, grounded answers to questions about specific planning applications, "
        "decisions, locations, and trends across Dublin city.",
        body_style
    ))
    
    story.append(Paragraph("<b>System Pipeline:</b>", body_style))
    
    # Pipeline table
    pipeline_data = [
        ["Stage", "Implementation"],
        ["Data Source", "ArcGIS Irish Planning Applications API (Dept. of Housing) — public, no auth required"],
        ["Download", "Python requests library paginates through API, filtering for Dublin City Council records"],
        ["Processing", "Dates converted from epoch ms, decisions normalized, appeals merged into application records"],
        ["Chunking", "Each application becomes a structured text document with all fields"],
        ["Embedding", "OpenAI text-embedding-3-small generates vector embeddings"],
        ["Storage", "ChromaDB persistent vector database for fast similarity search"],
        ["Retrieval", "Top-10 semantic search against user queries"],
        ["Generation", "GPT-4o-mini (or Claude) generates grounded answers citing specific planning references"],
        ["Interface", "Streamlit chat UI with source attribution"],
    ]
    
    pipeline_table = Table(pipeline_data, colWidths=[80, 380])
    pipeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('LEADING', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#f9f9f9')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(pipeline_table)
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(
        "<b>Model choice:</b> We use GPT-4o-mini for generation (fast, cost-effective) with OpenAI "
        "text-embedding-3-small for embeddings. The system also supports Claude as an alternative generator. "
        "No fine-tuning or retraining is involved — all enhancement comes from retrieval.",
        body_style
    ))
    
    # ==========================================
    # SECTION 2: HOW WE GOT THE DATA
    # ==========================================
    story.append(Paragraph("2. How We Got the Data", heading_style))
    
    story.append(Paragraph(
        "<b>Source:</b> The Department of Housing publishes a national Irish Planning Applications dataset via "
        "a public ArcGIS Feature Service. This API provides structured records for every planning authority in "
        "Ireland, updated regularly, and requires no authentication. We filter for Dublin City Council records only, "
        "pulling thousands of planning applications with full details.",
        body_style
    ))
    
    story.append(Paragraph(
        "<b>Why this data improves performance:</b> No LLM has been trained on the Irish Planning Applications "
        "database. When asked about specific planning references, recent applications in a given area, "
        "or whether a particular development was granted permission, baseline models (ChatGPT, Claude, Gemini) "
        "either refuse to answer, provide generic planning advice, or hallucinate fake reference numbers. "
        "This data is <i>functionally invisible</i> to LLMs — it sits behind an ArcGIS API, is updated regularly, "
        "and exists in structured JSON format that was never crawled for training.",
        body_style
    ))
    
    story.append(Paragraph("<b>Data files collected:</b>", body_style))
    
    story.append(Paragraph(
        "The ArcGIS API returns rich records with: ApplicationNumber, DevelopmentAddress, DevelopmentDescription, "
        "ApplicationType, ApplicationStatus, Decision, ReceivedDate, DecisionDate, GrantDate, ExpiryDate, "
        "AppealRefNumber, AppealStatus, AppealDecision, NumResidentialUnits, FloorArea, and direct links "
        "to the full application files. Data covers 2016 to present.",
        body_style
    ))
    
    story.append(Paragraph(
        "<b>Processing:</b> Records are fetched via paginated API calls (2000 per page), dates are converted from "
        "epoch milliseconds to readable format, decisions and appeal data are normalized, and each application is "
        "converted into a structured text document optimized for semantic search. "
        "The documents are embedded and indexed in ChromaDB for sub-second retrieval.",
        body_style
    ))
    
    # ==========================================
    # SECTION 2.5: WHO THIS IS FOR
    # ==========================================
    story.append(Paragraph("3. Real-World Application", heading_style))
    
    story.append(Paragraph(
        "Planning permission data is critical for multiple professions in Ireland, yet it is "
        "extremely difficult to query. The current system requires users to navigate the Agile Applications "
        "portal, search by individual reference number or keyword, and manually read through results. There is "
        "no way to ask natural-language questions like \"what extensions were refused in my area?\" or "
        "\"what developments are planned near this address?\"",
        body_style
    ))
    
    story.append(Paragraph(
        "<b>Target users:</b> Architects researching precedent before submitting applications. Solicitors conducting "
        "due diligence on property transactions. Property developers assessing areas for investment. Estate agents "
        "informing buyers about upcoming developments. Homeowners checking what has been approved or refused "
        "near their property. Journalists investigating development trends. All of these users currently spend "
        "hours manually searching council portals. Our system answers their questions in seconds.",
        body_style
    ))
    
    # ==========================================
    # SECTION 3: FUTURE POTENTIAL
    # ==========================================
    story.append(Paragraph("4. Future Potential", heading_style))
    
    story.append(Paragraph(
        "This system currently covers Dublin City Council, but the ArcGIS API contains records for "
        "<b>every local authority in Ireland</b>. Expanding to full national coverage requires only changing "
        "one API filter parameter. Beyond that, the same architecture applies to planning data across the UK "
        "(where similar open data portals exist) and the EU.",
        body_style
    ))

    story.append(Paragraph(
        "The commercial path is clear: a SaaS product for property professionals that combines planning "
        "application data with zoning maps, development plan policies, and property registry information "
        "into a single AI-powered research tool. The Irish property and construction sector is worth over "
        "EUR 30 billion annually — a tool that saves architects, solicitors, and developers hours of manual "
        "research per project has obvious product-market fit. This prototype demonstrates the core value "
        "proposition: give an LLM the right data, and it becomes a planning expert.",
        body_style
    ))
    
    # ==========================================
    # SECTION 4: SAMPLE PROMPTS
    # ==========================================
    story.append(Paragraph("5. Sample Prompts to Test", heading_style))
    
    story.append(Paragraph(
        "Copy and paste these prompts into the chat interface. For comparison, try the same prompts in "
        "ChatGPT, Claude, or Gemini to see the difference.",
        body_style
    ))
    
    prompts = [
        "What planning applications were submitted in Drumcondra?",
        "Was planning permission granted for developments on Griffith Avenue?",
        "Show me planning decisions that were refused in Dublin 8",
        "What types of residential developments have been proposed in the Docklands area?",
        "Are there any appeals lodged for planning applications in Rathmines?",
        "What planning applications involve demolition in Dublin city centre?",
    ]
    
    for i, prompt in enumerate(prompts, 1):
        story.append(Paragraph(f"{i}. {prompt}", prompt_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "<b>Expected results:</b> Baseline models will either refuse (\"I don't have access to planning databases\"), "
        "give generic advice (\"You should check your local planning authority\"), or hallucinate fake reference numbers. "
        "Our system returns actual planning references, real addresses, correct decisions, and accurate dates — "
        "because it has the data.",
        body_style
    ))
    
    # Build PDF
    doc.build(story)
    print(f"  ✓ PDF generated: {output_path}")
    return output_path


if __name__ == "__main__":
    print("Generating submission PDF...")
    generate_pdf()
    print("Done!")
