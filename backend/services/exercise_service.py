# backend/services/exercise_service.py
import os
import joblib
import pandas as pd
import nest_asyncio
from typing import Any, Dict, Optional
from fastapi import HTTPException
from config.settings import EXERCISE_MODELS_PATH
from models.request_models import UserInput
from utils.helpers import convert_numpy_types

# Exercise Model Globals
multi_clf: Optional[Any] = None # Exercise Classifier
multi_reg: Optional[Any] = None # Exercise Regressor
label_encoders: Optional[Dict[str, Any]] = None # Encoders for Exercise Model outputs (and gender)

# Define the exact order of features for the exercise model
EXERCISE_FEATURE_COLUMNS_ORDER = ["age", "gender", "height", "weight", "bmi", "calories_intake"]


async def load_exercise_models():
    """Loads the exercise prediction models and their label encoders."""
    global multi_clf, multi_reg, label_encoders

    try:
        multi_clf = joblib.load(os.path.join(EXERCISE_MODELS_PATH, "multi_classifier.pkl"))
        multi_reg = joblib.load(os.path.join(EXERCISE_MODELS_PATH, "multi_regressor.pkl"))
        loaded_encoders = joblib.load(os.path.join(EXERCISE_MODELS_PATH, "label_encoders.pkl"))

        if not isinstance(loaded_encoders, dict) or 'gender' not in loaded_encoders:
            raise ValueError("label_encoders.pkl is not a dictionary or is missing 'gender' encoder.")
        label_encoders = loaded_encoders # Assign to global only if valid
        print("Exercise prediction models and encoders loaded successfully!")

    except FileNotFoundError as e:
        print(f"Error loading exercise models: {e}. Make sure .pkl files are in {EXERCISE_MODELS_PATH}")
        raise HTTPException(status_code=500, detail=f"Server setup error: Missing exercise model files. {e}")
    except Exception as e:
        print(f"An unexpected error occurred loading exercise models: {e}")
        raise HTTPException(status_code=500, detail=f"Server setup error: Failed to load exercise models. {e}")

def preprocess_user_data_for_exercise(data: UserInput) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Preprocesses raw user input into a DataFrame suitable for the exercise models.
    Handles unit conversions, BMI calculation, and categorical encoding for gender.
    Returns the DataFrame and a dictionary of processed core features for later use.
    """
    if label_encoders is None or 'gender' not in label_encoders:
        raise HTTPException(status_code=500, detail="Gender LabelEncoder not loaded or missing from 'label_encoders'.")
    
    height_in_inches = data.height_value
    if data.height_unit.lower() == 'cm':
        height_in_inches = data.height_value * 0.393701
    elif data.height_unit.lower() == 'feet':
        height_in_inches = data.height_value * 12

    weight_in_kg = data.weight_value
    if data.weight_unit.lower() == 'lbs':
        weight_in_kg = data.weight_value * 0.453592

    height_in_meters = height_in_inches * 0.0254
    bmi = weight_in_kg / (height_in_meters ** 2) if height_in_meters > 0 else 0.0

    gender_le = label_encoders.get('gender')
    if not gender_le:
        raise HTTPException(status_code=500, detail="Gender LabelEncoder found None in 'label_encoders'.")
    
    try:
        encoded_gender = gender_le.transform([data.gender.lower()])[0]
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid gender value: '{data.gender}'. Must be one of: {list(gender_le.classes_)}")

    processed_core_features = {
        "age": data.age,
        "gender": encoded_gender,
        "height": height_in_inches,
        "weight": weight_in_kg,
        "bmi": bmi,
        "calories_intake": data.calories_intake
    }

    df_for_exercise_model = pd.DataFrame([processed_core_features])[EXERCISE_FEATURE_COLUMNS_ORDER]

    return df_for_exercise_model, processed_core_features

def get_exercise_models_and_encoders():
    """Returns the loaded exercise models and encoders, or None if not loaded."""
    if not all([multi_clf, multi_reg, label_encoders]):
        return None, None, None
    return multi_clf, multi_reg, label_encoders

def predict_exercise(user_input_data: UserInput) -> Dict[str, Any]:
    """
    Performs exercise predictions based on user input.
    Ensures models and encoders are loaded before prediction.
    """
    clf, reg, encoders = get_exercise_models_and_encoders()
    if not all([clf, reg, encoders]):
        # Try loading models if not loaded
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If running in an async context (e.g., FastAPI), schedule loading
            nest_asyncio.apply()
            loop.run_until_complete(load_exercise_models())
        else:
            loop.run_until_complete(load_exercise_models())
        clf, reg, encoders = get_exercise_models_and_encoders()
        if not all([clf, reg, encoders]):
            raise HTTPException(status_code=500, detail="Exercise models or encoders are not loaded. Server might be misconfigured.")

    if clf is None or reg is None or encoders is None:
        raise HTTPException(status_code=500, detail="Exercise models or encoders are not loaded. Cannot perform prediction.")

    df_for_exercise, processed_core_features = preprocess_user_data_for_exercise(user_input_data)

    try:
        y_class_pred_encoded = clf.predict(df_for_exercise)
        y_reg_pred = reg.predict(df_for_exercise)

        predicted_exercise_type = encoders['exercise_type'].inverse_transform([y_class_pred_encoded[0, 0]])[0]
        predicted_intensity_level = encoders['intensity_level'].inverse_transform([y_class_pred_encoded[0, 1]])[0]
        
        predicted_frequency_per_week_val = round(y_reg_pred[0, 0])
        predicted_duration_minutes = round(y_reg_pred[0, 1], 2)
        predicted_estimated_calorie_burn = round(y_reg_pred[0, 2], 2)

        exercise_predictions = {
            "exercise_type": predicted_exercise_type,
            "intensity_level": predicted_intensity_level,
            "frequency_per_week": int(predicted_frequency_per_week_val),
            "duration_minutes": predicted_duration_minutes,
            "estimated_calorie_burn": predicted_estimated_calorie_burn
        }
        return convert_numpy_types(exercise_predictions)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during exercise prediction: {str(e)}")