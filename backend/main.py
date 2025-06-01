import os
import uuid
from typing import Optional, Literal, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import joblib
from pymongo import MongoClient
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import io
import datetime

# --- Load Environment Variables ---
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "vitafit") # Default to 'vitafit' if not set

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Fitness and Diet Prediction API",
    description="API for predicting exercise and diet plans based on user data.",
    version="1.0.0"
)

# --- CORS Middleware ---
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Or restrict to your frontend URL like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Variables for Models and MongoDB Client ---
mongo_client: Optional[MongoClient] = None
db = None

# Exercise Model Globals
multi_clf: Any = None # Exercise Classifier
multi_reg: Any = None # Exercise Regressor
label_encoders: Optional[Dict[str, Any]] = None # Encoders for Exercise Model outputs (and gender)

# Diet Model Globals
diet_regressor: Any = None # Diet Model
diet_label_encoders: Optional[Dict[str, Any]] = None # Encoders specifically for Diet Model's categorical inputs

# Define the exact order of features for each model
EXERCISE_FEATURE_COLUMNS_ORDER = ["age", "gender", "height", "weight", "bmi", "calories_intake"]

# Diet model inputs: initial user data + exercise predictions + derived activity_level
# Note: "frequency_per_week" is now numerical for diet model, not encoded.
DIET_FEATURE_COLUMNS_ORDER = [
    "age", "gender", "height", "weight", "bmi", "calories_intake",
    "exercise_type", "intensity_level", "frequency_per_week", "activity_level"
]

# --- Helper to convert NumPy types to native Python types ---
def convert_numpy_types(obj):
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


# --- Startup Events ---

