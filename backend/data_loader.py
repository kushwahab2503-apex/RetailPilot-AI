import pandas as pd
from typing import Dict, Any

def load_csv(file_obj) -> Dict[str, Any]:
    """
    Safely load a CSV file uploaded via Streamlit.
    """
    result = {
        "success": False,
        "dataframe": None,
        "filename": getattr(file_obj, "name", "unknown.csv"),
        "row_count": 0,
        "column_count": 0,
        "file_size": getattr(file_obj, "size", 0),
        "error_message": None
    }
    
    try:
        # Move pointer to start just in case it was read previously
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
            
        df = pd.read_csv(file_obj)
        
        if df.empty:
            result["error_message"] = "The uploaded file is empty."
            return result
            
        result["success"] = True
        result["dataframe"] = df
        result["row_count"] = df.shape[0]
        result["column_count"] = df.shape[1]
        
    except pd.errors.EmptyDataError:
        result["error_message"] = "The uploaded file contains no data."
    except pd.errors.ParserError:
        result["error_message"] = "The file could not be parsed as a valid CSV."
    except UnicodeDecodeError:
        # Try a more forgiving encoding
        try:
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            df = pd.read_csv(file_obj, encoding="latin1")
            if df.empty:
                result["error_message"] = "The uploaded file is empty."
            else:
                result["success"] = True
                result["dataframe"] = df
                result["row_count"] = df.shape[0]
                result["column_count"] = df.shape[1]
        except Exception as e:
            result["error_message"] = f"Encoding error handling failed: {str(e)}"
    except Exception as e:
        result["error_message"] = f"An unexpected error occurred: {str(e)}"
        
    return result
