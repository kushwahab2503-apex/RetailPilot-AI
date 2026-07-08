import math
import pandas as pd

def format_indian_currency(val: float) -> str:
    """
    Format a numeric value into an Indian-friendly currency format.
    Examples:
        - 950 -> ₹950
        - 12500 -> ₹12.5K (if round multiple of 100, else standard comma)
        - 45200 -> ₹45.2K
        - 840000 -> ₹8.4L
        - 1240000 -> ₹12.4L
        - 12000000 -> ₹1.2Cr
        - 28000000 -> ₹2.8Cr
    Handles negative numbers and NaN/None gracefully.
    """
    if val is None or (isinstance(val, float) and math.isnan(val)) or pd.isna(val):
        return "₹—"
    
    sign = "-" if val < 0 else ""
    abs_val = abs(val)
    
    if abs_val >= 10_000_000:
        cr_val = abs_val / 10_000_000
        formatted = f"{cr_val:.2f}".rstrip('0').rstrip('.')
        # Ensure that if it has trailing decimals but represents a point value, e.g. 1.20 -> 1.2
        # Let's check if the raw number had more granularity, we show it, but usually standard 1 or 2 decimals is fine.
        return f"{sign}₹{formatted}Cr"
    elif abs_val >= 100_000:
        l_val = abs_val / 100_000
        formatted = f"{l_val:.2f}".rstrip('0').rstrip('.')
        return f"{sign}₹{formatted}L"
    elif abs_val >= 1_000:
        # Check if it is a round multiple of 100
        # Tolerating standard small float precision issues
        if abs(abs_val - round(abs_val)) < 1e-9 and int(round(abs_val)) % 100 == 0:
            k_val = abs_val / 1_000
            formatted = f"{k_val:.2f}".rstrip('0').rstrip('.')
            return f"{sign}₹{formatted}K"
        else:
            return f"{sign}₹{int(round(abs_val)):,}"
    else:
        if abs_val == int(abs_val):
            return f"{sign}₹{int(abs_val)}"
        else:
            return f"{sign}₹{abs_val:.2f}"

def format_indian_number(val: float) -> str:
    """
    Format a numeric value into a short count representation.
    Examples:
        - 950 -> 950
        - 12500 -> 12.5K
        - 840000 -> 8.4L
    """
    if val is None or (isinstance(val, float) and math.isnan(val)) or pd.isna(val):
        return "—"
    
    sign = "-" if val < 0 else ""
    abs_val = abs(val)
    
    if abs_val >= 10_000_000:
        cr_val = abs_val / 10_000_000
        formatted = f"{cr_val:.2f}".rstrip('0').rstrip('.')
        return f"{sign}{formatted}Cr"
    elif abs_val >= 100_000:
        l_val = abs_val / 100_000
        formatted = f"{l_val:.2f}".rstrip('0').rstrip('.')
        return f"{sign}{formatted}L"
    elif abs_val >= 1_000:
        if abs(abs_val - round(abs_val)) < 1e-9 and int(round(abs_val)) % 100 == 0:
            k_val = abs_val / 1_000
            formatted = f"{k_val:.2f}".rstrip('0').rstrip('.')
            return f"{sign}{formatted}K"
        else:
            return f"{sign}{int(round(abs_val)):,}"
    else:
        if abs_val == int(abs_val):
            return f"{sign}{int(abs_val)}"
        else:
            return f"{sign}{abs_val:.2f}"
