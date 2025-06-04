# backend/services/diet_service.py
import os
import joblib
import pandas as pd
from typing import Any, Dict, Optional
from fastapi import HTTPException
from config.settings import DIET_MODELS_PATH
from utils.helpers import convert_numpy_types, infer_activity_level


diet_regressor: Optional[Any] = None
diet_label_encoders: Optional[Dict[str, Any]] = None

DIET_FEATURE_COLUMNS_ORDER = [
    "age", "gender", "height", "weight", "bmi", "calories_intake",
    "exercise_type", "intensity_level", "frequency_per_week", "activity_level"
]

async def load_diet_models():
    """Loads the diet prediction model and its label encoders."""
    global diet_regressor, diet_label_encoders

    try:
        diet_regressor = joblib.load(os.path.join(DIET_MODELS_PATH, "diet_model_rf.pkl"))
        loaded_diet_encoders = joblib.load(os.path.join(DIET_MODELS_PATH, "diet_label_encoders.pkl"))
        
        if not isinstance(loaded_diet_encoders, dict):
            print("Warning: diet_label_encoders.pkl is not a dictionary. It might still work if gender is handled differently in diet model.")
        
        diet_label_encoders = loaded_diet_encoders
        print("Diet prediction model and encoders loaded successfully!")
    except FileNotFoundError as e:
        print(f"Error loading diet model: {e}. Make sure diet_model_rf.pkl and diet_label_encoders.pkl are in {DIET_MODELS_PATH}")
        diet_regressor = None
        diet_label_encoders = None
        print("Warning: Diet prediction model will not be available due to missing files.")
        raise HTTPException(status_code=500, detail=f"Server setup error: Missing diet model files. {e}")
    except Exception as e:
        print(f"An unexpected error occurred loading diet model: {e}")
        diet_regressor = None
        diet_label_encoders = None
        print(f"Warning: Diet prediction model will not be available due to error: {e}")
        raise HTTPException(status_code=500, detail=f"Server setup error: Failed to load diet model. {e}")

def get_diet_models_and_encoders():
    """Returns the loaded diet models and encoders, or None if not loaded."""
    if not all([diet_regressor, diet_label_encoders]):
        return None, None
    return diet_regressor, diet_label_encoders

def predict_diet(processed_core_features: Dict[str, Any], exercise_predictions: Dict[str, Any], raw_user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs diet predictions based on processed user data and exercise predictions.
    Assumes models and encoders are already loaded.
    """
    regressor, encoders = get_diet_models_and_encoders()
    if not all([regressor, encoders]):
        raise HTTPException(status_code=500, detail="Diet prediction models or encoders are not loaded. Server might be misconfigured.")

    diet_predictions = {}
    try:
        freq_for_activity = int(exercise_predictions.get("frequency_per_week", 0))
        
        activity_level = infer_activity_level(
            freq_for_activity,
            exercise_predictions["intensity_level"]
        )
        
        diet_gender_raw = raw_user_input['gender'].lower()

        if encoders is not None and 'gender' in encoders and encoders['gender'] is not None:
            try:
                diet_encoded_gender = encoders['gender'].transform([diet_gender_raw])[0]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid gender for diet model: '{diet_gender_raw}'. Must be one of: {list(encoders['gender'].classes_)}")
        else:
            print("WARNING: Diet model's 'gender' LabelEncoder is missing. Using pre-processed gender from exercise step.")
            diet_encoded_gender = processed_core_features["gender"]

        if (
            encoders is None or
            'exercise_type' not in encoders or encoders['exercise_type'] is None or
            'intensity_level' not in encoders or encoders['intensity_level'] is None or
            'activity_level' not in encoders or encoders['activity_level'] is None
        ):
            raise HTTPException(status_code=500, detail="Diet label encoders for exercise_type, intensity_level, or activity_level are missing or not loaded.")
        
        encoded_exercise_type = encoders['exercise_type'].transform([exercise_predictions["exercise_type"]])[0]
        encoded_intensity_level = encoders['intensity_level'].transform([exercise_predictions["intensity_level"]])[0]
        encoded_activity_level = encoders['activity_level'].transform([activity_level])[0]

        diet_model_input_data = {
            "age": processed_core_features["age"],
            "gender": diet_encoded_gender,
            "height": processed_core_features["height"],
            "weight": processed_core_features["weight"],
            "bmi": processed_core_features["bmi"],
            "calories_intake": processed_core_features["calories_intake"],
            "exercise_type": encoded_exercise_type,
            "intensity_level": encoded_intensity_level,
            "frequency_per_week": freq_for_activity,
            "activity_level": encoded_activity_level
        }
        
        df_for_diet_model = pd.DataFrame([diet_model_input_data])[DIET_FEATURE_COLUMNS_ORDER]

        if regressor is None:
            raise HTTPException(status_code=500, detail="Diet prediction model is not loaded.")
        y_diet_pred = regressor.predict(df_for_diet_model)
        diet_predictions = {
            "recommended_calories": round(y_diet_pred[0, 0], 2),
            "protein_grams_per_day": round(y_diet_pred[0, 1], 2),
            "carbs_grams_per_day": round(y_diet_pred[0, 2], 2),
            "fats_grams_per_day": round(y_diet_pred[0, 3], 2)
        }
        return convert_numpy_types(diet_predictions)

    except Exception as e:
        print(f"Warning: Error during diet prediction: {str(e)}")
        if not regressor or not encoders:
            diet_predictions = {"error": "Diet model not fully loaded or available."}
            return diet_predictions
        else:
            raise HTTPException(status_code=500, detail=f"Could not generate diet plan due to internal error: {str(e)}")