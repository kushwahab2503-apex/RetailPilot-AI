import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timedelta
import math

from backend.analytics_engine import prepare_analytics_dataset
from backend.customer_engine import prepare_customer_dataset, calculate_lifetime_customer_base, get_customer_period_performance
from backend.product_engine import prepare_product_dataset, get_product_performance, get_pareto_data
from backend.forecast_engine import detect_forecast_capabilities


def calculate_period_split_dates(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes equal comparison windows anchored at max(OrderDate).
    - Determine active date span in calendar days.
    - comparison_window_days = floor(total_span_days / 2)
    - Recent window: last comparison_window_days calendar days ending at max_date, inclusive.
    - Previous window: immediately preceding equal-length calendar window.
    - Unmatched earliest days are excluded.
    """
    default_split = {
        "span_days": 0,
        "window_size": 0,
        "recent_start": None,
        "recent_end": None,
        "prev_start": None,
        "prev_end": None,
        "is_valid": False
    }

    if df.empty or "OrderDate" not in df.columns:
        return default_split

    dates = pd.to_datetime(df["OrderDate"], errors="coerce").dropna()
    if dates.empty:
        return default_split

    min_date = dates.min()
    max_date = dates.max()

    span_days = (max_date - min_date).days + 1
    window_size = span_days // 2

    if window_size < 1:
        return {
            "span_days": span_days,
            "window_size": 0,
            "recent_start": None,
            "recent_end": max_date,
            "prev_start": None,
            "prev_end": None,
            "is_valid": False
        }

    # Recent Window
    recent_end = max_date
    recent_start = max_date - timedelta(days=window_size - 1)

    # Previous Window
    prev_end = recent_start - timedelta(days=1)
    prev_start = recent_start - timedelta(days=window_size)

    return {
        "span_days": span_days,
        "window_size": window_size,
        "recent_start": recent_start,
        "recent_end": recent_end,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "is_valid": True
    }


def calculate_daily_volatility(df: pd.DataFrame, min_date: datetime, max_date: datetime) -> Optional[float]:
    """
    Aggregates daily sales revenue over the complete min-to-max timeline context
    filling any missing calendar days with zero, yielding CV (std / mean) with ddof=1.
    """
    if df.empty or pd.isna(min_date) or pd.isna(max_date):
        return None

    # Force normalize OrderDate to date
    work_df = df.copy()
    work_df["OrderDate_Day"] = pd.to_datetime(work_df["OrderDate"]).dt.normalize()

    daily = work_df.groupby("OrderDate_Day")["_Revenue"].sum()
    
    # Complete daily range reindexing
    start_point = pd.Timestamp(min_date).normalize()
    end_point = pd.Timestamp(max_date).normalize()
    all_days = pd.date_range(start=start_point, end=end_point, freq='D')
    
    daily = daily.reindex(all_days, fill_value=0.0)

    mean_rev = daily.mean()
    if mean_rev <= 0 or len(daily) < 10:
        return None

    std_rev = daily.std(ddof=1)
    if pd.isna(std_rev):
        return None

    return float(std_rev / mean_rev)


def evaluate_business_health(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Aggregates indicators across all 4 key business performance domains and Forecast Readiness.
    Stateless and Streamlit-independent entry point return.
    """
    # 1. Initialize result structure with defaults
    result = {
        "dates_metadata": {
            "min_date": None,
            "max_date": None,
            "span_days": 0,
            "window_size": 0,
            "recent_start": None,
            "recent_end": None,
            "prev_start": None,
            "prev_end": None,
            "split_valid": False
        },
        "metrics": {
            # Revenue Domain
            "revenue_growth": {"value": None, "status": "Insufficient Data"},
            "revenue_volatility": {"value": None, "status": "Insufficient Data"},
            
            # Customer Domain
            "repeat_rate": {"value": None, "status": "Insufficient Data"},
            "onetime_dependence": {"value": None, "status": "Insufficient Data"},
            "top5_customer_concentration": {"value": None, "status": "Insufficient Data", "entity_count": 0, "context": "Normal"},
            
            # Product Domain
            "top5_product_concentration": {"value": None, "status": "Insufficient Data", "entity_count": 0, "context": "Normal"},
            "top1_product_concentration": {"value": None, "status": "Insufficient Data"},
            "pareto_share": {"value": None, "status": "Insufficient Data"},
            "low_performing_share": {"value": None, "status": "Insufficient Data"},
            
            # Economics Domain
            "aov_growth": {"value": None, "status": "Insufficient Data"},
            "upo_growth": {"value": None, "status": "Insufficient Data"},
            "rpc_growth": {"value": None, "status": "Insufficient Data"},
            
            # Forecast Readiness Domain
            "forecast_readiness": {"value": "UNAVAILABLE", "status": "Risk", "reasons": ["Dataset empty or invalid"]}
        },
        "domain_statuses": {
            "revenue_health": "Insufficient Data",
            "customer_health": "Insufficient Data",
            "product_health": "Insufficient Data",
            "order_economics": "Insufficient Data",
            "forecast_readiness": "Risk"
        },
        "overall_status": "Insufficient Data",
        "indicator_counts": {
            "Strong": 0,
            "Stable": 0,
            "Watch": 0,
            "Risk": 0,
            "Insufficient Data": 4
        },
        "executive_findings": {
            "strengths": [],
            "risks": [],
            "watches": [],
            "limitations": []
        }
    }

    if df is None or df.empty:
        return result

    # 2. Data Preparation via existing validation structures
    prep_df, prep_meta = prepare_analytics_dataset(df)
    if prep_df.empty:
        return result

    min_date = prep_df["OrderDate"].min()
    max_date = prep_df["OrderDate"].max()

    # 3. Period splits
    split = calculate_period_split_dates(prep_df)
    result["dates_metadata"] = {
        "min_date": min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else None,
        "max_date": max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None,
        "span_days": split["span_days"],
        "window_size": split["window_size"],
        "recent_start": split["recent_start"].strftime("%Y-%m-%d") if split["recent_start"] else None,
        "recent_end": split["recent_end"].strftime("%Y-%m-%d") if split["recent_end"] else None,
        "prev_start": split["prev_start"].strftime("%Y-%m-%d") if split["prev_start"] else None,
        "prev_end": split["prev_end"].strftime("%Y-%m-%d") if split["prev_end"] else None,
        "split_valid": split["is_valid"]
    }

    # Split df if split is valid
    recent_df = pd.DataFrame()
    prev_df = pd.DataFrame()
    if split["is_valid"]:
        recent_df = prep_df[(prep_df["OrderDate"] >= split["recent_start"]) & (prep_df["OrderDate"] <= split["recent_end"])].copy()
        prev_df = prep_df[(prep_df["OrderDate"] >= split["prev_start"]) & (prep_df["OrderDate"] <= split["prev_end"])].copy()

    # Check available columns
    has_customer = "CustomerID" in df.columns or "CustomerName" in df.columns
    has_product = "ProductID" in df.columns or "ProductName" in df.columns

    # ------------------ REVENUE HEALTH DOMAIN ------------------
    # Revenue Growth
    if split["is_valid"] and len(prev_df) > 0 and len(recent_df) > 0:
        prev_rev = prev_df["_Revenue"].sum()
        recent_rev = recent_df["_Revenue"].sum()
        if split["span_days"] < 14:
            result["metrics"]["revenue_growth"] = {"value": None, "status": "Insufficient Data"}
        elif prev_rev <= 0:
            result["metrics"]["revenue_growth"] = {"value": None, "status": "Insufficient Data"}
        else:
            growth = ((recent_rev - prev_rev) / prev_rev) * 100.0
            result["metrics"]["revenue_growth"]["value"] = float(growth)
            if growth >= 10.0:
                result["metrics"]["revenue_growth"]["status"] = "Strong"
            elif growth >= -5.0:
                result["metrics"]["revenue_growth"]["status"] = "Stable"
            elif growth >= -20.0:
                result["metrics"]["revenue_growth"]["status"] = "Watch"
            else:
                result["metrics"]["revenue_growth"]["status"] = "Risk"
    else:
        result["metrics"]["revenue_growth"] = {"value": None, "status": "Insufficient Data"}

    # Daily Volatility
    vol = calculate_daily_volatility(prep_df, min_date, max_date)
    if vol is not None:
        result["metrics"]["revenue_volatility"]["value"] = vol
        if vol < 0.50:
            result["metrics"]["revenue_volatility"]["status"] = "Strong"
        elif vol < 1.20:
            result["metrics"]["revenue_volatility"]["status"] = "Stable"
        elif vol < 2.00:
            result["metrics"]["revenue_volatility"]["status"] = "Watch"
        else:
            result["metrics"]["revenue_volatility"]["status"] = "Risk"

    # ------------------ CUSTOMER HEALTH DOMAIN ------------------
    if has_customer:
        cust_prep, cust_meta = prepare_customer_dataset(df)
        if not cust_prep.empty:
            lifetime_base = calculate_lifetime_customer_base(cust_prep)
            
            # Repeat Rate (using lifetime repeat status for customers active in the full period)
            tot_customers = cust_prep["Customer_Key"].nunique()
            active_keys = cust_prep["Customer_Key"].unique()
            active_lifetime = lifetime_base[lifetime_base["Customer_Key"].isin(active_keys)]
            
            n_repeat = len(active_lifetime[active_lifetime["Lifetime_Repeat_Status"] == "Repeat Customer"])
            if tot_customers > 0:
                r_rate = (n_repeat / tot_customers) * 100.0
                result["metrics"]["repeat_rate"]["value"] = float(r_rate)
                if r_rate >= 40.0:
                    result["metrics"]["repeat_rate"]["status"] = "Strong"
                elif r_rate >= 20.0:
                    result["metrics"]["repeat_rate"]["status"] = "Stable"
                elif r_rate >= 10.0:
                    result["metrics"]["repeat_rate"]["status"] = "Watch"
                else:
                    result["metrics"]["repeat_rate"]["status"] = "Risk"

                # One-Time Dependence (strictly Complement, displayed but skipped in Domain aggregation scoring)
                dep = 100.0 - r_rate
                result["metrics"]["onetime_dependence"]["value"] = float(dep)
                if dep < 60.0:
                    result["metrics"]["onetime_dependence"]["status"] = "Strong"
                elif dep < 80.0:
                    result["metrics"]["onetime_dependence"]["status"] = "Stable"
                elif dep < 90.0:
                    result["metrics"]["onetime_dependence"]["status"] = "Watch"
                else:
                    result["metrics"]["onetime_dependence"]["status"] = "Risk"
            
            # Customer Concentration (Top-5)
            # Find period-sensitive stats
            cust_perf = get_customer_period_performance(cust_prep, lifetime_base)
            if not cust_perf.empty:
                unique_custs_count = len(cust_perf)
                total_cust_rev = cust_perf["Filtered_Revenue"].sum()
                top_5_cust_rev = cust_perf.head(5)["Filtered_Revenue"].sum()
                
                if total_cust_rev > 0:
                    cust_con = (top_5_cust_rev / total_cust_rev) * 100.0
                    result["metrics"]["top5_customer_concentration"]["value"] = float(cust_con)
                    result["metrics"]["top5_customer_concentration"]["entity_count"] = unique_custs_count
                    
                    if unique_custs_count < 5:
                        result["metrics"]["top5_customer_concentration"]["context"] = "Small Customer Cohort"
                        result["metrics"]["top5_customer_concentration"]["status"] = "Insufficient Data"
                    else:
                        result["metrics"]["top5_customer_concentration"]["context"] = "Normal"
                        if cust_con < 20.0:
                            result["metrics"]["top5_customer_concentration"]["status"] = "Strong"
                        elif cust_con < 50.0:
                            result["metrics"]["top5_customer_concentration"]["status"] = "Stable"
                        elif cust_con < 70.0:
                            result["metrics"]["top5_customer_concentration"]["status"] = "Watch"
                        else:
                            result["metrics"]["top5_customer_concentration"]["status"] = "Risk"

    # ------------------ PRODUCT HEALTH DOMAIN ------------------
    if has_product:
        prod_prep, prod_meta = prepare_product_dataset(df)
        if not prod_prep.empty:
            prod_perf = get_product_performance(prod_prep)
            if not prod_perf.empty:
                product_count = len(prod_perf)
                total_prod_rev = prod_perf["Revenue"].sum()
                
                # Top-5 Product Concentration
                top5_prod_rev = prod_perf.head(5)["Revenue"].sum()
                if total_prod_rev > 0:
                    p5_con = (top5_prod_rev / total_prod_rev) * 100.0
                    result["metrics"]["top5_product_concentration"]["value"] = float(p5_con)
                    result["metrics"]["top5_product_concentration"]["entity_count"] = product_count
                    
                    if product_count < 5:
                        result["metrics"]["top5_product_concentration"]["context"] = "Small Product Portfolio"
                        result["metrics"]["top5_product_concentration"]["status"] = "Insufficient Data"
                    else:
                        result["metrics"]["top5_product_concentration"]["context"] = "Normal"
                        if p5_con < 40.0:
                            result["metrics"]["top5_product_concentration"]["status"] = "Strong"
                        elif p5_con < 60.0:
                            result["metrics"]["top5_product_concentration"]["status"] = "Stable"
                        elif p5_con < 80.0:
                            result["metrics"]["top5_product_concentration"]["status"] = "Watch"
                        else:
                            result["metrics"]["top5_product_concentration"]["status"] = "Risk"

                # Top-1 Product Concentration
                top1_prod_rev = prod_perf.iloc[0]["Revenue"] if len(prod_perf) > 0 else 0.0
                if total_prod_rev > 0:
                    p1_con = (top1_prod_rev / total_prod_rev) * 100.0
                    result["metrics"]["top1_product_concentration"]["value"] = float(p1_con)
                    if p1_con < 15.0:
                        result["metrics"]["top1_product_concentration"]["status"] = "Strong"
                    elif p1_con < 30.0:
                        result["metrics"]["top1_product_concentration"]["status"] = "Stable"
                    elif p1_con < 50.0:
                        result["metrics"]["top1_product_concentration"]["status"] = "Watch"
                    else:
                        result["metrics"]["top1_product_concentration"]["status"] = "Risk"

                # Product Pareto Share
                pareto_df, pareto_meta = get_pareto_data(prod_prep)
                contributors = pareto_meta.get("contributors_count", 0)
                if product_count > 0:
                    p_ratio = (contributors / product_count) * 100.0
                    result["metrics"]["pareto_share"]["value"] = float(p_ratio)
                    if p_ratio >= 30.0:
                        result["metrics"]["pareto_share"]["status"] = "Strong"
                    elif p_ratio >= 20.0:
                        result["metrics"]["pareto_share"]["status"] = "Stable"
                    elif p_ratio >= 10.0:
                        result["metrics"]["pareto_share"]["status"] = "Watch"
                    else:
                        result["metrics"]["pareto_share"]["status"] = "Risk"

                # Low Revenue Contribution Product Share
                low_contribs = (prod_perf["Revenue"] < (total_prod_rev * 0.005)).sum()
                if product_count > 0:
                    low_share = (low_contribs / product_count) * 100.0
                    result["metrics"]["low_performing_share"]["value"] = float(low_share)
                    if low_share < 20.0:
                        result["metrics"]["low_performing_share"]["status"] = "Strong"
                    elif low_share < 50.0:
                        result["metrics"]["low_performing_share"]["status"] = "Stable"
                    elif low_share < 75.0:
                        result["metrics"]["low_performing_share"]["status"] = "Watch"
                    else:
                        result["metrics"]["low_performing_share"]["status"] = "Risk"

    # ------------------ ORDER ECONOMICS DOMAIN ------------------
    if split["is_valid"] and len(prev_df) > 0 and len(recent_df) > 0:
        # AOV Growth
        prev_rev = prev_df["_Revenue"].sum()
        recent_rev = recent_df["_Revenue"].sum()
        prev_orders = prev_df["OrderID"].nunique()
        recent_orders = recent_df["OrderID"].nunique()
        
        prev_aov = (prev_rev / prev_orders) if prev_orders > 0 else 0.0
        recent_aov = (recent_rev / recent_orders) if recent_orders > 0 else 0.0

        if prev_aov > 0 and split["span_days"] >= 14:
            aov_g = ((recent_aov - prev_aov) / prev_aov) * 100.0
            result["metrics"]["aov_growth"]["value"] = float(aov_g)
            if aov_g >= 5.0:
                result["metrics"]["aov_growth"]["status"] = "Strong"
            elif aov_g >= -2.0:
                result["metrics"]["aov_growth"]["status"] = "Stable"
            elif aov_g >= -10.0:
                result["metrics"]["aov_growth"]["status"] = "Watch"
            else:
                result["metrics"]["aov_growth"]["status"] = "Risk"

        # UPO Growth
        prev_units = prev_df["Quantity"].sum()
        recent_units = recent_df["Quantity"].sum()
        
        prev_upo = (prev_units / prev_orders) if prev_orders > 0 else 0.0
        recent_upo = (recent_units / recent_orders) if recent_orders > 0 else 0.0

        if prev_upo > 0 and split["span_days"] >= 14:
            upo_g = ((recent_upo - prev_upo) / prev_upo) * 100.0
            result["metrics"]["upo_growth"]["value"] = float(upo_g)
            if upo_g >= 5.0:
                result["metrics"]["upo_growth"]["status"] = "Strong"
            elif upo_g >= -2.0:
                result["metrics"]["upo_growth"]["status"] = "Stable"
            elif upo_g >= -10.0:
                result["metrics"]["upo_growth"]["status"] = "Watch"
            else:
                result["metrics"]["upo_growth"]["status"] = "Risk"

        # RPC Growth (Customers)
        if has_customer:
            prev_custs = prev_df["CustomerID"].nunique() if "CustomerID" in prev_df.columns else prev_df["CustomerName"].nunique() if "CustomerName" in prev_df.columns else 0
            recent_custs = recent_df["CustomerID"].nunique() if "CustomerID" in recent_df.columns else recent_df["CustomerName"].nunique() if "CustomerName" in recent_df.columns else 0
            
            prev_rpc = (prev_rev / prev_custs) if prev_custs > 0 else 0.0
            recent_rpc = (recent_rev / recent_custs) if recent_custs > 0 else 0.0

            if prev_rpc > 0 and split["span_days"] >= 14:
                rpc_g = ((recent_rpc - prev_rpc) / prev_rpc) * 100.0
                result["metrics"]["rpc_growth"]["value"] = float(rpc_g)
                if rpc_g >= 5.0:
                    result["metrics"]["rpc_growth"]["status"] = "Strong"
                elif rpc_g >= -2.0:
                    result["metrics"]["rpc_growth"]["status"] = "Stable"
                elif rpc_g >= -10.0:
                    result["metrics"]["rpc_growth"]["status"] = "Watch"
                else:
                    result["metrics"]["rpc_growth"]["status"] = "Risk"

    # ------------------ FORECAST READINESS DOMAIN ------------------
    # Reuse Forecast Engine directly (always run check daily context)
    f_caps = detect_forecast_capabilities(prep_df, "Daily")
    f_state = f_caps.get("capability_state", "UNAVAILABLE")
    
    result["metrics"]["forecast_readiness"] = {
        "value": f_state,
        "status": "Strong" if f_state == "SUITABLE" else "Watch" if f_state == "LIMITED" else "Risk",
        "reasons": f_caps.get("capability_reasons", [])
    }
    
    # 4. Integrate Domain Level Statuses (Stateless helper function)
    result["domain_statuses"] = compute_domain_statuses(result["metrics"])
    
    # Calculate overall_status and indicator_counts from the four business performance domains only
    biz_domains = ["revenue_health", "customer_health", "product_health", "order_economics"]
    domain_vals = [result["domain_statuses"][d] for d in biz_domains]
    
    counts = {
        "Strong": sum(1 for v in domain_vals if v == "Strong"),
        "Stable": sum(1 for v in domain_vals if v == "Stable"),
        "Watch": sum(1 for v in domain_vals if v == "Watch"),
        "Risk": sum(1 for v in domain_vals if v == "Risk"),
        "Insufficient Data": sum(1 for v in domain_vals if v == "Insufficient Data")
    }
    
    result["indicator_counts"] = counts
    
    if counts["Insufficient Data"] == len(biz_domains):
        overall = "Insufficient Data"
    elif counts["Risk"] >= 1:
        overall = "Risk"
    elif counts["Watch"] >= 1:
        overall = "Watch"
    elif counts["Strong"] >= 1:
        overall = "Strong"
    else:
        overall = "Stable"
        
    result["overall_status"] = overall
    
    # 5. Populate Executive Diagnostic Finding Details
    result["executive_findings"] = generate_executive_findings(result["metrics"], split)

    return result


def compute_domain_statuses(metrics: Dict[str, Any]) -> Dict[str, str]:
    """
    Stateless calculator yielding domain-level diagnoses based on primary vs supporting metrics.
    Correlated/complementary customer metric (onetime_dependence) is completely skipped.
    """
    domains = {
        "revenue_health": {
            "primary": "revenue_growth",
            "metrics": ["revenue_growth", "revenue_volatility"]
        },
        "customer_health": {
            "primary": "repeat_rate",
            "metrics": ["repeat_rate", "top5_customer_concentration"]
        },
        "product_health": {
            "primary": "top5_product_concentration",
            "metrics": ["top5_product_concentration", "top1_product_concentration", "pareto_share", "low_performing_share"]
        },
        "order_economics": {
            "primary": "aov_growth",
            "metrics": ["aov_growth", "upo_growth", "rpc_growth"]
        }
    }

    out = {}
    for d_name, d_cfg in domains.items():
        primary_key = d_cfg["primary"]
        metric_keys = d_cfg["metrics"]
        
        # Get statuses of present metrics in this domain
        statuses = {k: metrics[k]["status"] for k in metric_keys if k in metrics}
        
        # Filter to only calculable statuses
        calculable_statuses = {k: s for k, s in statuses.items() if s != "Insufficient Data"}
        
        if not calculable_statuses:
            out[d_name] = "Insufficient Data"
            continue
            
        risk_count = sum(1 for s in calculable_statuses.values() if s == "Risk")
        watch_count = sum(1 for s in calculable_statuses.values() if s == "Watch")
        strong_count = sum(1 for s in calculable_statuses.values() if s == "Strong")
        
        primary_status = calculable_statuses.get(primary_key)
        
        # Rule: Risk if primary is Risk OR any calculable is Risk
        if primary_status == "Risk" or risk_count >= 1:
            out[d_name] = "Risk"
        # Rule: Watch if primary is Watch OR any calculable is Watch
        elif primary_status == "Watch" or watch_count >= 1:
            out[d_name] = "Watch"
        # Rule: Strong only if all calculable ones are Strong or Stable, and >=1 is Strong
        elif all(s in ["Strong", "Stable"] for s in calculable_statuses.values()) and strong_count >= 1:
            out[d_name] = "Strong"
        else:
            out[d_name] = "Stable"
            
    # Add forecast readiness state directly
    f_status_dict = metrics.get("forecast_readiness")
    f_status = f_status_dict.get("status", "Risk") if f_status_dict else "Risk"
    out["forecast_readiness"] = f_status
    
    return out


def generate_executive_findings(metrics: Dict[str, Any], split: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Constructs deterministic sentence-styled findings for each status band.
    """
    strengths = []
    risks = []
    watches = []
    limitations = []

    def classify_finding(status: str, msg: str):
        if status == "Strong":
            strengths.append(msg)
        elif status == "Risk":
            risks.append(msg)
        elif status == "Watch":
            watches.append(msg)
        elif status == "Insufficient Data":
            limitations.append(msg)

    # 1. Revenue growth finding
    rev_growth = metrics["revenue_growth"]
    status_rg = rev_growth["status"]
    val_rg = rev_growth["value"]
    
    if status_rg == "Insufficient Data":
        if split["span_days"] < 14:
            msg = f"Revenue growth could not be evaluated because the active timeline spans only {split['span_days']} day(s); at least 14 days are required."
        else:
            msg = "Revenue growth could not be evaluated due to insufficient data in the baseline window (zero sales)."
        limitations.append(msg)
    else:
        r_start = split["recent_start"].strftime("%Y-%m-%d") if split["recent_start"] else ""
        r_end = split["recent_end"].strftime("%Y-%m-%d") if split["recent_end"] else ""
        p_start = split["prev_start"].strftime("%Y-%m-%d") if split["prev_start"] else ""
        p_end = split["prev_end"].strftime("%Y-%m-%d") if split["prev_end"] else ""
        
        if val_rg >= 0:
            msg = f"Revenue increased {val_rg:.1f}% in the recent comparison window ({r_start} to {r_end}) versus the previous equal-length period ({p_start} to {p_end})."
        else:
            msg = f"Revenue decreased by {abs(val_rg):.1f}% in the recent comparison window ({r_start} to {r_end}) versus the previous period ({p_start} to {p_end})."
        classify_finding(status_rg, msg)

    # 2. Volatility finding
    rev_vol = metrics["revenue_volatility"]
    status_rv = rev_vol["status"]
    val_rv = rev_vol["value"]
    
    if status_rv == "Insufficient Data":
        limitations.append("Sales volatility could not be calculated; at least 10 calendar days are required.")
    else:
        desc = "exceptionally stable" if val_rv < 0.50 else "highly predictable" if val_rv < 1.20 else "erratic" if val_rv < 2.00 else "extremely erratic"
        msg = f"Revenue volatility was {val_rv:.2f} (CV) over the {split['span_days']} days analyzed, indicating {desc} transaction frequency."
        classify_finding(status_rv, msg)

    # 3. Customer Repeat Rate finding
    rep_rate = metrics["repeat_rate"]
    status_rr = rep_rate["status"]
    val_rr = rep_rate["value"]
    
    if status_rr == "Insufficient Data":
        limitations.append("Repeat customer retention could not be assessed because customer identity columns are missing.")
    else:
        if val_rr >= 20.0:
            msg = f"Active customer repeat buyer rate is stable at {val_rr:.1f}%, reflecting balanced transaction retention."
        else:
            msg = f"Low repeat buyer retention rate of {val_rr:.1f}% indicates high reliance on one-time customer acquisitions."
        classify_finding(status_rr, msg)

    # 4. Product concentration finding
    top5_prod = metrics["top5_product_concentration"]
    status_t5p = top5_prod["status"]
    val_t5p = top5_prod["value"]
    cnt_t5p = top5_prod["entity_count"]
    
    if status_t5p == "Insufficient Data":
        if top5_prod["context"] == "Small Product Portfolio":
            limitations.append(f"Product concentration check evaluated as small portfolio context ({cnt_t5p} products total; at least 5 products are required for normal evaluation).")
        else:
            limitations.append("Product concentration cannot be evaluated because product data columns are missing.")
    else:
        if val_t5p < 50.0:
            msg = f"Product portfolio is well-diversified; the top 5 items account for {val_t5p:.1f}% of total units/revenue."
        else:
            msg = f"High product concentration detected; the top 5 items account for {val_t5p:.1f}% of total revenue."
        classify_finding(status_t5p, msg)

    # 5. Forecast readiness finding
    fc_cap = metrics["forecast_readiness"]
    status_fc = fc_cap["status"]
    reasons_fc = fc_cap["reasons"]
    
    if status_fc == "Strong":
        strengths.append("Data timeline satisfies all chronological parameters and coverage conditions for forecasting.")
    else:
        reason_str = ", ".join(reasons_fc)
        limitations.append(f"Forecasting is currently limited or unavailable: {reason_str}.")

    return {
        "strengths": strengths,
        "risks": risks,
        "watches": watches,
        "limitations": limitations
    }
