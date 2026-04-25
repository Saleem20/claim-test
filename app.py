"""Synthetic Persona Lab — Streamlit frontend.

Test product claims or pack names against 10+ synthetic consumers
before committing to primary research.
"""

from __future__ import annotations

import io
import json
from typing import List

import pandas as pd
import streamlit as st

from backend.aggregation import (
    scores_dataframe,
    summarise,
    verbatim_dataframe,
)
from backend.claude_client import ClaudeClient
from backend.personas import (
    load_default_personas,
    load_personas_from_csv,
    load_personas_from_json,
)
from backend.schemas import Persona, TestInput
from backend.test_engine import run_test

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Synthetic Persona Lab",
    layout="wide",
    initial_sidebar_state="expanded",
)

VERDICT_COLOURS = {"GO": "#16a34a", "ITERATE": "#eab308", "REJECT": "#dc2626"}
CATEGORIES = ["Oral Health", "OTC", "Wellness"]


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "personas" not in st.session_state:
    st.session_state.personas = load_default_personas()
if "last_run" not in st.session_state:
    st.session_state.last_run = None
if "last_summary" not in st.session_state:
    st.session_state.last_summary = None
if "last_scores_df" not in st.session_state:
    st.session_state.last_scores_df = None
if "last_verbatim_df" not in st.session_state:
    st.session_state.last_verbatim_df = None


# ---------------------------------------------------------------------------
# Sidebar: API key, persona source, persona selection
# ---------------------------------------------------------------------------


def sidebar_controls() -> List[Persona]:
    st.sidebar.title("Setup")

    # API key
    stored_key = ""
    try:
        stored_key = st.secrets.get("ANTHROPIC_API_KEY", "")  # type: ignore[attr-defined]
    except Exception:
        stored_key = ""

    api_key = st.sidebar.text_input(
        "Anthropic API key",
        type="password",
        value=stored_key,
        help="Your key is used only for this session and is not stored by the app.",
    )
    st.session_state["api_key"] = api_key

    st.sidebar.divider()

    # Persona source
    st.sidebar.subheader("Personas")
    source = st.sidebar.radio(
        "Source",
        options=["Use default 10 personas", "Upload custom personas"],
        index=0,
    )

    if source == "Upload custom personas":
        uploaded = st.sidebar.file_uploader(
            "Upload JSON or CSV",
            type=["json", "csv"],
            help=(
                "JSON format: {'schema_version': '1.0', 'personas': [...] } matching the bundled schema. "
                "CSV format: flat columns, pipe-separated list fields."
            ),
        )
        if uploaded is not None:
            try:
                if uploaded.name.lower().endswith(".json"):
                    personas = load_personas_from_json(uploaded.read())
                else:
                    personas = load_personas_from_csv(uploaded.read())
                st.session_state.personas = personas
                st.sidebar.success(f"Loaded {len(personas)} persona(s).")
            except Exception as exc:  # noqa: BLE001
                st.sidebar.error(f"Could not load file: {exc}")

    personas: List[Persona] = st.session_state.personas

    # Persona picker
    persona_options = {f"{p.name} — {p.label}": p.id for p in personas}
    default_selection = list(persona_options.keys())
    selected_labels = st.sidebar.multiselect(
        "Personas to include",
        options=list(persona_options.keys()),
        default=default_selection,
    )
    selected_ids = {persona_options[label] for label in selected_labels}
    selected_personas = [p for p in personas if p.id in selected_ids]

    return selected_personas


# ---------------------------------------------------------------------------
# Main panel: test input
# ---------------------------------------------------------------------------


