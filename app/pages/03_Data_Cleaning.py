import streamlit as st
import pandas as pd
from app.components.layout import page_header, dataset_status
from backend.data_cleaner import generate_cleaning_recommendations, apply_cleaning
from backend.validator import validate_dataset

dataset_status()
page_header("Data Cleaning", "Safely transform your dataset based on validation results.")

# ── Readiness gates ─────────────────────────────────────────────────────────
if not st.session_state.get("dataset_loaded") and not st.session_state.get("demo_mode"):
    st.warning("Please upload a dataset or launch Demo Mode first.")
    st.stop()

if "validation_results" not in st.session_state:
    st.info("Dataset loaded but not validated. Please run validation on the Upload Data page.")
    st.stop()

# ── Completed-cleaning view ──────────────────────────────────────────────────
if st.session_state.get("cleaned_df") is not None:
    cleaned_df = st.session_state["cleaned_df"]
    cs = st.session_state.get("cleaning_summary", {})
    raw_val = st.session_state["validation_results"]
    cleaned_val = st.session_state.get("cleaned_validation_result", {})

    st.success("Dataset is currently cleaned and ready for analysis.")
    st.write("---")

    # ── Cleaning summary metrics ─────────────────────────────────────────────
    st.subheader("Cleaning Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows (Original)", cs.get("raw_rows", 0))
    c2.metric("Rows (Cleaned)", cs.get("clean_rows", 0))
    c3.metric("Rows Removed", cs.get("rows_removed", 0))

    if st.session_state.get("cleaning_applied"):
        with st.expander("Actions applied"):
            for action in st.session_state["cleaning_applied"]:
                st.markdown(f"- `{action}`")

    st.write("---")

    # ── Before / After quality comparison ───────────────────────────────────
    st.subheader("Data Quality Improvement")
    st.caption(
        "Scores are computed by the same validation engine applied independently "
        "to the original raw dataset and the cleaned dataset."
    )

    before_score = raw_val.get("data_quality_score", 0)
    before_band  = raw_val.get("quality_band", "—")
    after_score  = cleaned_val.get("data_quality_score", 0) if cleaned_val else None
    after_band   = cleaned_val.get("quality_band", "—")   if cleaned_val else "—"

    qa_col1, qa_col2, qa_col3 = st.columns(3)

    with qa_col1:
        st.metric(
            label="Quality Score — Before",
            value=f"{before_score} / 100",
            help=f"Band: {before_band}",
        )

    with qa_col2:
        if after_score is not None:
            delta = after_score - before_score
            st.metric(
                label="Quality Score — After",
                value=f"{after_score} / 100",
                delta=f"{delta:+d} pts",
                delta_color="normal" if delta > 0 else ("off" if delta == 0 else "inverse"),
                help=f"Band: {after_band}",
            )
        else:
            st.metric(label="Quality Score — After", value="—")

    with qa_col3:
        missing_before = cs.get("raw_missing_cells", 0)
        missing_after  = cs.get("clean_missing_cells", 0)
        missing_delta  = missing_after - missing_before
        st.metric(
            label="Missing Cells (Before → After)",
            value=f"{missing_before} → {missing_after}",
            delta=f"{missing_delta:+d}",
            delta_color="inverse" if missing_delta > 0 else ("off" if missing_delta == 0 else "normal"),
            help=(
                "Coercing invalid dates or numerics may increase missing values. "
                "This is expected and reflects accurate measurement after type fixing."
            ),
        )

    # Truthful band display — no forced positive framing
    if after_score is not None:
        if after_score > before_score:
            delta = after_score - before_score
            if after_band == before_band:
                st.info(
                    f"Data quality score improved by **{delta} point{'s' if delta != 1 else ''}**, "
                    f"while the status remains **{after_band}**."
                )
            else:
                st.info(f"Data quality improved from **{before_band}** to **{after_band}**.")
        elif after_score == before_score:
            st.info(
                f"Data quality score is unchanged ({after_score} / 100, band: **{after_band}**). "
                "Type coercions may have created new missing values that offset other improvements."
            )
        else:
            st.warning(
                f"Data quality score decreased from {before_score} to {after_score} "
                f"(band: **{after_band}**). This is expected when coercing invalid dates or "
                "numeric strings into missing values — the cleaned data is structurally more "
                "correct even though the missing-value count increased."
            )

    st.write("---")

    # ── Download cleaned CSV ─────────────────────────────────────────────────
    st.subheader("Export")
    csv_bytes = cleaned_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Cleaned CSV",
        data=csv_bytes,
        file_name="retailpilot_cleaned_data.csv",
        mime="text/csv",
        help="Downloads the cleaned dataset. The original raw dataset is not affected.",
    )

    st.write("---")

    # ── Reset ────────────────────────────────────────────────────────────────
    if st.button("Reset Cleaning Pipeline", type="secondary"):
        for key in [
            "cleaned_df",
            "cleaning_config",
            "cleaning_summary",
            "cleaning_applied",
            "cleaned_validation_result",
        ]:
            st.session_state.pop(key, None)
        st.rerun()

