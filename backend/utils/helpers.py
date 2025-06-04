# backend/utils/helpers.py
import numpy as np
from typing import Any, Dict, List

def convert_numpy_types(obj: Any) -> Any:
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(elem) for elem in obj]
    return obj

def infer_activity_level(freq: int, intensity: str) -> str:
    if freq >= 5 and intensity.lower() == "high":
        return "very active"
    elif freq >= 3 and intensity.lower() in ["medium", "high"]:
        return "moderate"
    elif freq <= 2:
        return "light"
    else:
        return "sedentary"