def test_input_panel() -> TestInput | None:
    st.title("Synthetic Persona Lab")
    st.caption(
        "A virtual pre-test for claims and pack names across Oral Health, OTC and Wellness. "
        "Use this to filter weak options before primary research, not to replace it."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        test_type_label = st.radio(
            "Test type",
            options=["Claim test", "Pack name test"],
            horizontal=True,
        )
    with col2:
        category = st.selectbox("Category", options=CATEGORIES, index=0)

    test_type = "claim" if test_type_label == "Claim test" else "name"

    subject = st.text_area(
        "Claim or name to test",
        placeholder=(
            "e.g. 'Clinically proven to whiten teeth 3 shades in 7 days'  or  'ZenRoot Calm Gummies'"
        ),
        height=80,
    )

    with st.expander("Optional product context", expanded=False):
        product_context = st.text_area(
            "Product context",
            placeholder=(
                "e.g. 'Toothpaste for sensitive teeth, 100g tube, RRP $8.99, pharmacy channel' "
                "or 'Magnesium gummy, 60 pack, RRP $34.99, aimed at sleep support'"
            ),
            height=80,
        )

    if not subject.strip():
        return None

    return TestInput(
        test_type=test_type,
        category=category,
        subject=subject.strip(),
        product_context=product_context.strip() or None,
    )


# ---------------------------------------------------------------------------
# Run & render
# ---------------------------------------------------------------------------


def run_panel(test_input: TestInput, personas: List[Persona]) -> None:
    run_disabled = not personas or not st.session_state.get("api_key")
    if st.button(
        "Run test across personas",
        type="primary",
        disabled=run_disabled,
        use_container_width=True,
    ):
        if not st.session_state.get("api_key"):
            st.error("Enter an Anthropic API key in the sidebar.")
            return
        if not personas:
            st.error("Select at least one persona in the sidebar.")
            return

        try:
            client = ClaudeClient(api_key=st.session_state["api_key"])
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not initialise Claude client: {exc}")
            return

        progress_bar = st.progress(0.0, text="Running personas...")

        def _on_progress(done: int, total: int) -> None:
            progress_bar.progress(done / total, text=f"Completed {done} of {total} personas")

        with st.spinner("Querying personas..."):
            run = run_test(test_input, personas, client, progress_callback=_on_progress)

        progress_bar.empty()

        if not run.responses:
            st.error("No personas returned a valid response. Check the API key or try again.")
            return

        scores_df = scores_dataframe(run, personas)
        verbatim_df = verbatim_dataframe(run, personas)
        summary = summarise(run, personas)

        st.session_state.last_run = run
        st.session_state.last_scores_df = scores_df
        st.session_state.last_verbatim_df = verbatim_df
        st.session_state.last_summary = summary


def render_results() -> None:
    summary = st.session_state.last_summary
    run = st.session_state.last_run
    scores_df = st.session_state.last_scores_df
    verbatim_df = st.session_state.last_verbatim_df

    if not summary or run is None:
        return

    st.divider()
    st.header("Results")

    # Verdict tile
    verdict = summary["verdict"]
    colour = VERDICT_COLOURS.get(verdict, "#6b7280")
    st.markdown(
        f"""
        <div style="padding:16px;border-radius:8px;background:{colour};color:white;">
            <div style="font-size:14px;opacity:0.85;">Verdict</div>
            <div style="font-size:32px;font-weight:700;">{verdict}</div>
            <div style="font-size:14px;">{summary['reason']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Headline metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Overall score", summary["overall_score"])
    m2.metric("Personas tested", summary["persona_count"])
    m3.metric("Segment winners", len(summary["segment_winners"]))
    m4.metric("Red flags", len(summary["red_flags"]))

    # Dimension means
    st.subheader("Dimension averages")
    dim_df = pd.DataFrame(
        {"dimension": list(summary["dimension_means"].keys()),
         "mean_score": list(summary["dimension_means"].values())}
    )
    st.bar_chart(dim_df.set_index("dimension"))

    # Per-persona heatmap
    st.subheader("Scores by persona")
    dim_cols = [c for c in scores_df.columns if c not in {
        "persona_id", "persona_label", "persona_name", "overall"
    }]
    display_df = scores_df.set_index("persona_name")[dim_cols + ["overall"]]
    styled = display_df.style.background_gradient(cmap="RdYlGn", vmin=1, vmax=7, subset=dim_cols)
    st.dataframe(styled, use_container_width=True)

    # Segment winners
    if summary["segment_winners"]:
        st.subheader("Segment winners")
        for w in summary["segment_winners"]:
            st.markdown(f"- **{w['persona']}** (score {w['decision_score']}/7) — _{w['why']}_")
    else:
        st.info("No segment winners this round — no persona scored the decision dimension ≥ 5.5.")

    # Red flags
    if summary["red_flags"]:
        st.subheader("Red flags")
        for r in summary["red_flags"]:
            st.markdown(
                f"- **{r['persona']}** (trust {r['trust_score']}/7) — _{r['concern']}_"
            )

    # Verbatims
    st.subheader("Persona verbatims")
    for _, row in verbatim_df.iterrows():
        with st.expander(f"{row['persona_name']} — {row['persona_label']}  (overall {row['overall']}/7)"):
            st.markdown(f"> {row['verbatim']}")
            st.markdown(f"**Top positive:** {row['top_positive']}")
            st.markdown(f"**Top concern:** {row['top_concern']}")
            st.markdown(f"**Associations:** {row['associations']}")

    # Export
    st.subheader("Export")
    csv_bytes = scores_df.to_csv(index=False).encode("utf-8")
    verbatim_bytes = verbatim_df.to_csv(index=False).encode("utf-8")
    json_bytes = json.dumps(
        {
            "input": run.input.model_dump(),
            "summary": summary,
            "responses": [r.model_dump() for r in run.responses],
        },
        indent=2,
    ).encode("utf-8")

    c1, c2, c3 = st.columns(3)
    c1.download_button("Download scores (CSV)", csv_bytes, file_name="scores.csv", mime="text/csv")
    c2.download_button(
        "Download verbatims (CSV)", verbatim_bytes, file_name="verbatims.csv", mime="text/csv"
    )
    c3.download_button(
        "Download full run (JSON)", json_bytes, file_name="run.json", mime="application/json"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    personas = sidebar_controls()

    test_input = test_input_panel()

    if test_input is None:
        st.info("Enter a claim or a pack name above to begin.")
        return

    run_panel(test_input, personas)
    render_results()


if __name__ == "__main__":
    main()
