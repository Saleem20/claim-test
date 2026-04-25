"""
Bulk Claim Tester — Synthetic Persona Lab
Built with Streamlit + Anthropic Claude API

Run locally:   streamlit run app.py
Deploy:        Push to GitHub → connect to Streamlit Cloud
"""

import streamlit as st
import anthropic
import pandas as pd
from personas import PERSONAS, PERSONA_MAP
from claude_api import test_claim, avg_score, verdict_counts

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bulk Claim Tester | Synthetic Persona Lab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'EB Garamond', Georgia, serif;
    background-color: #0d1117;
    color: #e2d9c5;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #1a1d2a;
}

/* Headers */
h1, h2, h3 { font-family: 'EB Garamond', serif; color: #f0e8d4; }
h1 { font-size: 1.6rem !important; font-weight: 600; }

/* Gold accent label */
.label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.18em;
    color: #c8a84b;
    text-transform: uppercase;
    margin-bottom: 4px;
}

/* Verdict chips */
.chip-pass   { background:#22c55e14; color:#22c55e; border:1px solid #22c55e33; border-radius:5px; padding:2px 10px; font-size:0.75rem; font-weight:700; }
.chip-revise { background:#eab30814; color:#eab308; border:1px solid #eab30833; border-radius:5px; padding:2px 10px; font-size:0.75rem; font-weight:700; }
.chip-reject { background:#ef444414; color:#ef4444; border:1px solid #ef444433; border-radius:5px; padding:2px 10px; font-size:0.75rem; font-weight:700; }

/* Score bar */
.score-bar-wrap { background:#1a1d2a; border-radius:3px; height:6px; margin-top:4px; }
.score-bar      { height:6px; border-radius:3px; }

/* Result card */
.result-card {
    background: #111827;
    border: 1px solid #1a1d2a;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.result-card:hover { border-color: #c8a84b55; }

/* Resonates / concerns lists */
.plus  { color: #22c55e; font-weight: 700; margin-right: 6px; }
.minus { color: #ef4444; font-weight: 700; margin-right: 6px; }

/* Metric number */
.big-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    font-weight: 700;
    color: #c8a84b;
}

/* Disclaimer */
.disclaimer {
    font-size: 0.72rem;
    color: #3a3828;
    border-top: 1px solid #1a1d2a;
    padding-top: 10px;
    margin-top: 24px;
}

/* Streamlit overrides */
.stButton > button {
    background: #c8a84b !important;
    color: #0d1117 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 7px !important;
    padding: 0.55rem 1.4rem !important;
}
.stButton > button:hover { background: #d4b55a !important; }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #111827 !important;
    border: 1px solid #2a2d3a !important;
    color: #e2d9c5 !important;
    font-family: 'EB Garamond', serif !important;
    border-radius: 7px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #c8a84b !important;
    box-shadow: none !important;
}

[data-testid="stMetricValue"] { color: #c8a84b !important; font-family: 'JetBrains Mono', monospace !important; }

div[data-testid="stExpander"] {
    background: #111827;
    border: 1px solid #1a1d2a;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def score_color(score: int) -> str:
    return ["", "#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"][score]


def score_bar_html(score: int, max_score: int = 5) -> str:
    pct = (score / max_score) * 100
    color = score_color(score)
    return f"""
    <div class="score-bar-wrap">
      <div class="score-bar" style="width:{pct}%;background:{color};"></div>
    </div>
    """


def verdict_chip(verdict: str) -> str:
    cls = {"Pass": "chip-pass", "Revise": "chip-revise", "Reject": "chip-reject"}.get(verdict, "")
    return f'<span class="{cls}">{verdict}</span>'


def get_client() -> anthropic.Anthropic | None:
    """Return an Anthropic client using the key from secrets or session state."""
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        try:
            api_key = st.secrets["ANTHROPIC_API_KEY"]
        except (KeyError, FileNotFoundError):
            pass
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    return None


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="label">Synthetic Persona Lab</div>', unsafe_allow_html=True)
    st.markdown("## Bulk Claim Tester")
    st.markdown("---")

    # API key (only shown if not set in secrets)
    has_secret = False
    try:
        _ = st.secrets["ANTHROPIC_API_KEY"]
        has_secret = True
    except (KeyError, FileNotFoundError):
        pass

    if not has_secret:
        st.markdown('<div class="label">Anthropic API Key</div>', unsafe_allow_html=True)
        api_key_input = st.text_input(
            "API Key", type="password", label_visibility="collapsed",
            placeholder="sk-ant-...",
            help="Get your key at console.anthropic.com"
        )
        if api_key_input:
            st.session_state["api_key"] = api_key_input
    else:
        st.success("🔑 API key loaded from secrets", icon="✓")

    st.markdown("---")
    st.markdown('<div class="label">Product Details</div>', unsafe_allow_html=True)
    category = st.text_input("Category", placeholder="e.g. Skincare, Finance, Pet Care")
    product_name = st.text_input("Product / Brand Name", placeholder="e.g. Lumora, NestEgg")

    st.markdown("---")
    st.markdown('<div class="label">Personas</div>', unsafe_allow_html=True)
    selected_persona_ids = []
    for p in PERSONAS:
        checked = p["id"] in ["young_urban", "family_suburban", "budget_conscious"]
        if st.checkbox(f"{p['icon']} {p['label']} · {p['age']}", value=checked, key=f"p_{p['id']}"):
            selected_persona_ids.append(p["id"])

    st.markdown("---")
    st.markdown('<div class="label">Sort Results By</div>', unsafe_allow_html=True)
    sort_option = st.selectbox(
        "Sort", ["Average Score (High→Low)", "Pass Count (High→Low)", "Input Order"],
        label_visibility="collapsed"
    )

    st.markdown('<div class="disclaimer">⚠ Outputs are synthetic persona simulations for initial hypothesis testing only. Validate against primary research before vendor presentation.</div>', unsafe_allow_html=True)


# ── Main area ─────────────────────────────────────────────────────────────────

st.markdown('<div class="label">Bulk Claim Tester</div>', unsafe_allow_html=True)
st.markdown("## Name & Claim Testing")
st.markdown("Enter up to **15 claims**, select your personas, and run a full test before sharing with vendors.")

st.markdown("---")

# ── Claim input grid ──────────────────────────────────────────────────────────
st.markdown('<div class="label">Claims to Test</div>', unsafe_allow_html=True)

claims_input = []
cols_per_row = 3
rows = 5  # 5 rows × 3 cols = 15

for row in range(rows):
    cols = st.columns(cols_per_row)
    for col_idx, col in enumerate(cols):
        n = row * cols_per_row + col_idx + 1
        with col:
            val = st.text_input(
                f"Claim {n:02d}",
                key=f"claim_{n}",
                placeholder=f"Claim {n}",
                label_visibility="visible",
            )
            claims_input.append(val.strip())

filled_claims = [(i, c) for i, c in enumerate(claims_input) if c]

st.markdown("---")

# ── Run button ────────────────────────────────────────────────────────────────
col_btn, col_info = st.columns([2, 3])
with col_btn:
    run_pressed = st.button(
        f"▶  Run {len(filled_claims)} Claims × {len(selected_persona_ids)} Personas"
        + (f"  ({len(filled_claims) * len(selected_persona_ids)} tests)" if filled_claims and selected_persona_ids else "")
    )

with col_info:
    if not filled_claims:
        st.caption("Enter at least one claim above.")
    elif not selected_persona_ids:
        st.caption("Select at least one persona in the sidebar.")
    elif not get_client():
        st.caption("Add your Anthropic API key in the sidebar.")


# ── Run tests ─────────────────────────────────────────────────────────────────
if run_pressed:
    errors = []
    if not category.strip():    errors.append("Category")
    if not product_name.strip(): errors.append("Product Name")
    if not filled_claims:        errors.append("at least one claim")
    if not selected_persona_ids: errors.append("at least one persona")
    client = get_client()
    if not client:               errors.append("a valid API key")

    if errors:
        st.error(f"Please provide: {', '.join(errors)}.")
    else:
        selected_personas = [PERSONA_MAP[pid] for pid in selected_persona_ids]
        total_tests = len(filled_claims) * len(selected_personas)

        st.session_state["results"] = {}
        st.session_state["category"] = category
        st.session_state["product_name"] = product_name

        progress_bar = st.progress(0, text="Starting…")
        status_text = st.empty()
        completed = 0

        all_results = {}

        for orig_idx, claim_text in filled_claims:
            all_results[orig_idx] = {"claim": claim_text, "persona_results": {}}
            for persona in selected_personas:
                status_text.markdown(
                    f'<div class="label">Testing claim {orig_idx+1}: "{claim_text[:50]}…" → {persona["icon"]} {persona["label"]}</div>',
                    unsafe_allow_html=True
                )
                result = test_claim(client, persona, category, product_name, claim_text)
                all_results[orig_idx]["persona_results"][persona["id"]] = result
                completed += 1
                progress_bar.progress(completed / total_tests, text=f"{completed}/{total_tests} tests complete")

        st.session_state["results"] = all_results
        progress_bar.empty()
        status_text.empty()
        st.success(f"✓ {total_tests} tests complete across {len(filled_claims)} claims and {len(selected_personas)} personas.")


# ── Results ───────────────────────────────────────────────────────────────────
if "results" in st.session_state and st.session_state["results"]:
    results = st.session_state["results"]
    saved_category = st.session_state.get("category", category)
    saved_product = st.session_state.get("product_name", product_name)

    st.markdown("---")
    st.markdown('<div class="label">Results</div>', unsafe_allow_html=True)
    st.markdown(f"### {saved_product} · {saved_category}")

    # ── Summary metrics ────────────────────────────────────────────────────────
    all_persona_results = []
    for data in results.values():
        all_persona_results.extend(data["persona_results"].values())

    total_pass   = sum(1 for r in all_persona_results if not r.get("error") and r.get("verdict") == "Pass")
    total_revise = sum(1 for r in all_persona_results if not r.get("error") and r.get("verdict") == "Revise")
    total_reject = sum(1 for r in all_persona_results if not r.get("error") and r.get("verdict") == "Reject")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Claims Tested", len(results))
    m2.metric("✅ Pass", total_pass)
    m3.metric("⚠️ Revise", total_revise)
    m4.metric("❌ Reject", total_reject)

    st.markdown("---")

    # ── Sort ───────────────────────────────────────────────────────────────────
    claim_items = list(results.items())
    if sort_option == "Average Score (High→Low)":
        claim_items.sort(key=lambda x: avg_score(list(x[1]["persona_results"].values())), reverse=True)
    elif sort_option == "Pass Count (High→Low)":
        claim_items.sort(key=lambda x: verdict_counts(list(x[1]["persona_results"].values()))["Pass"], reverse=True)

    # ── Per-claim expanders ────────────────────────────────────────────────────
    for rank, (orig_idx, data) in enumerate(claim_items):
        claim_text = data["claim"]
        persona_results = data["persona_results"]
        pr_list = list(persona_results.values())
        a_score = avg_score(pr_list)
        vc = verdict_counts(pr_list)

        chip_html = " ".join(
            f'<span style="font-size:0.72rem;padding:1px 7px;border-radius:4px;background:{["#22c55e14","#eab30814","#ef444414"][i]};color:{["#22c55e","#eab308","#ef4444"][i]};border:1px solid {["#22c55e33","#eab30833","#ef444433"][i]}">{c} {v}</span>'
            for i, (v, c) in enumerate(vc.items()) if c > 0
        )

        header = (
            f"**#{rank+1}** &nbsp; \"{claim_text}\" &nbsp;&nbsp; "
            f"<span style='font-family:monospace;color:{score_color(round(a_score))};font-weight:700'>{a_score:.1f}/5</span>"
        )

        with st.expander(f"#{rank+1}  \"{claim_text}\"  —  avg {a_score:.1f}/5", expanded=(rank == 0)):
            st.markdown(chip_html, unsafe_allow_html=True)
            st.markdown("")

            for pid, result in persona_results.items():
                persona = PERSONA_MAP.get(pid, {})
                if result.get("error"):
                    st.warning(f"{persona.get('icon','')} {persona.get('label','Unknown')} — test failed.")
                    continue

                verdict = result.get("verdict", "—")
                name_score = result.get("name_score", 0)
                claim_score = result.get("claim_score", 0)

                st.markdown(
                    f"""
                    <div class="result-card">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
                        <div>
                          <span style="font-size:1.05rem">{persona.get('icon','')} </span>
                          <strong style="color:#f0e8d4;font-size:0.95rem">{persona.get('label','')}</strong>
                          <span style="color:#4a4535;font-size:0.75rem;margin-left:8px">{persona.get('age','')}</span>
                        </div>
                        {verdict_chip(verdict)}
                      </div>
                      <div style="color:#8a8070;font-style:italic;font-size:0.88rem;margin-bottom:12px">
                        "{result.get('first_reaction','')}"
                      </div>
                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
                        <div>
                          <div style="font-family:monospace;font-size:0.6rem;color:#5a5040;text-transform:uppercase;letter-spacing:0.1em">
                            Name Score &nbsp;<span style="color:{score_color(name_score)};font-size:0.75rem">{name_score}/5</span>
                          </div>
                          {score_bar_html(name_score)}
                        </div>
                        <div>
                          <div style="font-family:monospace;font-size:0.6rem;color:#5a5040;text-transform:uppercase;letter-spacing:0.1em">
                            Claim Score &nbsp;<span style="color:{score_color(claim_score)};font-size:0.75rem">{claim_score}/5</span>
                          </div>
                          {score_bar_html(claim_score)}
                        </div>
                      </div>
                      <div style="font-size:0.85rem;color:#b0a898;line-height:1.65;margin-bottom:12px">
                        {result.get('claim_feedback','')}
                      </div>
                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
                        <div style="background:#22c55e08;border:1px solid #22c55e18;border-radius:6px;padding:10px 12px">
                          <div style="font-family:monospace;font-size:0.58rem;color:#22c55e;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">Resonates</div>
                          {''.join(f'<div style="font-size:0.82rem;color:#b0a898;margin-bottom:4px"><span class="plus">+</span>{item}</div>' for item in result.get('resonates',[]))}
                        </div>
                        <div style="background:#ef44440a;border:1px solid #ef444418;border-radius:6px;padding:10px 12px">
                          <div style="font-family:monospace;font-size:0.58rem;color:#ef4444;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">Concerns</div>
                          {''.join(f'<div style="font-size:0.82rem;color:#b0a898;margin-bottom:4px"><span class="minus">−</span>{item}</div>' for item in result.get('concerns',[]))}
                        </div>
                      </div>
                      <div style="margin-top:10px;font-size:0.78rem;color:#5a5040;font-style:italic">
                        {result.get('verdict_reason','')}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── CSV Export ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="label">Export</div>', unsafe_allow_html=True)

    export_rows = []
    for rank, (orig_idx, data) in enumerate(claim_items):
        claim_text = data["claim"]
        for pid, result in data["persona_results"].items():
            if not result.get("error"):
                export_rows.append({
                    "Rank": rank + 1,
                    "Claim": claim_text,
                    "Persona": result.get("persona_label", pid),
                    "Name Score": result.get("name_score"),
                    "Claim Score": result.get("claim_score"),
                    "Verdict": result.get("verdict"),
                    "Verdict Reason": result.get("verdict_reason"),
                    "First Reaction": result.get("first_reaction"),
                    "Claim Feedback": result.get("claim_feedback"),
                    "Resonates": " | ".join(result.get("resonates", [])),
                    "Concerns": " | ".join(result.get("concerns", [])),
                })

    if export_rows:
        df = pd.DataFrame(export_rows)
        csv = df.to_csv(index=False)
        st.download_button(
            label="⬇  Download Results as CSV",
            data=csv,
            file_name=f"claim_test_{saved_product.replace(' ','_').lower()}.csv",
            mime="text/csv",
        )
