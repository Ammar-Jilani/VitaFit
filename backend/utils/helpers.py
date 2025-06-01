# backend/utils/helpers.py
import numpy as np
from typing import Any, Dict, List

def convert_numpy_types(obj: Any) -> Any:
    """
    Recursively converts NumPy types within an object (dict, list, etc.)
    to native Python types for JSON serialization or MongoDB storage.
    """
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
    """
    Infers activity level based on exercise frequency and intensity.
    This logic must match the data generation logic used for training the diet model.
    """
    if freq >= 5 and intensity.lower() == "high":
        return "very active"
    elif freq >= 3 and intensity.lower() in ["medium", "high"]:
        return "moderate"
    elif freq <= 2:
        return "light"
    else:
        return "sedentary"