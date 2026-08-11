"""Generate docs/presentation/parking_chatbot.pptx."""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path("docs/presentation/parking_chatbot.pptx")
OUT.parent.mkdir(parents=True, exist_ok=True)

# ── Colour palette ──────────────────────────────────────────────────────────
NAVY   = RGBColor(0x1A, 0x37, 0x6C)
TEAL   = RGBColor(0x00, 0x7A, 0x87)
ORANGE = RGBColor(0xF5, 0x7C, 0x00)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
LGRAY  = RGBColor(0xF4, 0xF6, 0xF8)
DGRAY  = RGBColor(0x44, 0x44, 0x44)
GREEN  = RGBColor(0x2E, 0x7D, 0x32)
RED    = RGBColor(0xC6, 0x28, 0x28)

W, H = Inches(13.33), Inches(7.5)   # 16:9 widescreen

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H

blank = prs.slide_layouts[6]   # completely blank


# ── Helpers ─────────────────────────────────────────────────────────────────

def add_rect(slide, x, y, w, h, fill, alpha=None):
    shape = slide.shapes.add_shape(1, x, y, w, h)   # MSO_SHAPE_TYPE.RECTANGLE
    shape.line.fill.background()
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    return shape


def add_text(slide, text, x, y, w, h, size=18, bold=False, color=DGRAY,
             align=PP_ALIGN.LEFT, wrap=True):
    txb = slide.shapes.add_textbox(x, y, w, h)
    tf  = txb.text_frame
    tf.word_wrap = wrap
    p   = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = Pt(size)
    run.font.bold  = bold
    run.font.color.rgb = color
    return txb


def header_band(slide, title, subtitle=None):
    """Dark navy band across the top."""
    add_rect(slide, 0, 0, W, Inches(1.4), NAVY)
    add_text(slide, title, Inches(0.4), Inches(0.15), Inches(12.5), Inches(0.8),
             size=28, bold=True, color=WHITE)
    if subtitle:
        add_text(slide, subtitle, Inches(0.4), Inches(0.85), Inches(12.5), Inches(0.45),
                 size=14, color=RGBColor(0xB0, 0xC8, 0xE0))


def bullet_box(slide, items, x, y, w, h, title=None, title_color=TEAL):
    if title:
        add_text(slide, title, x, y, w, Inches(0.4), size=15, bold=True, color=title_color)
        y += Inches(0.38)
        h -= Inches(0.38)
    txb = slide.shapes.add_textbox(x, y, w, h)
    tf  = txb.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(3)
        run = p.add_run()
        run.text = f"• {item}"
        run.font.size  = Pt(13)
        run.font.color.rgb = DGRAY


def code_box(slide, lines, x, y, w, h):
    add_rect(slide, x, y, w, h, RGBColor(0x28, 0x2C, 0x34))
    txb = slide.shapes.add_textbox(x + Inches(0.12), y + Inches(0.08),
                                   w - Inches(0.24), h - Inches(0.16))
    tf  = txb.text_frame
    tf.word_wrap = False
    first = True
    for line in lines:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        run = p.add_run()
        run.text = line
        run.font.size  = Pt(10)
        run.font.color.rgb = RGBColor(0xAB, 0xB2, 0xBF)
        run.font.name  = "Courier New"


def flow_box(slide, label, x, y, w=Inches(1.7), h=Inches(0.55), fill=TEAL):
    add_rect(slide, x, y, w, h, fill)
    add_text(slide, label, x, y + Inches(0.05), w, h - Inches(0.1),
             size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)


def arrow(slide, x, y, length=Inches(0.25), vertical=False):
    if vertical:
        line = slide.shapes.add_connector(1, x, y, x, y + length)
    else:
        line = slide.shapes.add_connector(1, x, y, x + length, y)
    line.line.color.rgb = DGRAY
    line.line.width     = Pt(1.5)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, NAVY)
add_rect(s, 0, Inches(2.8), W, Inches(2.0), TEAL)

add_text(s, "🅿", Inches(0.5), Inches(0.3), Inches(1.5), Inches(1.5),
         size=72, color=WHITE, align=PP_ALIGN.CENTER)

add_text(s, "CityPark Intelligent Parking Chatbot",
         Inches(2.0), Inches(0.5), Inches(10.8), Inches(1.1),
         size=36, bold=True, color=WHITE)
add_text(s, "Stage 1 — RAG Foundation",
         Inches(2.0), Inches(1.45), Inches(10.8), Inches(0.7),
         size=22, color=RGBColor(0xB0, 0xC8, 0xE0))

