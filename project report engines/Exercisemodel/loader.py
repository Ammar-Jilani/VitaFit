import os
import joblib

def load_exercise_models():
    base_path = os.path.dirname(__file__)
    
    try:
        multi_clf = joblib.load(os.path.join(base_path, "multi_classifier.pkl"))
        multi_reg = joblib.load(os.path.join(base_path, "multi_regressor.pkl"))
        encoders = joblib.load(os.path.join(base_path, "label_encoders.pkl"))
        
        return {
            "multi_clf": multi_clf,
            "multi_reg": multi_reg,
            "label_encoders": encoders
        }
    except Exception as e:
        raise RuntimeError(f"Failed to load exercise models: {e}")
