import os
import joblib

def load_diet_models():
    base_path = os.path.dirname(__file__)
    
    try:
        model = joblib.load(os.path.join(base_path, "diet_model_rf.pkl"))
        encoders = joblib.load(os.path.join(base_path, "diet_label_encoders.pkl"))
        
        return {
            "model": model,
            "diet_label_encoders": encoders
        }
    except Exception as e:
        raise RuntimeError(f"Failed to load diet models: {e}")