add_text(s, "Solution Overview  ·  Architecture  ·  RAG Pipeline  ·  Guard Rails  ·  Reservation  ·  Evaluation",
         Inches(0.5), Inches(3.0), Inches(12.3), Inches(0.6),
         size=14, color=WHITE, align=PP_ALIGN.CENTER)

add_text(s, "Built with Python 3.13  ·  LangChain  ·  LangGraph  ·  Milvus  ·  PostgreSQL  ·  FastAPI  ·  Streamlit",
         Inches(0.5), Inches(3.55), Inches(12.3), Inches(0.5),
         size=12, color=RGBColor(0xB0, 0xC8, 0xE0), align=PP_ALIGN.CENTER)

add_text(s, "2026-08-11", Inches(11.5), Inches(6.9), Inches(1.5), Inches(0.4),
         size=11, color=RGBColor(0x80, 0xA0, 0xC0), align=PP_ALIGN.RIGHT)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Solution Overview
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "Solution Overview", "What was built and why")

# Problem
add_rect(s, Inches(0.3), Inches(1.55), Inches(5.9), Inches(2.5), WHITE)
bullet_box(s, [
    "Customers ring the facility for basic info",
    "Staff answer repetitive questions about prices, hours, availability",
    "Reservation process is manual and error-prone",
    "No 24/7 self-service channel exists",
], Inches(0.45), Inches(1.55), Inches(5.6), Inches(2.5), title="❌  Problem", title_color=RED)

# Solution
add_rect(s, Inches(6.5), Inches(1.55), Inches(6.5), Inches(2.5), WHITE)
bullet_box(s, [
    "LLM-powered chatbot with RAG over parking knowledge base",
    "Static Q&A: general info, location, rules, booking process",
    "Dynamic data: live prices, hours, availability from PostgreSQL",
    "Reservation collection via LangGraph sub-workflow",
    "Two-layer guard-rails (blocklist + Presidio PII)",
], Inches(6.65), Inches(1.55), Inches(6.2), Inches(2.5), title="✅  Solution", title_color=GREEN)

# 4 user stories
stories = [
    ("US1", "Ask a Parking Question", "P1 MVP", NAVY),
    ("US2", "Get Prices / Hours / Availability", "P1 MVP", TEAL),
    ("US3", "Make a Reservation", "P2", ORANGE),
    ("US4", "Guard Rails & Safety", "P1 MVP", GREEN),
]
for i, (code, name, prio, col) in enumerate(stories):
    bx = Inches(0.3) + i * Inches(3.28)
    add_rect(s, bx, Inches(4.3), Inches(3.1), Inches(0.45), col)
    add_text(s, f"{code} — {name}  [{prio}]",
             bx + Inches(0.1), Inches(4.33), Inches(3.0), Inches(0.38),
             size=12, bold=True, color=WHITE)
    add_rect(s, bx, Inches(4.75), Inches(3.1), Inches(2.4), WHITE)

add_text(s, "Delivery scope: 4 user stories · 26 unit tests · CI on GitHub Actions · Docker Compose full-stack",
         Inches(0.3), Inches(7.15), Inches(12.7), Inches(0.3),
         size=11, color=DGRAY, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — System Architecture
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "System Architecture", "Component overview and data flow")