@app.on_event("startup")
async def startup_all():
    """
    Handles all necessary startup procedures:
    1. Connect to MongoDB.
    2. Load Machine Learning Models and Encoders.
    """
    global mongo_client, db
    global multi_clf, multi_reg, diet_regressor, label_encoders, diet_label_encoders

    # --- 1. MongoDB Client Initialization ---
    try:
        mongo_client = MongoClient(MONGODB_URI)
        db = mongo_client[DB_NAME]
        mongo_client.admin.command('ismaster')
        print(f"Connected to MongoDB database: {DB_NAME}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise HTTPException(status_code=500, detail=f"Server startup error: Failed to connect to MongoDB. {e}")

    # --- 2. Load Models and Encoders ---
    exercise_models_path = "Exercise_Models"
    try:
        multi_clf = joblib.load(os.path.join(exercise_models_path, "multi_classifier.pkl"))
        multi_reg = joblib.load(os.path.join(exercise_models_path, "multi_regressor.pkl"))
        loaded_encoders = joblib.load(os.path.join(exercise_models_path, "label_encoders.pkl"))
        if not isinstance(loaded_encoders, dict) or 'gender' not in loaded_encoders:
            raise ValueError("label_encoders.pkl is not a dictionary or is missing 'gender' encoder.")
        label_encoders = loaded_encoders # Assign to global only if valid
        print("Exercise prediction models and encoders loaded successfully!")

    except FileNotFoundError as e:
        print(f"Error loading exercise models: {e}. Make sure .pkl files are in {exercise_models_path}")
        raise HTTPException(status_code=500, detail=f"Server setup error: Missing exercise model files. {e}")
    except Exception as e:
        print(f"An unexpected error occurred loading exercise models: {e}")
        raise HTTPException(status_code=500, detail=f"Server setup error: Failed to load exercise models. {e}")

    # Load Diet Model and its encoders
    diet_models_path = "Diet_Recommendation_Models"
    try:
        diet_regressor = joblib.load(os.path.join(diet_models_path, "diet_model_rf.pkl"))
        loaded_diet_encoders = joblib.load(os.path.join(diet_models_path, "diet_label_encoders.pkl"))
        if not isinstance(loaded_diet_encoders, dict) or 'gender' not in loaded_diet_encoders:
             print("Warning: diet_label_encoders.pkl is not a dictionary or is missing 'gender' encoder for diet model. It might still work if gender is handled differently in diet model.")
        diet_label_encoders = loaded_diet_encoders
        print("Diet prediction model and encoders loaded successfully!")
    except FileNotFoundError as e:
        print(f"Error loading diet model: {e}. Make sure diet_model_rf.pkl and diet_label_encoders.pkl are in {diet_models_path}")
        diet_regressor = None
        diet_label_encoders = None
        print("Warning: Diet prediction model will not be available due to missing files.")
    except Exception as e:
        print(f"An unexpected error occurred loading diet model: {e}")
        diet_regressor = None
        diet_label_encoders = None
        print(f"Warning: Diet prediction model will not be available due to error: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Closes the MongoDB connection on application shutdown."""
    if mongo_client:
        mongo_client.close()
        print("MongoDB connection closed.")

# --- Pydantic Models for Request Body Validation ---
class UserInput(BaseModel):
    session_id: str = Field(..., description="Unique session ID from frontend to track user's predictions.")
    age: int = Field(..., gt=0, lt=120, description="User's age in years.")
    gender: Literal["male", "female"] = Field(..., description="User's gender.")
    height_value: float = Field(..., gt=0, description="User's height value.")
    height_unit: Literal["cm", "inches", "feet"] = Field(..., description="Unit of height.")
    weight_value: float = Field(..., gt=0, description="User's weight value.")
    weight_unit: Literal["kg", "lbs"] = Field(..., description="Unit of weight.")
    calories_intake: int = Field(..., gt=0, description="User's daily calorie intake.")


class UserPersonalDetails(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ReportRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to retrieve stored predictions.")
    user_details: Optional[UserPersonalDetails] = None

class DietPlanRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to retrieve previous exercise predictions and user data.")
    # Medical conditions, dietary restrictions, food preferences are no longer direct model inputs
    # and are not required to be sent with this request for model prediction.
    # If collected for record-keeping only, they would be handled elsewhere (e.g., initial user input).
    # Since they are not used by the models, they are removed from here to simplify API.
    # They can still be stored in the database if the initial UserInput is updated to include them.
    # For now, we assume they are not collected if not used by models.


# --- Helper Functions ---

def infer_activity_level(freq: int, intensity: str) -> str:
    """
    Infres activity level based on exercise frequency and intensity.
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

def preprocess_user_data_for_exercise(data: UserInput, encoders: dict) -> tuple[pd.DataFrame, dict]:
    """
    Preprocesses raw user input into a DataFrame suitable for the exercise models.
    Handles unit conversions, BMI calculation, and categorical encoding for gender.
    Returns the DataFrame and a dictionary of processed core features for later use.
    """
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

    if encoders is None or 'gender' not in encoders:
        raise HTTPException(status_code=500, detail="Gender LabelEncoder not loaded or missing from 'label_encoders'.")
    
    gender_le = encoders.get('gender')
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

# --- API Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Fitness and Diet Prediction API!"}

@app.post("/predict_exercise") # Renamed endpoint
async def predict_exercise_plan(user_input: UserInput):
    # Ensure exercise models are loaded
    if not all([multi_clf, multi_reg, label_encoders]):
        raise HTTPException(status_code=500, detail="Exercise models or encoders are not loaded. Server might be misconfigured.")

    # --- 1. Preprocess User Input for Exercise Model ---
    df_for_exercise, processed_core_features = preprocess_user_data_for_exercise(user_input, label_encoders) # type: ignore

    # --- 2. Exercise Predictions ---
    exercise_predictions = {}
    try:
        y_class_pred_encoded = multi_clf.predict(df_for_exercise) # type: ignore
        y_reg_pred = multi_reg.predict(df_for_exercise) # type: ignore

        predicted_exercise_type = label_encoders['exercise_type'].inverse_transform([y_class_pred_encoded[0, 0]])[0] # type: ignore
        predicted_intensity_level = label_encoders['intensity_level'].inverse_transform([y_class_pred_encoded[0, 1]])[0] # type: ignore
        
        # frequency_per_week comes from the regression model (multi_reg)
        predicted_frequency_per_week_val = round(y_reg_pred[0, 0]) # First output of multi_reg is frequency_per_week
        predicted_duration_minutes = round(y_reg_pred[0, 1], 2) # Second output is duration_minutes
        predicted_estimated_calorie_burn = round(y_reg_pred[0, 2], 2) # Third output is estimated_calorie_burn

        exercise_predictions = {
            "exercise_type": predicted_exercise_type,
            "intensity_level": predicted_intensity_level,
            "frequency_per_week": int(predicted_frequency_per_week_val), # Ensure it's an integer
            "duration_minutes": predicted_duration_minutes,
            "estimated_calorie_burn": predicted_estimated_calorie_burn
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during exercise prediction: {str(e)}")

    # --- 3. Store Predictions in MongoDB ---
    if db is not None:
        try:
            prediction_record = {
                "session_id": user_input.session_id,
                "timestamp": datetime.datetime.utcnow(),
                "raw_user_input": convert_numpy_types(user_input.dict()), # Convert NumPy types
                "processed_features": convert_numpy_types(processed_core_features), # Convert NumPy types
                "exercise_predictions": convert_numpy_types(exercise_predictions), # Convert NumPy types
                "diet_predictions": {} # Initialize empty, will be filled by /predict_diet
            }
            db.predictions.update_one(
                {"session_id": user_input.session_id},
                {"$set": prediction_record},
                upsert=True
            )
            print(f"Exercise predictions for session {user_input.session_id} stored/updated in MongoDB.")
        except Exception as e:
            print(f"Error storing exercise predictions in MongoDB: {e}")
            print(f"Invalid document: {prediction_record}") # Print the problematic document
    else:
        print("MongoDB client not initialized. Exercise predictions not stored.")

    # --- 4. Return Exercise Predictions ---
    return {
        "session_id": user_input.session_id,
        "exercise_plan": convert_numpy_types(exercise_predictions), # Ensure return type is native
        "message": "Exercise plan generated. You can now generate a diet plan with more details if desired."
    }

@app.post("/predict_diet")
async def predict_diet_plan(diet_request: DietPlanRequest):
    if not all([diet_regressor, diet_label_encoders]):
        raise HTTPException(status_code=500, detail="Diet prediction models or encoders are not loaded. Server might be misconfigured.")
    
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB client not initialized. Cannot generate diet plan.")

    # Retrieve existing predictions for the session
    prediction_record = db.predictions.find_one({"session_id": diet_request.session_id})

    if not prediction_record:
        raise HTTPException(status_code=404, detail=f"No exercise predictions found for session ID: {diet_request.session_id}. Please submit initial user data first.")

    # Extract stored data (which should now be native Python types)
    processed_core_features = prediction_record.get('processed_features', {})
    exercise_predictions = prediction_record.get('exercise_predictions', {})
    raw_user_input = prediction_record.get('raw_user_input', {})

    if not processed_core_features or not exercise_predictions:
        raise HTTPException(status_code=500, detail="Incomplete stored data for session. Cannot generate diet plan.")

    diet_predictions = {}
    try:
        # Ensure frequency_per_week is an integer for activity level inference
        freq_for_activity = int(exercise_predictions.get("frequency_per_week", 0)) # Should be an integer now
        
        activity_level = infer_activity_level(
            freq_for_activity,
            exercise_predictions["intensity_level"]
        )
        
        # Use the stored (already decoded/native) gender for diet model input
        # Note: processed_core_features["gender"] should already be an int from previous conversion,
        # but if the diet model expects the *string* 'male'/'female' for encoding, we need raw_user_input.
        # Let's assume diet_label_encoders['gender'] encodes 'male'/'female' strings to numbers.
        diet_gender_raw = raw_user_input['gender'].lower() # Use raw string for encoding

        # Re-encode gender specifically for diet model if diet_label_encoders['gender'] exists
        if diet_label_encoders is not None and 'gender' in diet_label_encoders and diet_label_encoders['gender'] is not None:
            try:
                diet_encoded_gender = diet_label_encoders['gender'].transform([diet_gender_raw])[0]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid gender for diet model: '{diet_gender_raw}'. Must be one of: {list(diet_label_encoders['gender'].classes_)}")
        else:
            # Fallback if diet gender encoder is missing (e.g., use the already processed gender, or raise error)
            # This implies diet model expects numerical gender without needing re-encoding if its encoder is missing
            print("WARNING: Diet model's 'gender' LabelEncoder is missing. Using pre-processed gender from exercise step.")
            diet_encoded_gender = processed_core_features["gender"] # This was already an int (0 or 1)

        if (
            diet_label_encoders is None or
            'exercise_type' not in diet_label_encoders or diet_label_encoders['exercise_type'] is None or
            'intensity_level' not in diet_label_encoders or diet_label_encoders['intensity_level'] is None or
            'activity_level' not in diet_label_encoders or diet_label_encoders['activity_level'] is None
        ):
            raise HTTPException(status_code=500, detail="Diet label encoders for exercise_type, intensity_level, or activity_level are missing or not loaded.")
        encoded_exercise_type = diet_label_encoders['exercise_type'].transform([exercise_predictions["exercise_type"]])[0]
        encoded_intensity_level = diet_label_encoders['intensity_level'].transform([exercise_predictions["intensity_level"]])[0]
        encoded_activity_level = diet_label_encoders['activity_level'].transform([activity_level])[0]

        diet_model_input_data = {
            "age": processed_core_features["age"],
            "gender": diet_encoded_gender, # This should be the encoded integer
            "height": processed_core_features["height"],
            "weight": processed_core_features["weight"],
            "bmi": processed_core_features["bmi"],
            "calories_intake": processed_core_features["calories_intake"],
            "exercise_type": encoded_exercise_type,
            "intensity_level": encoded_intensity_level,
            "frequency_per_week": freq_for_activity, # This is the integer frequency
            "activity_level": encoded_activity_level
        }
        
        df_for_diet_model = pd.DataFrame([diet_model_input_data])[DIET_FEATURE_COLUMNS_ORDER]

        y_diet_pred = diet_regressor.predict(df_for_diet_model)
        diet_predictions = {
            "recommended_calories": round(y_diet_pred[0, 0], 2),
            "protein_grams_per_day": round(y_diet_pred[0, 1], 2),
            "carbs_grams_per_day": round(y_diet_pred[0, 2], 2),
            "fats_grams_per_day": round(y_diet_pred[0, 3], 2)
        }
    except Exception as e:
        print(f"Warning: Error during diet prediction: {str(e)}")
        # If diet model isn't fully available/functional, send a specific message to frontend
        if not diet_regressor or not diet_label_encoders:
            diet_predictions = {"error": "Diet model not fully loaded or available."}
        else:
            raise HTTPException(status_code=500, detail=f"Could not generate diet plan due to internal error: {str(e)}")

    # Update the stored record with diet predictions and any new optional user inputs
    if db is not None:
        try:
            # Update the diet_predictions field. Note: medical_conditions etc. are not expected from diet_request
            db.predictions.update_one(
                {"session_id": diet_request.session_id},
                {"$set": {
                    "diet_predictions": convert_numpy_types(diet_predictions), # Convert NumPy types
                    "last_updated": datetime.datetime.utcnow() # Add a timestamp for update
                }}
            )
            print(f"Diet predictions for session {diet_request.session_id} updated in MongoDB.")
        except Exception as e:
            print(f"Error updating diet predictions in MongoDB: {e}")
            print(f"Invalid diet document for update: {convert_numpy_types(diet_predictions)}") # Print problematic part
    else:
        print("MongoDB client not initialized. Diet predictions not stored.")

    return {
        "session_id": diet_request.session_id,
        "diet_plan": convert_numpy_types(diet_predictions), # Ensure return type is native
        "message": "Diet plan generated successfully!"
    }


@app.post("/generate_report", response_class=StreamingResponse)
async def generate_report(report_request: ReportRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="MongoDB client not initialized. Cannot generate report.")

    prediction_record = db.predictions.find_one({"session_id": report_request.session_id})

    if not prediction_record:
        raise HTTPException(status_code=404, detail=f"No predictions found for session ID: {report_request.session_id}")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Fitness and Diet Plan Report", styles['h1']))
    elements.append(Spacer(1, 0.2 * inch))

    if report_request.user_details and any(report_request.user_details.dict().values()):
        elements.append(Paragraph("User Details:", styles['h2']))
        user_data = []
        if report_request.user_details.first_name: user_data.append(["First Name:", report_request.user_details.first_name])
        if report_request.user_details.last_name: user_data.append(["Last Name:", report_request.user_details.last_name])
        if report_request.user_details.email: user_data.append(["Email:", report_request.user_details.email])
        if report_request.user_details.phone: user_data.append(["Phone:", report_request.user_details.phone])
        if user_data:
            table_style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ])
            elements.append(Table(user_data, style=table_style))
            elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph("Submitted Data:", styles['h2']))
    raw_input_data_for_report = []
    # Include all raw_user_input for the report.
    # Note: Medical conditions, dietary restrictions, food preferences might be present
    # if previously stored, even if they are no longer part of the UserInput model for new requests.
    raw_user_input_stored = prediction_record.get('raw_user_input', {})
    for key, value in raw_user_input_stored.items():
        if value is not None and value != '' and key not in ['medical_conditions', 'dietary_restrictions', 'food_preferences']:
            raw_input_data_for_report.append([key.replace('_', ' ').title() + ":", str(value)])
    
    # Add optional fields only if they exist in the stored record
    if raw_user_input_stored.get('medical_conditions'):
        raw_input_data_for_report.append(["Medical Conditions:", raw_user_input_stored['medical_conditions']])
    if raw_user_input_stored.get('dietary_restrictions'):
        raw_input_data_for_report.append(["Dietary Restrictions:", raw_user_input_stored['dietary_restrictions']])
    if raw_user_input_stored.get('food_preferences'):
        raw_input_data_for_report.append(["Food Preferences:", raw_user_input_stored['food_preferences']])

    if raw_input_data_for_report:
        elements.append(Table(raw_input_data_for_report, style=TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,-1), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT')
        ])))
        elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph("Exercise Plan:", styles['h2']))
    exercise_data = []
    for key, value in prediction_record.get('exercise_predictions', {}).items():
        exercise_data.append([key.replace('_', ' ').title() + ":", str(value)])
    if exercise_data:
        elements.append(Table(exercise_data, style=TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,-1), colors.lightgreen),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT')
        ])))
        elements.append(Spacer(1, 0.2 * inch))

    # Only include Diet Plan if it exists and is not empty
    diet_predictions_data = prediction_record.get('diet_predictions', {})
    if diet_predictions_data and not (isinstance(diet_predictions_data, dict) and 'error' in diet_predictions_data):
        elements.append(Paragraph("Diet Plan:", styles['h2']))
        diet_data = []
        for key, value in diet_predictions_data.items():
            if key != "message": # Don't display message key in the table
                diet_data.append([key.replace('_', ' ').title() + ":", str(value)])
        if diet_data:
            elements.append(Table(diet_data, style=TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BACKGROUND', (0,0), (-1,-1), colors.lightblue),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT')
            ])))
            elements.append(Spacer(1, 0.2 * inch))
    elif diet_predictions_data and "error" in diet_predictions_data:
        elements.append(Paragraph(f"Diet Plan Error: {diet_predictions_data['error']}", styles['Normal']))
        elements.append(Spacer(1, 0.2 * inch))
    else:
        elements.append(Paragraph("Diet Plan: Not yet generated.", styles['Normal']))
        elements.append(Spacer(1, 0.2 * inch))


    doc.build(elements)
    buffer.seek(0)

    filename = f"Fitness_Report_{report_request.session_id}_{datetime.date.today()}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})