# ── Active cleaning pipeline (no cleaned data yet) ──────────────────────────
else:
    val = st.session_state["validation_results"]
    raw_df = st.session_state["raw_df"]

    # ── Recommendations ──────────────────────────────────────────────────────
    st.subheader("Cleaning Recommendations")
    recs = generate_cleaning_recommendations(val)

    if not recs:
        st.success("No critical or medium severity anomalies detected. Your dataset is pristine.")

    for r in recs:
        box_style = (
            "info"    if r["severity"] == "low"      else
            "warning" if r["severity"] == "medium"   else
            "error"
        )
        getattr(st, box_style)(
            f"**{r['title']}** (Affected: {r['affected_count']})  \n{r['explanation']}"
        )

    st.write("---")

    # ── Actions form ─────────────────────────────────────────────────────────
    st.subheader("Configure Actions")
    st.markdown(
        "Select transformations to apply. "
        "**Note: Unrecoverable critical row removals are disabled by default.**"
    )

    with st.form("cleaning_config_form"):
        config = {}
        c_left, c_right = st.columns(2)

        with c_left:
            st.markdown("#### Standard Transformations")
            config["remove_exact_duplicates"] = st.checkbox("Remove Exact Duplicates", value=True)
            config["normalize_whitespace"]    = st.checkbox("Normalize Whitespace",    value=True)
            config["convert_dates"]           = st.checkbox("Fix Date Formatting",     value=True)
            config["convert_numerics"]        = st.checkbox("Coerce Invalid Numerics", value=True)

        with c_right:
            st.markdown("#### Destructive Row Filters")
            config["remove_invalid_quantity"] = st.checkbox("Remove Quantity <= 0",     value=False)
            config["remove_negative_price"]   = st.checkbox("Remove Negative Prices",   value=False)
            config["remove_blank_order_id"]   = st.checkbox("Remove Missing Order IDs", value=False)

        st.write("")
        submit = st.form_submit_button("Apply Cleaning Transformation", type="primary")

    if submit:
        with st.spinner("Applying rules and validating cleaned dataset..."):
            res = apply_cleaning(raw_df, config)

            if res["success"]:
                cleaned_df = res["cleaned_dataframe"]

                # Run post-cleaning validation on the cleaned copy only.
                # The original validation_results key is never overwritten.
                post_val = validate_dataset(cleaned_df)

                st.session_state["cleaned_df"]               = cleaned_df
                st.session_state["cleaning_summary"]         = res["summary"]
                st.session_state["cleaning_config"]          = config
                st.session_state["cleaning_applied"]         = res["actions_applied"]
                st.session_state["cleaned_validation_result"] = post_val
                st.rerun()
            else:
                st.error("Engine failed to complete transformations.")