# User layer
add_rect(s, Inches(0.3), Inches(1.6), Inches(2.5), Inches(0.55), TEAL)
add_text(s, "User  (Browser)", Inches(0.3), Inches(1.62), Inches(2.5), Inches(0.5),
         size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

# Streamlit
add_rect(s, Inches(0.3), Inches(2.45), Inches(2.5), Inches(0.55), NAVY)
add_text(s, "Streamlit UI :8501", Inches(0.3), Inches(2.47), Inches(2.5), Inches(0.5),
         size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
arrow(s, Inches(1.55), Inches(2.15), Inches(0.01), vertical=True)
arrow(s, Inches(1.55), Inches(2.3), Inches(0.01), vertical=True)

# FastAPI
add_rect(s, Inches(3.2), Inches(2.45), Inches(2.8), Inches(0.55), NAVY)
add_text(s, "FastAPI  :8000\n/chat  /health", Inches(3.2), Inches(2.45), Inches(2.8), Inches(0.55),
         size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
arrow(s, Inches(2.8), Inches(2.72))

# LangGraph
add_rect(s, Inches(6.4), Inches(1.8), Inches(3.5), Inches(4.5), WHITE)
add_text(s, "LangGraph Workflow", Inches(6.4), Inches(1.82), Inches(3.5), Inches(0.38),
         size=13, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
add_rect(s, Inches(6.4), Inches(1.8), Inches(3.5), Inches(0.42), NAVY)
add_text(s, "LangGraph Workflow", Inches(6.4), Inches(1.82), Inches(3.5), Inches(0.38),
         size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

nodes_list = [
    "route_intent",
    "retrieve_and_generate",
    "dynamic_data_node",
    "reservation_collector_node",
    "reservation_validator_node",
    "guard_rails_node",
    "respond",
]
for i, n in enumerate(nodes_list):
    ny = Inches(2.35) + i * Inches(0.51)
    add_rect(s, Inches(6.55), ny, Inches(3.2), Inches(0.42), LGRAY)
    add_text(s, n, Inches(6.6), ny + Inches(0.04), Inches(3.1), Inches(0.34),
             size=11, color=DGRAY)

arrow(s, Inches(6.0), Inches(2.72))

# External services
ext = [
    (Inches(10.3), Inches(2.0),  "OpenAI\nGPT-4o + embeddings", ORANGE),
    (Inches(10.3), Inches(3.2),  "Milvus\nVector DB :19530",     TEAL),
    (Inches(10.3), Inches(4.4),  "PostgreSQL\nRelational :5432",  NAVY),
    (Inches(10.3), Inches(5.6),  "Presidio\nPII Guard Rails",    GREEN),
]
for ex, ey, el, ec in ext:
    add_rect(s, ex, ey, Inches(2.7), Inches(0.85), ec)
    add_text(s, el, ex, ey + Inches(0.08), Inches(2.7), Inches(0.7),
             size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    arrow(s, Inches(9.9), ey + Inches(0.42))

add_text(s, "Docker Compose: etcd · minio · milvus · postgres · api · ui — all health-checked",
         Inches(0.3), Inches(7.1), Inches(12.7), Inches(0.35),
         size=11, color=DGRAY, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — RAG Pipeline
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "RAG Pipeline — 8 Stages", "From Markdown documents to grounded LLM response")

stages = [
    ("1  Ingest",      "DirectoryLoader\nMarkdown files",     NAVY),
    ("2  Chunk",       "512 tokens\n50-token overlap",        TEAL),
    ("3  Embed",       "text-embedding-3-small\n1536-dim",    TEAL),
    ("4  Store",       "Milvus\nCosine IVF_FLAT",             TEAL),
    ("5  Retrieve",    "top-k = 5\nCosine similarity",        NAVY),
    ("6  Context",     "Concatenate\nchunk content",          NAVY),
    ("7  Generate",    "GPT-4o\ngrounded prompt",             ORANGE),
    ("8  Filter",      "Blocklist +\nPresidio PII",           GREEN),
]

bw = Inches(1.42)
for i, (title, detail, col) in enumerate(stages):
    bx = Inches(0.25) + i * (bw + Inches(0.08))
    by = Inches(1.7)
    add_rect(s, bx, by, bw, Inches(0.45), col)
    add_text(s, title, bx, by + Inches(0.05), bw, Inches(0.35),
             size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_rect(s, bx, by + Inches(0.45), bw, Inches(1.0), WHITE)
    add_text(s, detail, bx + Inches(0.05), by + Inches(0.5), bw - Inches(0.1), Inches(0.9),
             size=11, color=DGRAY, align=PP_ALIGN.CENTER)
    if i < 7:
        add_text(s, "→", bx + bw, by + Inches(0.6), Inches(0.1), Inches(0.35),
                 size=18, bold=True, color=DGRAY, align=PP_ALIGN.CENTER)

# Offline vs Online
add_rect(s, Inches(0.25), Inches(3.4), Inches(5.5), Inches(0.35), RGBColor(0xE3, 0xF2, 0xFD))
add_text(s, "▶  OFFLINE  (ingest.py)", Inches(0.35), Inches(3.43), Inches(5.3), Inches(0.28),
         size=11, bold=True, color=NAVY)
add_rect(s, Inches(5.85), Inches(3.4), Inches(7.2), Inches(0.35), RGBColor(0xE8, 0xF5, 0xE9))
add_text(s, "▶  ONLINE  (per request)", Inches(5.95), Inches(3.43), Inches(7.0), Inches(0.28),
         size=11, bold=True, color=GREEN)

# Code snippet
code_box(s, [
    "# ingest.py (offline — runs once at container startup)",
    "docs  = DirectoryLoader(data_dir, glob='**/*.md').load()",
    "chunks = splitter.split_documents(docs)            # 15 chunks from 4 files",
    "embeds = embedder.embed_documents([c.page_content for c in chunks])",
    "store.add_documents(chunks, embeds)                # → Milvus IVF_FLAT index",
], Inches(0.25), Inches(3.95), Inches(12.8), Inches(1.1))

bullet_box(s, [
    "15 chunks indexed from 4 knowledge-base files (general · location · rules · booking)",
    "Fallback message returned when retrieval finds no relevant context",
    "ingest.py drops and re-creates the collection — fully idempotent",
], Inches(0.25), Inches(5.2), Inches(12.8), Inches(1.3))


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — LangGraph Workflow
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "LangGraph Stateful Workflow", "Intent routing and response generation")

# Flow diagram — horizontal then vertical branches
# START
flow_box(s, "START", Inches(0.3), Inches(2.4), Inches(1.2), Inches(0.5), DGRAY)
arrow(s, Inches(1.5), Inches(2.65))

# route_intent
flow_box(s, "route_intent", Inches(1.8), Inches(2.4), Inches(1.9))
arrow(s, Inches(3.7), Inches(2.65))

# branch label
add_text(s, "intent?", Inches(3.85), Inches(2.35), Inches(0.9), Inches(0.3),
         size=10, bold=True, color=ORANGE)

# Branches
branches = [
    ("info_query",    "retrieve_and_generate",       Inches(2.25), NAVY),
    ("pricing/hours/\navailability", "dynamic_data_node", Inches(3.5), TEAL),
    ("reservation",   "reservation_collector →\nreservation_validator", Inches(4.8), ORANGE),
    ("out_of_scope",  "out_of_scope_node",            Inches(5.8), DGRAY),
]
arrow_x = Inches(4.75)
for label, node, ny, col in branches:
    add_text(s, label, arrow_x + Inches(0.05), ny - Inches(0.18), Inches(2.2), Inches(0.35),
             size=9, color=DGRAY)
    flow_box(s, node, arrow_x + Inches(0.05), ny + Inches(0.02), Inches(2.9), Inches(0.55), col)
    arrow(s, arrow_x + Inches(2.95), ny + Inches(0.29))
    flow_box(s, "guard_rails_node", arrow_x + Inches(3.2), ny + Inches(0.02), Inches(2.2), Inches(0.55), GREEN)
    arrow(s, arrow_x + Inches(5.4), ny + Inches(0.29))
    flow_box(s, "respond → END", arrow_x + Inches(5.65), ny + Inches(0.02), Inches(1.9), Inches(0.55), DGRAY)

# State fields
add_rect(s, Inches(0.3), Inches(5.5), Inches(12.7), Inches(1.65), WHITE)
add_text(s, "ConversationState  (Pydantic model — LangGraph state)", Inches(0.4), Inches(5.55),
         Inches(12.5), Inches(0.38), size=13, bold=True, color=NAVY)
fields = [
    "session_id: str",
    "messages: list[BaseMessage]  ← add_messages reducer",
    "intent: str | None",
    "retrieved_chunks: list[Document]",
    "reservation: ReservationData | None",
    "response_draft: str | None",
    "response_final: str | None",
    "error: str | None",
]
col1, col2 = fields[:4], fields[4:]
bullet_box(s, col1, Inches(0.4), Inches(5.95), Inches(6.2), Inches(1.1))
bullet_box(s, col2, Inches(6.7), Inches(5.95), Inches(6.2), Inches(1.1))


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Guard Rails
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "Guard-Rails Mechanism", "Two-layer safety filter on every bot response")

# Layer 1
add_rect(s, Inches(0.3), Inches(1.55), Inches(6.0), Inches(3.5), WHITE)
add_rect(s, Inches(0.3), Inches(1.55), Inches(6.0), Inches(0.45), RED)
add_text(s, "Layer 1 — RuleBlocklist  (regex)", Inches(0.4), Inches(1.57),
         Inches(5.8), Inches(0.38), size=14, bold=True, color=WHITE)
bullet_box(s, [
    r"API keys:  /sk-[A-Za-z0-9]{20,}/",
    r"JWT tokens:  /eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/",
    r"Prompt injection probes:  'ignore previous', 'disregard instructions'",
    "Any match → response replaced with privacy disclaimer",
    "Zero external dependencies — pure Python regex",
], Inches(0.45), Inches(2.1), Inches(5.7), Inches(2.8))

# Layer 2
add_rect(s, Inches(6.8), Inches(1.55), Inches(6.2), Inches(3.5), WHITE)
add_rect(s, Inches(6.8), Inches(1.55), Inches(6.2), Inches(0.45), ORANGE)
add_text(s, "Layer 2 — Presidio PII Scanner", Inches(6.9), Inches(1.57),
         Inches(6.0), Inches(0.38), size=14, bold=True, color=WHITE)
bullet_box(s, [
    "Entities: PERSON, LOCATION, PHONE_NUMBER, EMAIL_ADDRESS",
    "Entities: CREDIT_CARD, IBAN_CODE, IP_ADDRESS",
    r"Custom regex: licence plates  /\b[A-Z]{2,3}[-\s]?\d{2,4}…\b/",
    "Powered by Microsoft Presidio + spaCy en_core_web_lg",
    "Gracefully disabled if Presidio unavailable (logs warning)",
], Inches(6.95), Inches(2.1), Inches(5.9), Inches(2.8))

# Exception note
add_rect(s, Inches(0.3), Inches(5.2), Inches(12.7), Inches(0.6), RGBColor(0xE8, 0xF5, 0xE9))
add_text(s,
    "⚡  Exception: Reservation confirmations (status = 'submitted') skip PII scanning "
    "because they legitimately echo the user's own data back.",
    Inches(0.5), Inches(5.25), Inches(12.3), Inches(0.5),
    size=12, color=GREEN)

# Flow
add_text(s, "response_draft", Inches(0.3), Inches(6.0), Inches(2.2), Inches(0.4),
         size=12, bold=True, color=DGRAY, align=PP_ALIGN.CENTER)
arrow(s, Inches(2.5), Inches(6.2))
flow_box(s, "RuleBlocklist\n.check(draft)", Inches(2.75), Inches(5.95), Inches(2.0), Inches(0.55), RED)
arrow(s, Inches(4.75), Inches(6.2))
flow_box(s, "PiiScanner\n.scan(draft)", Inches(5.0), Inches(5.95), Inches(2.0), Inches(0.55), ORANGE)
arrow(s, Inches(7.0), Inches(6.2))
flow_box(s, "match?", Inches(7.25), Inches(5.95), Inches(1.3), Inches(0.55), DGRAY)
arrow(s, Inches(8.55), Inches(6.2))
flow_box(s, "Privacy\ndisclaimer", Inches(8.8), Inches(5.95), Inches(1.7), Inches(0.55), RED)
add_text(s, "clean →", Inches(8.6), Inches(6.75), Inches(1.1), Inches(0.3),
         size=10, color=GREEN)
flow_box(s, "response_final\n= draft", Inches(9.8), Inches(6.7), Inches(1.9), Inches(0.55), GREEN)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Reservation Workflow
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "Reservation Workflow (US3)", "Multi-turn field collection via LangGraph sub-workflow")

# Flow
flow_box(s, "User message\n(reservation intent)", Inches(0.3), Inches(1.7), Inches(2.5), Inches(0.65), NAVY)
arrow(s, Inches(2.8), Inches(2.02))
flow_box(s, "reservation_collector\n_node", Inches(3.05), Inches(1.7), Inches(2.5), Inches(0.65), TEAL)
arrow(s, Inches(5.55), Inches(2.02))
flow_box(s, "reservation_validator\n_node", Inches(5.8), Inches(1.7), Inches(2.5), Inches(0.65), TEAL)
arrow(s, Inches(8.3), Inches(2.02))
add_text(s, "valid?", Inches(8.35), Inches(1.75), Inches(0.9), Inches(0.3),
         size=10, bold=True, color=ORANGE)
flow_box(s, "guard_rails_node\n→ respond", Inches(9.25), Inches(1.7), Inches(2.3), Inches(0.65), GREEN)

# Missing fields loop arrow
add_text(s, "❌ missing / invalid → ask for next field", Inches(5.8), Inches(2.5),
         Inches(6.0), Inches(0.3), size=11, color=RED)
add_text(s, "✅ all fields valid → status = 'submitted' → confirmation",
         Inches(9.25), Inches(2.45), Inches(3.9), Inches(0.35), size=11, color=GREEN)

# Fields box
add_rect(s, Inches(0.3), Inches(3.0), Inches(5.5), Inches(3.6), WHITE)
add_text(s, "Required fields", Inches(0.4), Inches(3.05), Inches(5.3), Inches(0.4),
         size=14, bold=True, color=NAVY)
fields_detail = [
    "first_name  — presence check",
    "surname     — presence check",
    "license_plate — regex: ^[A-Z0-9]{2,10}$",
    "start_datetime — DD.MM.YYYY HH:MM  |  DD/MM/YYYY HH:MM  |  YYYY-MM-DD HH:MM",
    "end_datetime  — same formats  +  end > start",
]
bullet_box(s, fields_detail, Inches(0.45), Inches(3.5), Inches(5.2), Inches(2.9))

# LLM extraction box
add_rect(s, Inches(6.2), Inches(3.0), Inches(6.8), Inches(3.6), WHITE)
add_text(s, "LLM JSON extraction", Inches(6.3), Inches(3.05), Inches(6.6), Inches(0.4),
         size=14, bold=True, color=NAVY)
code_box(s, [
    '# GPT-4o extracts fields from natural language',
    '{"first_name": "Aleksandr",',
    ' "surname": "Mordanov",',
    ' "license_plate": "1672MNP",',
    ' "start_datetime": "12.08.2026 12:00",',
    ' "end_datetime": "13.08.2026 12:00"}',
    '',
    '# Code-fence stripping ensures robust JSON parse',
    '# setattr() merges into existing ReservationData',
], Inches(6.3), Inches(3.5), Inches(6.6), Inches(2.9))


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Evaluation
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "Evaluation Framework", "Retrieval quality measurement with Recall@5 and Precision@5")

# Metrics definition
add_rect(s, Inches(0.3), Inches(1.55), Inches(5.8), Inches(2.8), WHITE)
add_text(s, "Metrics", Inches(0.4), Inches(1.6), Inches(5.6), Inches(0.4),
         size=14, bold=True, color=NAVY)
code_box(s, [
    "Recall@5     = |relevant ∩ retrieved_top5| / |relevant|",
    "Precision@5  = |relevant ∩ retrieved_top5| / 5",
    "",
    "EvaluationReport",
    "  .mean_recall     # avg Recall@5 across all questions",
    "  .mean_precision  # avg Precision@5 across all questions",
    "  .pass_rate       # fraction with recall == 1.0",
], Inches(0.35), Inches(2.0), Inches(5.6), Inches(2.2))

# Dataset
add_rect(s, Inches(6.4), Inches(1.55), Inches(6.6), Inches(2.8), WHITE)
add_text(s, "Evaluation Dataset", Inches(6.5), Inches(1.6), Inches(6.4), Inches(0.4),
         size=14, bold=True, color=NAVY)
bullet_box(s, [
    "22 question–answer pairs in eval/questions.json",
    "Categories: info_query · pricing · hours · availability",
    "5–6 questions per category for balanced coverage",
    "Run: python scripts/evaluate.py → timestamped JSON report",
    "Note: relevant_chunk_ids need back-fill after ingest",
    "       for Recall/Precision to reflect real retrieval",
], Inches(6.5), Inches(2.0), Inches(6.3), Inches(2.2))

# Category table
add_rect(s, Inches(0.3), Inches(4.55), Inches(12.7), Inches(0.45), NAVY)
for i, col_text in enumerate(["Category", "Questions", "Focus", "Example"]):
    add_text(s, col_text, Inches(0.4) + i * Inches(3.2), Inches(4.58),
             Inches(3.1), Inches(0.35), size=12, bold=True, color=WHITE)

rows = [
    ("info_query",    "6",  "Location, facilities, rules, policies",          "Where is the parking located?"),
    ("pricing",       "5",  "Hourly / daily / monthly / overnight rates",      "What is the daily parking rate?"),
    ("hours",         "5",  "Opening times by day of week",                    "What time does the parking open on Sunday?"),
    ("availability",  "6",  "Free spaces, total capacity, reserved count",     "How many spaces are currently available?"),
]
for j, (cat, n, focus, ex) in enumerate(rows):
    bg = WHITE if j % 2 == 0 else LGRAY
    add_rect(s, Inches(0.3), Inches(5.0) + j * Inches(0.5), Inches(12.7), Inches(0.5), bg)
    for k, txt in enumerate([cat, n, focus, ex]):
        add_text(s, txt, Inches(0.4) + k * Inches(3.2), Inches(5.05) + j * Inches(0.5),
                 Inches(3.1), Inches(0.38), size=11, color=DGRAY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Live Demo / Screenshots
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "Live Demo — Streamlit UI", "Running at http://localhost:8501")

# Screenshot placeholder — left panel
add_rect(s, Inches(0.3), Inches(1.6), Inches(6.2), Inches(4.7), RGBColor(0x28, 0x2C, 0x34))
add_text(s, "🖥  Screenshot placeholder\n\nStreamlit UI at http://localhost:8501\n\n"
            "Replace with actual screenshot",
         Inches(0.5), Inches(2.8), Inches(5.8), Inches(2.0),
         size=14, color=RGBColor(0x80, 0x90, 0xA0), align=PP_ALIGN.CENTER)

# Sample interactions
add_rect(s, Inches(6.8), Inches(1.6), Inches(6.2), Inches(4.7), WHITE)
add_text(s, "Sample interactions (verified working)", Inches(6.9), Inches(1.65),
         Inches(6.0), Inches(0.4), size=13, bold=True, color=NAVY)

chats = [
    ("user",      "What are the parking rates?"),
    ("assistant", "Hourly: 2.50 EUR · Daily: 15.00 EUR\nMonthly: 120.00 EUR · Overnight: 8.00 EUR"),
    ("user",      "What time do you open on Sunday?"),
    ("assistant", "Sunday hours: 08:00 – 20:00"),
    ("user",      "First name: Aleksandr  Surname: Mordanov\nLicence plate: 1672MNP\nStart: 12.08.2026 12:00  End: 13.08.2026 12:00"),
    ("assistant", "✅ Reservation submitted!\nName: Aleksandr Mordanov · Plate: 1672MNP\nFrom: 12.08.2026 12:00 to 13.08.2026 12:00"),
]
cy = Inches(2.15)
for role, text in chats:
    col = RGBColor(0xE3, 0xF2, 0xFD) if role == "user" else RGBColor(0xE8, 0xF5, 0xE9)
    label_col = NAVY if role == "user" else GREEN
    add_rect(s, Inches(6.9), cy, Inches(5.9), Inches(0.5), col)
    add_text(s, f"{'👤' if role=='user' else '🤖'}  {text}",
             Inches(6.95), cy + Inches(0.04), Inches(5.8), Inches(0.45),
             size=9, color=label_col)
    cy += Inches(0.52)

add_text(s, "UI features: session UUID · spinner · error banner · message history",
         Inches(0.3), Inches(6.45), Inches(12.7), Inches(0.3),
         size=11, color=DGRAY, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Key Technical Decisions
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "Key Technical Decisions", "Design choices that shaped the implementation")

decisions = [
    (
        "Lazy pymilvus imports",
        "MilvusVectorStore methods import pymilvus inside the method body, not at module level.",
        "All 26 unit tests run without Milvus installed — CI stays fast and cheap.",
        TEAL,
    ),
    (
        "VectorStorePort ABC",
        "MilvusVectorStore implements a minimal ABC interface (add_documents, similarity_search, drop_collection).",
        "Swapping to Pinecone or Weaviate is a single-file change with zero impact on nodes or tests.",
        NAVY,
    ),
    (
        "Pydantic Settings singleton",
        "A module-level `settings` singleton reads all config from .env at import time.",
        "Eliminates scattered os.environ reads; wrong config fails loudly at startup.",
        ORANGE,
    ),
    (
        "pymilvus 2.5.x upgrade",
        "pymilvus 2.4.x imports pkg_resources (setuptools), absent in python:3.13-slim.",
        "2.5.x uses importlib.metadata — no setuptools dependency, Python 3.13 compatible.",
        GREEN,
    ),
    (
        "Guard-rails as a graph node",
        "guard_rails_node is an explicit node that all generation paths route through.",
        "New generation nodes automatically get filtered without touching guard-rails code.",
        RED,
    ),
    (
        "LangGraph → dict result",
        "compiled_graph.invoke() returns AddableValuesDict, not the Pydantic state model.",
        "API uses .get() instead of attribute access — forward-compatible with LangGraph updates.",
        DGRAY,
    ),
]

bw, bh = Inches(4.1), Inches(1.5)
for i, (title, problem, benefit, col) in enumerate(decisions):
    row, col_i = divmod(i, 3)
    bx = Inches(0.3) + col_i * (bw + Inches(0.26))
    by = Inches(1.6) + row * (bh + Inches(0.15))
    add_rect(s, bx, by, bw, bh, WHITE)
    add_rect(s, bx, by, bw, Inches(0.38), col)
    add_text(s, title, bx + Inches(0.1), by + Inches(0.04), bw - Inches(0.2), Inches(0.3),
             size=12, bold=True, color=WHITE)
    add_text(s, f"Context: {problem}", bx + Inches(0.1), by + Inches(0.43), bw - Inches(0.2), Inches(0.5),
             size=10, color=DGRAY)
    add_text(s, f"✓ {benefit}", bx + Inches(0.1), by + Inches(0.93), bw - Inches(0.2), Inches(0.48),
             size=10, bold=True, color=col)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — Tests & CI
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "Tests & CI", "26 unit tests · GitHub Actions · Python 3.13")

# Test table
add_rect(s, Inches(0.3), Inches(1.55), Inches(7.5), Inches(0.4), NAVY)
for j, h in enumerate(["Module", "Tests", "What's covered"]):
    add_text(s, h, Inches(0.4) + j * Inches(2.5), Inches(1.58), Inches(2.4), Inches(0.32),
             size=12, bold=True, color=WHITE)

test_rows = [
    ("test_config.py",          "3",  "Settings load, missing key raises, defaults apply"),
    ("test_rag_pipeline.py",    "5",  "Context format, fallback, LLM mock, chain call"),
    ("test_retriever.py",       "4",  "Top-k filter, empty results, score threshold"),
    ("test_guard_rails.py",     "6",  "Blocklist regex, PII entities, clean text passes"),
    ("test_validator.py",       "5",  "Required fields, plate format, date parse, end > start"),
    ("test_evaluation.py",      "3",  "Recall@5, Precision@5 pure-function correctness"),
]
for j, (mod, n, cover) in enumerate(test_rows):
    bg = WHITE if j % 2 == 0 else LGRAY
    add_rect(s, Inches(0.3), Inches(1.95) + j * Inches(0.44), Inches(7.5), Inches(0.44), bg)
    for k, txt in enumerate([mod, n, cover]):
        add_text(s, txt, Inches(0.4) + k * Inches(2.5), Inches(1.98) + j * Inches(0.44),
                 Inches(2.4), Inches(0.36), size=11, color=DGRAY)

# CI pipeline
add_rect(s, Inches(8.1), Inches(1.55), Inches(4.9), Inches(5.0), WHITE)
add_text(s, "GitHub Actions CI", Inches(8.2), Inches(1.6), Inches(4.7), Inches(0.4),
         size=14, bold=True, color=NAVY)
code_box(s, [
    "on: push (main) · pull_request",
    "",
    "jobs:",
    "  lint:",
    "    ruff check src/ tests/",
    "    ruff format --check",
    "",
    "  test:",
    "    python-version: '3.13'",
    "    pip install -r requirements-dev.txt -e .",
    "    pytest tests/unit/ -v --tb=short",
    "",
    "  # integration tests: local-only (Docker required)",
], Inches(8.2), Inches(2.05), Inches(4.7), Inches(4.2))

# Run result
add_rect(s, Inches(0.3), Inches(4.75), Inches(7.5), Inches(0.55), RGBColor(0xE8, 0xF5, 0xE9))
add_text(s, "✅  pytest tests/unit/  →  26 passed  (0.8 s, no external services)",
         Inches(0.45), Inches(4.8), Inches(7.2), Inches(0.42),
         size=13, bold=True, color=GREEN)

add_text(s, "pythonpath = [\"src\"] in pyproject.toml — no PYTHONPATH hacks needed",
         Inches(0.3), Inches(5.45), Inches(7.5), Inches(0.3), size=11, color=DGRAY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 12 — What's Next
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank)
add_rect(s, 0, 0, W, H, LGRAY)
header_band(s, "What's Next — Stage 2 Roadmap", "Known gaps and planned improvements")

columns = [
    ("Testing", RED, [
        "Add pytest-docker fixture for Milvus integration tests",
        "Wire integration tests into GitHub Actions with services: block",
        "Back-fill relevant_chunk_ids in eval dataset post-ingest",
        "Add OpenAI mock to ingest_documents unit test",
    ]),
    ("Architecture", NAVY, [
        "Module-level MilvusVectorStore singleton (one connection per process)",
        "SQLAlchemy engine as long-lived connection pool in FastAPI lifespan",
        "Switch reservation extraction to LLM .with_structured_output()",
        "Store retrieved_chunks as plain dicts (JSON-serialisable for checkpointing)",
    ]),
    ("Operational", TEAL, [
        "Request-level INFO log: session_id · intent · latency per request",
        "Force error if ADMIN_TOKEN == 'change-me' in production config",
        "Alembic migrations replacing create_all for production schema management",
        "Human-in-the-loop reservation approval (Stage 3 scope)",
    ]),
]

bw = Inches(4.0)
for i, (title, col, items) in enumerate(columns):
    bx = Inches(0.3) + i * (bw + Inches(0.26))
    add_rect(s, bx, Inches(1.55), bw, Inches(5.0), WHITE)
    add_rect(s, bx, Inches(1.55), bw, Inches(0.45), col)
    add_text(s, title, bx + Inches(0.1), Inches(1.58), bw - Inches(0.2), Inches(0.38),
             size=14, bold=True, color=WHITE)
    bullet_box(s, items, bx + Inches(0.1), Inches(2.1), bw - Inches(0.2), Inches(4.3))

add_text(s, "Stage 1 ✅ complete  ·  Stage 2: enhanced retrieval + HITL reservation  ·  "
            "Stage 3: multi-tenant + auth  ·  Stage 4: production hardening",
         Inches(0.3), Inches(6.9), Inches(12.7), Inches(0.35),
         size=11, color=DGRAY, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════════
# Save
# ══════════════════════════════════════════════════════════════════════════════
prs.save(OUT)
print(f"Saved: {OUT}  ({OUT.stat().st_size // 1024} KB,  {len(prs.slides)} slides)")
