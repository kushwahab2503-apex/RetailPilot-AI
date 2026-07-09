import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

# Import of existing completed and completed engines/helpers
from backend.analytics_engine import prepare_analytics_dataset
from backend.customer_engine import prepare_customer_dataset, calculate_lifetime_customer_base, get_customer_period_performance
from backend.product_engine import prepare_product_dataset, get_product_performance, get_pareto_data
from backend.forecast_engine import detect_forecast_capabilities
from backend.business_health_engine import calculate_period_split_dates, evaluate_business_health

DOMAIN_ORDER = {
    "Revenue": 1,
    "Customers": 2,
    "Products": 3,
    "Order Economics": 4,
    "Forecast Readiness": 5,
    "Data Quality": 6
}

SEVERITY_RANK = {
    "Risk": 4,
    "Watch": 3,
    "Positive": 2,
    "Informational": 1
}


def sort_insights(insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sorts insights deterministically in accordance with the rules:
    1. priority ascending (1 = highest)
    2. explicit domain order
    3. insight id ascending
    """
    return sorted(
        insights,
        key=lambda x: (
            x.get("priority", 5),
            DOMAIN_ORDER.get(x.get("domain", "Revenue"), 99),
            x.get("id", "")
        )
    )


def deduplicate_insights(insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Performs semantic deduplication on product portfolio insights.
    If Top-1 and Top-5 product concentration insights both exist:
    - Retain the one with the higher severity (Risk > Watch > Positive > Informational)
    - If severity ties, retain the one with the lower priority number (1 (highest) to 5)
    - If still tied, use a fixed precedence ('prod_top1_dependency' takes precedence over 'prod_top5_concentration')
    """
    # Identify if both top-1 and top-5 product insights are present
    top1_ins = [i for i in insights if i["id"].startswith("prod_top1_dependency")]
    top5_ins = [i for i in insights if i["id"].startswith("prod_top5_concentration")]

    if not top1_ins or not top5_ins:
        return insights

    # We have both types of insights in the list. Overlapping occurs when both represent warnings/alerts/observes.
    # Collect indices to compare
    t1 = top1_ins[0]
    t5 = top5_ins[0]

    # Compare severity
    s1 = SEVERITY_RANK.get(t1["severity"], 0)
    s2 = SEVERITY_RANK.get(t5["severity"], 0)

    keep_t1 = True
    if s1 > s2:
        keep_t1 = True
    elif s2 > s1:
        keep_t1 = False
    else:
        # Tie severity, check priority (smaller is higher priority)
        p1 = t1["priority"]
        p2 = t5["priority"]
        if p1 < p2:
            keep_t1 = True
        elif p2 < p1:
            keep_t1 = False
        else:
            # Still tied, Top-1 takes precedence
            keep_t1 = True

    # Build deduplicated list
    to_remove = t5 if keep_t1 else t1
    return [i for i in insights if i["id"] != to_remove["id"]]


def generate_business_insights(df: pd.DataFrame, generated_from_cleaned_dataset: bool = False) -> Dict[str, Any]:
    """
    Generates deterministic, explainable business insights from a transactional dataset.
    Orchestrates calculations from analytics, customer, product, forecast, and business health engines.
    """
    # 1. Initialize result structure with default metadata and zero counts
    result = {
        "insights": [],
        "priority_insights": [],
        "positive_insights": [],
        "watch_insights": [],
        "risk_insights": [],
        "informational_insights": [],
        "domain_counts": {
            "Revenue": 0,
            "Customers": 0,
            "Products": 0,
            "Order Economics": 0,
            "Forecast Readiness": 0,
            "Data Quality": 0
        },
        "severity_counts": {
            "Positive": 0,
            "Informational": 0,
            "Watch": 0,
            "Risk": 0
        },
        "metadata": {
            "input_row_count": len(df) if df is not None else 0,
            "working_row_count": 0,
            "insight_count": 0,
            "calculable_domain_count": 0,
            "insufficient_domains": [],
            "generated_from_cleaned_dataset": generated_from_cleaned_dataset
        }
    }

    # 2. Defensive handling of empty or invalid datasets
    if df is None or df.empty:
        # Generate appropriate chronological unavailable limitation insight
        limitation_insight = {
            "id": "data_chronological_unavailable",
            "domain": "Data Quality",
            "title": "Chronological Analysis Unavailable",
            "summary": "No transactions were detected in the uploaded dataset. Insufficient data for chronological comparison or trend matching.",
            "severity": "Informational",
            "priority": 4,
            "metric_name": "Row Count",
            "metric_value": 0,
            "comparison_value": None,
            "unit": "rows",
            "evidence": ["The input dataframe has 0 rows."],
            "recommended_action": "Upload a valid CSV file containing historical sales transactions.",
            "source_engine": "analytics_engine",
            "status": "Unavailable"
        }
        result["insights"] = [limitation_insight]
        result["informational_insights"] = [limitation_insight]
        result["domain_counts"]["Data Quality"] = 1
        result["severity_counts"]["Informational"] = 1
        result["metadata"]["insight_count"] = 1
        result["metadata"]["insufficient_domains"] = ["Revenue", "Customers", "Products", "Order Economics"]
        return result

    # Check for core columns
    has_orders = "OrderID" in df.columns
    has_dates = "OrderDate" in df.columns
    has_qty = "Quantity" in df.columns
    has_price = "UnitPrice" in df.columns

    # Add insufficient domains
    unsat_domains = []
    if not (has_orders and has_dates and has_qty and has_price):
        unsat_domains.extend(["Revenue", "Order Economics"])

    # Prepare analytics dataset
    prep_df, prep_meta = prepare_analytics_dataset(df)
    result["metadata"]["working_row_count"] = len(prep_df)

    if prep_df.empty:
        limitation_insight = {
            "id": "data_chronological_unavailable",
            "domain": "Data Quality",
            "title": "Chronological Analysis Unavailable",
            "summary": "No valid transaction rows remained after filtering missing transaction fields.",
            "severity": "Informational",
            "priority": 4,
            "metric_name": "Working Row Count",
            "metric_value": 0,
            "comparison_value": None,
            "unit": "rows",
            "evidence": ["All transactions were excluded during validation filters."],
            "recommended_action": "Check date format and numeric columns in your source file.",
            "source_engine": "analytics_engine",
            "status": "Unavailable"
        }
        result["insights"] = [limitation_insight]
        result["informational_insights"] = [limitation_insight]
        result["domain_counts"]["Data Quality"] = 1
        result["severity_counts"]["Informational"] = 1
        result["metadata"]["insight_count"] = 1
        result["metadata"]["insufficient_domains"] = ["Revenue", "Customers", "Products", "Order Economics"]
        return result

    # Calculate actual parameters for chronological checks
    min_date = prep_df["OrderDate"].min()
    max_date = prep_df["OrderDate"].max()
    date_span_days = (max_date - min_date).days + 1 if pd.notna(min_date) and pd.notna(max_date) else 0

    has_customer = "CustomerID" in df.columns or "CustomerName" in df.columns
    has_product = "ProductID" in df.columns or "ProductName" in df.columns

    if not has_customer:
        unsat_domains.append("Customers")
    if not has_product:
        unsat_domains.append("Products")

    # Evaluate business health directly
    bh_res = evaluate_business_health(df)
    bh_metrics = bh_res["metrics"]
    split = bh_res["dates_metadata"].copy()
    for k in ["recent_start", "recent_end", "prev_start", "prev_end"]:
        if split.get(k):
            split[k] = pd.to_datetime(split[k])

    insights_list = []

    # ------------------ DATA QUALITY LIMITATION INSIGHTS ------------------
    # Missing customers identity
    if not has_customer:
        insights_list.append({
            "id": "data_missing_customers",
            "domain": "Data Quality",
            "title": "Customer Analysis Unavailable",
            "summary": "Customer identity columns (CustomerID/CustomerName) are missing from the dataset. Customer retention and concentration tracking cannot be performed.",
            "severity": "Informational",
            "priority": 4,
            "metric_name": "Customer Columns",
            "metric_value": 0,
            "comparison_value": None,
            "unit": "columns",
            "evidence": ["Neither CustomerID nor CustomerName columns exist in the uploaded dataset schema."],
            "recommended_action": "Ensure CustomerID or CustomerName is included in the upload format.",
            "source_engine": "customer_engine",
            "status": "Unavailable"
        })

    # Missing products identity
    if not has_product:
        insights_list.append({
            "id": "data_missing_products",
            "domain": "Data Quality",
            "title": "Product Analysis Unavailable",
            "summary": "Product identity columns (ProductID/ProductName) are missing from the dataset. Product concentration and Pareto calculations cannot be performed.",
            "severity": "Informational",
            "priority": 4,
            "metric_name": "Product Columns",
            "metric_value": 0,
            "comparison_value": None,
            "unit": "columns",
            "evidence": ["Neither ProductID nor ProductName columns exist in the uploaded dataset schema."],
            "recommended_action": "Ensure ProductID or ProductName is included in the upload format.",
            "source_engine": "product_engine",
            "status": "Unavailable"
        })

    # Timeline/chronological span limited
    if date_span_days < 14:
        insights_list.append({
            "id": "data_chronological_unavailable",
            "domain": "Data Quality",
            "title": "Chronological Analysis Limited",
            "summary": "Dataset timeline spans less than 14 days, preventing standard baseline period comparison and growth insights.",
            "severity": "Informational",
            "priority": 4,
            "metric_name": "Calendar Days Span",
            "metric_value": int(date_span_days),
            "comparison_value": 14,
            "unit": "days",
            "evidence": [f"The active date span is {date_span_days} days. (Minimum required is 14 days)"],
            "recommended_action": "Upload a dataset covering at least 14 days to enable period-over-period comparisons.",
            "source_engine": "analytics_engine",
            "status": "Unavailable"
        })
    elif not split.get("split_valid", False):
        insights_list.append({
            "id": "data_chronological_unavailable",
            "domain": "Data Quality",
            "title": "Chronological comparison Unavailable",
            "summary": "Equal comparison windows could not be anchored. Insufficient sales history distribution to split periods.",
            "severity": "Informational",
            "priority": 4,
            "metric_name": "Is Split Valid",
            "metric_value": 0,
            "comparison_value": 1,
            "unit": "bool",
            "evidence": ["Period split is invalid; insufficient historical density in previous comparison block."],
            "recommended_action": "Upload a dataset with uniform transaction dates covering both comparison windows.",
            "source_engine": "analytics_engine",
            "status": "Unavailable"
        })

    # No positive revenue base
    total_revenue = prep_df["_Revenue"].sum() if "_Revenue" in prep_df.columns else 0.0
    if total_revenue <= 0.0:
        insights_list.append({
            "id": "data_no_positive_revenue",
            "domain": "Data Quality",
            "title": "No Positive Revenue Base",
            "summary": "The dataset has zero or negative transaction values, preventing financial growth and baseline calculations.",
            "severity": "Informational",
            "priority": 4,
            "metric_name": "Total Revenue",
            "metric_value": float(total_revenue),
            "comparison_value": 0.0,
            "unit": "revenue",
            "evidence": [f"Total analyzed revenue is {total_revenue:.2f}."],
            "recommended_action": "Ensure UnitPrice and Quantity values are positive and accurately formatted.",
            "source_engine": "analytics_engine",
            "status": "Unavailable"
        })

    # Prepare data partitions for economic evidence formatting
    recent_df = pd.DataFrame()
    prev_df = pd.DataFrame()
    if split["split_valid"]:
        recent_df = prep_df[(prep_df["OrderDate"] >= split["recent_start"]) & (prep_df["OrderDate"] <= split["recent_end"])].copy()
        prev_df = prep_df[(prep_df["OrderDate"] >= split["prev_start"]) & (prep_df["OrderDate"] <= split["prev_end"])].copy()

    # ------------------ REVENUE HEALTH INSIGHTS ------------------
    rev_growth = bh_metrics["revenue_growth"]
    if rev_growth["status"] != "Insufficient Data":
        growth_val = rev_growth["value"]
        if growth_val is not None:
            prev_rev = prev_df["_Revenue"].sum() if not prev_df.empty else 0.0
            recent_rev = recent_df["_Revenue"].sum() if not recent_df.empty else 0.0
            rec_start_str = split["recent_start"].strftime("%Y-%m-%d") if split["recent_start"] else ""
            rec_end_str = split["recent_end"].strftime("%Y-%m-%d") if split["recent_end"] else ""
            prev_start_str = split["prev_start"].strftime("%Y-%m-%d") if split["prev_start"] else ""
            prev_end_str = split["prev_end"].strftime("%Y-%m-%d") if split["prev_end"] else ""

            if growth_val >= 10.0:
                insights_list.append({
                    "id": "rev_acceleration",
                    "domain": "Revenue",
                    "title": "Revenue Acceleration Detected",
                    "summary": f"Revenue expanded significantly by {growth_val:.1f}% compared to the prior period.",
                    "severity": "Positive",
                    "priority": 5,
                    "metric_name": "Revenue Growth Rate",
                    "metric_value": float(growth_val),
                    "comparison_value": 10.0,
                    "unit": "%",
                    "evidence": [
                        f"Recent period revenue ({rec_start_str} to {rec_end_str}) was {recent_rev:.2f}.",
                        f"Previous period revenue ({prev_start_str} to {prev_end_str}) was {prev_rev:.2f}.",
                        f"Net increase was {recent_rev - prev_rev:.2f} ({growth_val:.1f}%)."
                    ],
                    "recommended_action": "Maintain current sales momentum and identify the specific products or channels driving this expansion.",
                    "source_engine": "business_health_engine",
                    "status": "Strong"
                })
            elif -20.0 <= growth_val < -5.0:
                insights_list.append({
                    "id": "rev_softening",
                    "domain": "Revenue",
                    "title": "Revenue Growth Softening",
                    "summary": f"Revenue is showing signs of softening, contracting by {growth_val:.1f}% compared to the previous period.",
                    "severity": "Watch",
                    "priority": 2,
                    "metric_name": "Revenue Growth Rate",
                    "metric_value": float(growth_val),
                    "comparison_value": -5.0,
                    "unit": "%",
                    "evidence": [
                        f"Recent period revenue ({rec_start_str} to {rec_end_str}) was {recent_rev:.2f}.",
                        f"Previous period revenue ({prev_start_str} to {prev_end_str}) was {prev_rev:.2f}.",
                        f"Growth declined by {growth_val:.1f}%."
                    ],
                    "recommended_action": "Review conversion metrics, check for pricing adjustments, and monitor promotional cycles.",
                    "source_engine": "business_health_engine",
                    "status": "Watch"
                })
            elif growth_val < -20.0:
                insights_list.append({
                    "id": "rev_contraction",
                    "domain": "Revenue",
                    "title": "Revenue Contraction Warning",
                    "summary": f"Revenue contracted severely by {growth_val:.1f}% compared to the preceding period.",
                    "severity": "Risk",
                    "priority": 1,
                    "metric_name": "Revenue Growth Rate",
                    "metric_value": float(growth_val),
                    "comparison_value": -20.0,
                    "unit": "%",
                    "evidence": [
                        f"Recent period revenue ({rec_start_str} to {rec_end_str}) was {recent_rev:.2f}.",
                        f"Previous period revenue ({prev_start_str} to {prev_end_str}) was {prev_rev:.2f}.",
                        f"Revenue drop represented a severe contraction of {growth_val:.1f}%."
                    ],
                    "recommended_action": "Compare the declining period by product, customer segment, and geography to isolate the largest negative contributors.",
                    "source_engine": "business_health_engine",
                    "status": "Risk"
                })

    rev_vol = bh_metrics["revenue_volatility"]
    if rev_vol["status"] != "Insufficient Data":
        vol_val = rev_vol["value"]
        if vol_val is not None:
            if vol_val >= 2.0:
                insights_list.append({
                    "id": "rev_high_volatility",
                    "domain": "Revenue",
                    "title": "High Sales Volatility",
                    "summary": f"Sales revenue exhibits extreme volatility ({vol_val:.2f} CV) over the active period.",
                    "severity": "Risk",
                    "priority": 1,
                    "metric_name": "Revenue Volatility (CV)",
                    "metric_value": float(vol_val),
                    "comparison_value": 2.0,
                    "unit": "CV",
                    "evidence": [
                        f"The coefficient of variation is {vol_val:.2f}.",
                        f"Standard deviation of daily sales is wider than double the daily mean revenue."
                    ],
                    "recommended_action": "Review zero-sales days and high-revenue spikes separately to identify operational or demand irregularity.",
                    "source_engine": "business_health_engine",
                    "status": "Risk"
                })
            elif 1.2 <= vol_val < 2.0:
                insights_list.append({
                    "id": "rev_elevated_volatility",
                    "domain": "Revenue",
                    "title": "Elevated Sales Volatility",
                    "summary": f"Daily sales exhibit elevated swings ({vol_val:.2f} CV), highlighting demand or supply inconsistency.",
                    "severity": "Watch",
                    "priority": 2,
                    "metric_name": "Revenue Volatility (CV)",
                    "metric_value": float(vol_val),
                    "comparison_value": 1.2,
                    "unit": "CV",
                    "evidence": [
                        f"The coefficient of variation is {vol_val:.2f}.",
                        f"Daily sales distributions reflect moderate chronological irregularity."
                    ],
                    "recommended_action": "Analyze promotional dates and key distributor calendars to identify events spikes and normalize dispatch dates.",
                    "source_engine": "business_health_engine",
                    "status": "Watch"
                })

    # ------------------ CUSTOMER HEALTH INSIGHTS ------------------
    if has_customer:
        repeat_rate = bh_metrics["repeat_rate"]
        if repeat_rate["status"] != "Insufficient Data":
            rep_val = repeat_rate["value"]
            if rep_val is not None:
                if rep_val < 10.0:
                    insights_list.append({
                        "id": "cust_low_retention",
                        "domain": "Customers",
                        "title": "Critical Customer Retention Risk",
                        "summary": f"An extremely low repeat buyer rate of {rep_val:.1f}% indicates high acquisition churn dependency.",
                        "severity": "Risk",
                        "priority": 1,
                        "metric_name": "Repeat Buyer Rate",
                        "metric_value": float(rep_val),
                        "comparison_value": 10.0,
                        "unit": "%",
                        "evidence": [
                            f"Repeat buyers drive only {rep_val:.1f}% of total customer counts.",
                            f"Acquisition strategy relies almost fully on one-time transactions ({100.0 - rep_val:.1f}%)."
                        ],
                        "recommended_action": "Review repeat-purchase cohorts, post-purchase engagement, and retention offers before increasing acquisition dependence.",
                        "source_engine": "business_health_engine",
                        "status": "Risk"
                    })
                elif 10.0 <= rep_val < 20.0:
                    insights_list.append({
                        "id": "cust_weak_retention",
                        "domain": "Customers",
                        "title": "Weak Repeat Customer Retention",
                        "summary": f"Repeat buyer rate of {rep_val:.1f}% is weak, reflecting potential barriers to secondary purchases.",
                        "severity": "Watch",
                        "priority": 2,
                        "metric_name": "Repeat Buyer Rate",
                        "metric_value": float(rep_val),
                        "comparison_value": 20.0,
                        "unit": "%",
                        "evidence": [
                            f"Repeat buyer proportion is {rep_val:.1f}%.",
                            f"One-time buyers account for {100.0 - rep_val:.1f}% of active accounts."
                        ],
                        "recommended_action": "Initiate email re-engagement flows and evaluate product quality feedbacks from early cohorts.",
                        "source_engine": "business_health_engine",
                        "status": "Watch"
                    })
                elif rep_val >= 40.0:
                    insights_list.append({
                        "id": "cust_strong_retention",
                        "domain": "Customers",
                        "title": "Healthy Repeat Customer Retention",
                        "summary": f"Strong repeat customer rate of {rep_val:.1f}% reinforces sustained satisfaction and repeat demand.",
                        "severity": "Positive",
                        "priority": 5,
                        "metric_name": "Repeat Buyer Rate",
                        "metric_value": float(rep_val),
                        "comparison_value": 40.0,
                        "unit": "%",
                        "evidence": [
                            f"Repeat customer cohort accounts for {rep_val:.1f}% of active transacting customers."
                        ],
                        "recommended_action": "Establish loyalty rewards programs to compound retention benefits among high-affinity cohorts.",
                        "source_engine": "business_health_engine",
                        "status": "Strong"
                    })

        cust_con_metric = bh_metrics["top5_customer_concentration"]
        if cust_con_metric["status"] != "Insufficient Data" and cust_con_metric.get("entity_count", 0) >= 5:
            con_val = cust_con_metric["value"]
            if con_val is not None:
                if con_val >= 70.0:
                    insights_list.append({
                        "id": "cust_concentration_high",
                        "domain": "Customers",
                        "title": "High Customer Concentration Risk",
                        "summary": f"Top 5 customers account for {con_val:.1f}% of total revenue, representing severe portfolio exposure.",
                        "severity": "Risk",
                        "priority": 1,
                        "metric_name": "Top-5 Customer Concentration",
                        "metric_value": float(con_val),
                        "comparison_value": 70.0,
                        "unit": "%",
                        "evidence": [
                            f"Concentration exposure value is {con_val:.1f}% of revenue.",
                            "Loss of a single key client could severely derail operational safety."
                        ],
                        "recommended_action": "Review revenue exposure to the highest-contributing customers and evaluate diversification opportunities.",
                        "source_engine": "business_health_engine",
                        "status": "Risk"
                    })
                elif 50.0 <= con_val < 70.0:
                    insights_list.append({
                        "id": "cust_concentration_medium",
                        "domain": "Customers",
                        "title": "Elevated Customer Concentration",
                        "summary": f"Top 5 customers account for {con_val:.1f}% of total sales. Moderate concentration signals growing top-account reliance.",
                        "severity": "Watch",
                        "priority": 2,
                        "metric_name": "Top-5 Customer Concentration",
                        "metric_value": float(con_val),
                        "comparison_value": 50.0,
                        "unit": "%",
                        "evidence": [
                            f"Five customer entities compose {con_val:.1f}% of total net sales."
                        ],
                        "recommended_action": "Examine pricing agreements with top-tier buyers and align sales reps to acquire mid-market clients.",
                        "source_engine": "business_health_engine",
                        "status": "Watch"
                    })
                elif con_val < 20.0:
                    insights_list.append({
                        "id": "cust_concentration_low",
                        "domain": "Customers",
                        "title": "Low Customer Concentration",
                        "summary": f"Top 5 customers account for only {con_val:.1f}% of revenue, indicating a highly diversified buyer range.",
                        "severity": "Positive",
                        "priority": 5,
                        "metric_name": "Top-5 Customer Concentration",
                        "metric_value": float(con_val),
                        "comparison_value": 20.0,
                        "unit": "%",
                        "evidence": [
                            f"Top 5 customers compose only {con_val:.1f}% of total sales."
                        ],
                        "recommended_action": "Continue leveraging this balanced exposure to explore new market niches.",
                        "source_engine": "business_health_engine",
                        "status": "Strong"
                    })

    # ------------------ PRODUCT HEALTH INSIGHTS ------------------
    if has_product:
        # Top-1 Product Concentration
        top1_metric = bh_metrics["top1_product_concentration"]
        if top1_metric["status"] != "Insufficient Data":
            t1_val = top1_metric["value"]
            if t1_val is not None:
                if t1_val >= 50.0:
                    insights_list.append({
                        "id": "prod_top1_dependency_high",
                        "domain": "Products",
                        "title": "High Single Product Dependency Risk",
                        "summary": f"The leading product dominates catalog revenue, contributing {t1_val:.1f}% of aggregate net transactions.",
                        "severity": "Risk",
                        "priority": 1,
                        "metric_name": "Top-1 Product Concentration",
                        "metric_value": float(t1_val),
                        "comparison_value": 50.0,
                        "unit": "%",
                        "evidence": [
                            f"Single product SKU drives {t1_val:.1f}% of total revenue.",
                            "Operational issues or supply interruptions for this item would represent immediate failure exposure."
                        ],
                        "recommended_action": "Review category depth and secondary product contribution before increasing reliance on the leading product.",
                        "source_engine": "business_health_engine",
                        "status": "Risk"
                    })
                elif 30.0 <= t1_val < 50.0:
                    insights_list.append({
                        "id": "prod_top1_dependency_medium",
                        "domain": "Products",
                        "title": "Elevated Single Product Dependency",
                        "summary": f"The leading product contributes {t1_val:.1f}% of sales. Mindful catalog dependency detected.",
                        "severity": "Watch",
                        "priority": 2,
                        "metric_name": "Top-1 Product Concentration",
                        "metric_value": float(t1_val),
                        "comparison_value": 30.0,
                        "unit": "%",
                        "evidence": [
                            f"Top SKU commands {t1_val:.1f}% of overall revenue."
                        ],
                        "recommended_action": "Build promotional bundles pairing the top product with emerging SKUs to encourage portfolio diversification.",
                        "source_engine": "business_health_engine",
                        "status": "Watch"
                    })

        # Top-5 Product Concentration
        top5_metric = bh_metrics["top5_product_concentration"]
        if top5_metric["status"] != "Insufficient Data" and top5_metric.get("entity_count", 0) >= 5:
            t5_val = top5_metric["value"]
            if t5_val is not None:
                if t5_val >= 80.0:
                    insights_list.append({
                        "id": "prod_top5_concentration_high",
                        "domain": "Products",
                        "title": "High Portfolio Concentration Risk",
                        "summary": f"The top 5 product SKUs generate {t5_val:.1f}% of aggregate sales revenue.",
                        "severity": "Risk",
                        "priority": 1,
                        "metric_name": "Top-5 Product Concentration",
                        "metric_value": float(t5_val),
                        "comparison_value": 80.0,
                        "unit": "%",
                        "evidence": [
                            f"Top 5 items dictate {t5_val:.1f}% of portfolio revenue.",
                            "The downstream catalog remains largely inactive or economically minor."
                        ],
                        "recommended_action": "Review category depth and marketing spend allocation to encourage wider catalog coverage.",
                        "source_engine": "business_health_engine",
                        "status": "Risk"
                    })
                elif 60.0 <= t5_val < 80.0:
                    insights_list.append({
                        "id": "prod_top5_concentration_medium",
                        "domain": "Products",
                        "title": "Elevated Portfolio Concentration",
                        "summary": f"Top 5 product items command {t5_val:.1f}% of sales. Long-tail products remain underutilized.",
                        "severity": "Watch",
                        "priority": 2,
                        "metric_name": "Top-5 Product Concentration",
                        "metric_value": float(t5_val),
                        "comparison_value": 60.0,
                        "unit": "%",
                        "evidence": [
                            f"Top 5 catalog SKUs compose {t5_val:.1f}% of active transactions."
                        ],
                        "recommended_action": "Explore bundling low-performing items with primary items to clear stagnant shelf stocks.",
                        "source_engine": "business_health_engine",
                        "status": "Watch"
                    })
                elif t5_val < 40.0:
                    insights_list.append({
                        "id": "prod_top5_concentration_low",
                        "domain": "Products",
                        "title": "Well-Diversified Product Portfolio",
                        "summary": f"Top 5 product items account for only {t5_val:.1f}% of revenue, showing healthy catalog distribution.",
                        "severity": "Positive",
                        "priority": 5,
                        "metric_name": "Top-5 Product Concentration",
                        "metric_value": float(t5_val),
                        "comparison_value": 40.0,
                        "unit": "%",
                        "evidence": [
                            f"Top 5 product concentration exposure is {t5_val:.1f}%."
                        ],
                        "recommended_action": "Promote balanced expansion across multiple product divisions.",
                        "source_engine": "business_health_engine",
                        "status": "Strong"
                    })

        # Low Revenue Contribution Product Share
        low_perf_metric = bh_metrics["low_performing_share"]
        if low_perf_metric["status"] != "Insufficient Data":
            lp_val = low_perf_metric["value"]
            if lp_val is not None:
                if lp_val >= 75.0:
                    insights_list.append({
                        "id": "prod_low_performing_high",
                        "domain": "Products",
                        "title": "Excessive Underperforming Catalog",
                        "summary": f"{lp_val:.1f}% of products contribute less than 0.5% each to total revenue, indicating catalog bloat.",
                        "severity": "Risk",
                        "priority": 1,
                        "metric_name": "Low-Performing Product Share",
                        "metric_value": float(lp_val),
                        "comparison_value": 75.0,
                        "unit": "%",
                        "evidence": [
                            f"Catalog low contribution share is {lp_val:.1f}% of items.",
                            "A significant portion of products creates storage and inventory cost overhead without providing material sales return."
                        ],
                        "recommended_action": "Execute a catalog audit to prune or phase out dead stock and optimize warehousing resource capacity.",
                        "source_engine": "business_health_engine",
                        "status": "Risk"
                    })
                elif 50.0 <= lp_val < 75.0:
                    insights_list.append({
                        "id": "prod_low_performing_medium",
                        "domain": "Products",
                        "title": "Elevated Underperforming Catalog",
                        "summary": f"{lp_val:.1f}% of items generate marginal individual returns (<0.5%).",
                        "severity": "Watch",
                        "priority": 2,
                        "metric_name": "Low-Performing Product Share",
                        "metric_value": float(lp_val),
                        "comparison_value": 50.0,
                        "unit": "%",
                        "evidence": [
                            f"Stagnant items represent {lp_val:.1f}% of total catalog SKU count."
                        ],
                        "recommended_action": "Optimize vendor purchase frequencies for slow items to match localized demand levels.",
                        "source_engine": "business_health_engine",
                        "status": "Watch"
                    })
                elif lp_val < 20.0:
                    insights_list.append({
                        "id": "prod_low_performing_low",
                        "domain": "Products",
                        "title": "Highly Active Product Catalog",
                        "summary": f"Only {lp_val:.1f}% of products are low-performing, showing broad active sales velocity across the catalog.",
                        "severity": "Positive",
                        "priority": 5,
                        "metric_name": "Low-Performing Product Share",
                        "metric_value": float(lp_val),
                        "comparison_value": 20.0,
                        "unit": "%",
                        "evidence": [
                            f"Active catalog items represent {100.0 - lp_val:.1f}% of portfolio SKU list."
                        ],
                        "recommended_action": "Establish standard restocking automation channels to keep high active availability rates.",
                        "source_engine": "business_health_engine",
                        "status": "Strong"
                    })

        # Pareto Dependency
        pareto_metric = bh_metrics["pareto_share"]
        if pareto_metric["status"] != "Insufficient Data":
            par_val = pareto_metric["value"]
            if par_val is not None:
                if par_val < 10.0:
                    insights_list.append({
                        "id": "prod_pareto_share_low",
                        "domain": "Products",
                        "title": "Extreme Product Pareto Concentration",
                        "summary": f"Fewer than {par_val:.1f}% of products generate 80% of total revenue. Sales rely on an extremely narrow core.",
                        "severity": "Risk",
                        "priority": 2,
                        "metric_name": "Pareto Revenue Share",
                        "metric_value": float(par_val),
                        "comparison_value": 10.0,
                        "unit": "%",
                        "evidence": [
                            f"Only {par_val:.1f}% of active items generate 80% of net sales."
                        ],
                        "recommended_action": "Introduce brand marketing budgets targeting secondary categories to distribute demand across a broader shelf mix.",
                        "source_engine": "business_health_engine",
                        "status": "Risk"
                    })
                elif 10.0 <= par_val < 20.0:
                    insights_list.append({
                        "id": "prod_pareto_share_medium",
                        "domain": "Products",
                        "title": "Elevated Product Pareto Concentration",
                        "summary": f"Top 80% of revenue is driven by {par_val:.1f}% of items, reflecting standard Pareto concentration.",
                        "severity": "Watch",
                        "priority": 3,
                        "metric_name": "Pareto Revenue Share",
                        "metric_value": float(par_val),
                        "comparison_value": 20.0,
                        "unit": "%",
                        "evidence": [
                            f"{par_val:.1f}% of items represent the active sales kernel."
                        ],
                        "recommended_action": "Build customer loyalty programs offering dynamic redemptions covering low-concentration catalog segments.",
                        "source_engine": "business_health_engine",
                        "status": "Watch"
                    })
                elif par_val >= 30.0:
                    insights_list.append({
                        "id": "prod_pareto_share_high",
                        "domain": "Products",
                        "title": "Balanced Portfolio Revenue Share",
                        "summary": f"A balanced proportion of products ({par_val:.1f}%) contributes to 80% of sales, indicating healthy category distribution.",
                        "severity": "Positive",
                        "priority": 5,
                        "metric_name": "Pareto Revenue Share",
                        "metric_value": float(par_val),
                        "comparison_value": 30.0,
                        "unit": "%",
                        "evidence": [
                            f"Exactly {par_val:.1f}% of active SKUs drive 80% of revenue." if par_val >= 100.0 else f"More than {par_val:.1f}% of active SKUs drive 80% of revenue."
                        ],
                        "recommended_action": "Maintain this balanced shelf mix and monitor customer segment preferences across active categories.",
                        "source_engine": "business_health_engine",
                        "status": "Strong"
                    })

    # ------------------ ORDER ECONOMICS INSIGHTS ------------------
    if split["split_valid"] and not recent_df.empty and not prev_df.empty:
        prev_orders = prev_df["OrderID"].nunique()
        recent_orders = recent_df["OrderID"].nunique()
        prev_rev = prev_df["_Revenue"].sum()
        recent_rev = recent_df["_Revenue"].sum()

        prev_aov = prev_rev / prev_orders if prev_orders > 0 else 0.0
        recent_aov = recent_rev / recent_orders if recent_orders > 0 else 0.0

        prev_units = prev_df["Quantity"].sum()
        recent_units = recent_df["Quantity"].sum()
        prev_upo = prev_units / prev_orders if prev_orders > 0 else 0.0
        recent_upo = recent_units / recent_orders if recent_orders > 0 else 0.0

        # AOV Economics
        aov_metric = bh_metrics["aov_growth"]
        if aov_metric["status"] != "Insufficient Data":
            aov_growth_val = aov_metric["value"]
            if aov_growth_val is not None:
                evidence_text = [
                    f"Recent average order value was {recent_aov:.2f}.",
                    f"Previous average order value was {prev_aov:.2f}.",
                    f"Average Order Value changed by {aov_growth_val:.1f}%."
                ]
                if aov_growth_val >= 5.0:
                    insights_list.append({
                        "id": "econ_aov_strong",
                        "domain": "Order Economics",
                        "title": "AOV Expansion Detected",
                        "summary": f"Average order value (AOV) increased by {aov_growth_val:.1f}% relative to the previous period.",
                        "severity": "Positive",
                        "priority": 5,
                        "metric_name": "AOV Growth Rate",
                        "metric_value": float(aov_growth_val),
                        "comparison_value": 5.0,
                        "unit": "%",
                        "evidence": evidence_text,
                        "recommended_action": "Monitor this basket size expansion and leverage up-selling paths to increase transaction yield.",
                        "source_engine": "business_health_engine",
                        "status": "Strong"
                    })
                elif aov_growth_val < -10.0:
                    insights_list.append({
                        "id": "econ_aov_risk",
                        "domain": "Order Economics",
                        "title": "Average Order Value Risk",
                        "summary": f"Average order value (AOV) declined by {aov_growth_val:.1f}% compared to the prior period.",
                        "severity": "Risk",
                        "priority": 1,
                        "metric_name": "AOV Growth Rate",
                        "metric_value": float(aov_growth_val),
                        "comparison_value": -10.0,
                        "unit": "%",
                        "evidence": evidence_text,
                        "recommended_action": "Investigate discounting trends, pricing adjustments, or shifts in customer basket composition.",
                        "source_engine": "business_health_engine",
                        "status": "Risk"
                    })
                elif -10.0 <= aov_growth_val < -2.0:
                    insights_list.append({
                        "id": "econ_aov_watch",
                        "domain": "Order Economics",
                        "title": "AOV Growth Decline",
                        "summary": f"Average order value (AOV) is showing minor decline, dropping by {aov_growth_val:.1f}%.",
                        "severity": "Watch",
                        "priority": 2,
                        "metric_name": "AOV Growth Rate",
                        "metric_value": float(aov_growth_val),
                        "comparison_value": -2.0,
                        "unit": "%",
                        "evidence": evidence_text,
                        "recommended_action": "Review average unit price configurations and evaluate minimum order thresholds for free shipping promotions.",
                        "source_engine": "business_health_engine",
                        "status": "Watch"
                    })

        # UPO Economics
        upo_metric = bh_metrics["upo_growth"]
        if upo_metric["status"] != "Insufficient Data":
            upo_growth_val = upo_metric["value"]
            if upo_growth_val is not None:
                evidence_text = [
                    f"Recent average units per order was {recent_upo:.2f}.",
                    f"Previous average units per order was {prev_upo:.2f}.",
                    f"Units per order changed by {upo_growth_val:.1f}%."
                ]
                if upo_growth_val >= 5.0:
                    insights_list.append({
                        "id": "econ_upo_strong",
                        "domain": "Order Economics",
                        "title": "UPO Growth Detected",
                        "summary": f"Units per order (UPO) increased by {upo_growth_val:.1f}% relative to the previous period.",
                        "severity": "Positive",
                        "priority": 5,
                        "metric_name": "UPO Growth Rate",
                        "metric_value": float(upo_growth_val),
                        "comparison_value": 5.0,
                        "unit": "%",
                        "evidence": evidence_text,
                        "recommended_action": "Highlight catalog cross-sell choices to keep boosting items count per transaction.",
                        "source_engine": "business_health_engine",
                        "status": "Strong"
                    })
                elif upo_growth_val < -10.0:
                    insights_list.append({
                        "id": "econ_upo_risk",
                        "domain": "Order Economics",
                        "title": "Units Per Order Risk",
                        "summary": f"Units per order (UPO) declined by {upo_growth_val:.1f}% compared to the prior period.",
                        "severity": "Risk",
                        "priority": 1,
                        "metric_name": "UPO Growth Rate",
                        "metric_value": float(upo_growth_val),
                        "comparison_value": -10.0,
                        "unit": "%",
                        "evidence": evidence_text,
                        "recommended_action": "Evaluate bundle strategies, wholesale pricing configurations, and minimum transaction quantites.",
                        "source_engine": "business_health_engine",
                        "status": "Risk"
                    })
                elif -10.0 <= upo_growth_val < -2.0:
                    insights_list.append({
                        "id": "econ_upo_watch",
                        "domain": "Order Economics",
                        "title": "UPO Growth Decline",
                        "summary": f"Average units per order is showing mild decline, contracting by {upo_growth_val:.1f}%.",
                        "severity": "Watch",
                        "priority": 2,
                        "metric_name": "UPO Growth Rate",
                        "metric_value": float(upo_growth_val),
                        "comparison_value": -2.0,
                        "unit": "%",
                        "evidence": evidence_text,
                        "recommended_action": "Construct promo packages offering tiered unit discounts (e.g. buy 3 spend less) to incentivize volume purchases.",
                        "source_engine": "business_health_engine",
                        "status": "Watch"
                    })

        # RPC Economics (do not generate if customer identity unavailable)
        if has_customer:
            rpc_metric = bh_metrics["rpc_growth"]
            if rpc_metric["status"] != "Insufficient Data":
                rpc_growth_val = rpc_metric["value"]
                if rpc_growth_val is not None:
                    # Recalculate customers counts matching business health approach
                    prev_custs_count = prev_df["CustomerID"].nunique() if "CustomerID" in prev_df.columns else prev_df["CustomerName"].nunique() if "CustomerName" in prev_df.columns else 0
                    recent_custs_count = recent_df["CustomerID"].nunique() if "CustomerID" in recent_df.columns else recent_df["CustomerName"].nunique() if "CustomerName" in recent_df.columns else 0
                    prev_rpc = prev_rev / prev_custs_count if prev_custs_count > 0 else 0.0
                    recent_rpc = recent_rev / recent_custs_count if recent_custs_count > 0 else 0.0

                    evidence_text = [
                        f"Recent revenue per customer was {recent_rpc:.2f}.",
                        f"Previous revenue per customer was {prev_rpc:.2f}.",
                        f"Revenue per customer changed by {rpc_growth_val:.1f}%."
                    ]
                    if rpc_growth_val >= 5.0:
                        insights_list.append({
                            "id": "econ_rpc_strong",
                            "domain": "Order Economics",
                            "title": "RPC Growth Detected",
                            "summary": f"Revenue per customer (RPC) increased by {rpc_growth_val:.1f}% compared to the prior period.",
                            "severity": "Positive",
                            "priority": 5,
                            "metric_name": "RPC Growth Rate",
                            "metric_value": float(rpc_growth_val),
                            "comparison_value": 5.0,
                            "unit": "%",
                            "evidence": evidence_text,
                            "recommended_action": "Optimize your account management resources to cross-sell additional value to top-revenue client tiers.",
                            "source_engine": "business_health_engine",
                            "status": "Strong"
                        })
                    elif rpc_growth_val < -10.0:
                        insights_list.append({
                            "id": "econ_rpc_risk",
                            "domain": "Order Economics",
                            "title": "Revenue Per Customer Risk",
                            "summary": f"Revenue per customer (RPC) declined by {rpc_growth_val:.1f}% compared to the previous period.",
                            "severity": "Risk",
                            "priority": 1,
                            "metric_name": "RPC Growth Rate",
                            "metric_value": float(rpc_growth_val),
                            "comparison_value": -10.0,
                            "unit": "%",
                            "evidence": evidence_text,
                            "recommended_action": "Investigate decline in purchase frequency or customer segment shifts affecting average customer lifetime spend.",
                            "source_engine": "business_health_engine",
                            "status": "Risk"
                        })
                    elif -10.0 <= rpc_growth_val < -2.0:
                        insights_list.append({
                            "id": "econ_rpc_watch",
                            "domain": "Order Economics",
                            "title": "RPC Growth Decline",
                            "summary": f"Average revenue per customer has softened by {rpc_growth_val:.1f}%.",
                            "severity": "Watch",
                            "priority": 2,
                            "metric_name": "RPC Growth Rate",
                            "metric_value": float(rpc_growth_val),
                            "comparison_value": -2.0,
                            "unit": "%",
                            "evidence": evidence_text,
                            "recommended_action": "Review client-level purchase logs and dispatch retention campaigns targeting segments showing buying deceleration.",
                            "source_engine": "business_health_engine",
                            "status": "Watch"
                        })

    # ------------------ FORECAST READINESS INSIGHTS ------------------
    # Reuse Forecast Engine output directly (always run checking Daily context)
    f_caps = detect_forecast_capabilities(prep_df, "Daily")
    f_state = f_caps.get("capability_state", "UNAVAILABLE")
    f_reasons = f_caps.get("capability_reasons", [])

    if f_state == "SUITABLE":
        insights_list.append({
            "id": "fc_readiness_suitable",
            "domain": "Forecast Readiness",
            "title": "Forecast Engine Fully Ready",
            "summary": "Chronological sales data quality and span support robust validation and predictive forecast modeling.",
            "severity": "Positive",
            "priority": 5,
            "metric_name": "Forecast Capability",
            "metric_value": None,
            "comparison_value": None,
            "unit": None,
            "evidence": ["Dataset satisfies all chronological requirements for robust forecasting."],
            "recommended_action": "Navigate to the Forecast tab to model future revenue trajectories.",
            "source_engine": "forecast_engine",
            "status": "Ready"
        })
    elif f_state == "LIMITED":
        reasons_msg = "; ".join(f_reasons)
        insights_list.append({
            "id": "fc_readiness_limited",
            "domain": "Forecast Readiness",
            "title": "Forecast Engine Capabilities Limited",
            "summary": f"Forecast modeling is available, but running in compressed/limited mode. Limits: {reasons_msg}.",
            "severity": "Watch",
            "priority": 3,
            "metric_name": "Forecast Capability",
            "metric_value": None,
            "comparison_value": None,
            "unit": None,
            "evidence": [f"Current validation triggers compressed mode: {r}" for r in f_reasons],
            "recommended_action": "Use predictions with caution as back-testing validity intervals are compressed.",
            "source_engine": "forecast_engine",
            "status": "Limited"
        })
    else:  # UNAVAILABLE
        reasons_msg = "; ".join(f_reasons)
        insights_list.append({
            "id": "fc_readiness_unavailable",
            "domain": "Forecast Modeling Unavailable",
            "title": "Forecast Modeling Unavailable",
            "summary": f"Chronological sales history is insufficient to generate reliable forecast baseline projections. Limits: {reasons_msg}.",
            "severity": "Informational",
            "priority": 4,
            "metric_name": "Forecast Capability",
            "metric_value": None,
            "comparison_value": None,
            "unit": None,
            "evidence": [f"Downstream forecasting disabled: {r}" for r in f_reasons],
            "recommended_action": "Collect additional chronological sales history before relying on forecast projections.",
            "source_engine": "forecast_engine",
            "status": "Unavailable"
        })

    # 3. Deduplication (semantic product constraints)
    deduped = deduplicate_insights(insights_list)

    # 4. Deterministic sorting
    sorted_res = sort_insights(deduped)

    # 5. Populate and filter return lists
    result["insights"] = sorted_res
    result["priority_insights"] = [i for i in sorted_res if i["priority"] in [1, 2]]
    result["risk_insights"] = [i for i in sorted_res if i["severity"] == "Risk"]
    result["watch_insights"] = [i for i in sorted_res if i["severity"] == "Watch"]
    result["positive_insights"] = [i for i in sorted_res if i["severity"] == "Positive"]
    result["informational_insights"] = [i for i in sorted_res if i["severity"] == "Informational"]

    # Compute actual counts
    for i in sorted_res:
        domain = i["domain"]
        severity = i["severity"]
        # Map domain key if named slightly differently
        if domain == "Forecast Modeling Unavailable":
            domain = "Forecast Readiness"
        if domain in result["domain_counts"]:
            result["domain_counts"][domain] += 1
        if severity in result["severity_counts"]:
            result["severity_counts"][severity] += 1

    # Metadata updates
    result["metadata"]["insight_count"] = len(sorted_res)
    result["metadata"]["insufficient_domains"] = sorted(list(set(unsat_domains)))
    result["metadata"]["calculable_domain_count"] = 4 - len(result["metadata"]["insufficient_domains"])

    return result
