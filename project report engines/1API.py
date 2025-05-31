import os
import uuid
from typing import Optional, Literal
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
from sklearn.preprocessing import LabelEncoder

# --- Load Environment Variables ---
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "fitness_predictions") # Default to 'fitness_predictions' if not set

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Fitness and Diet Prediction API",
    description="API for predicting exercise and diet plans based on user data.",
    version="1.0.0"
)

# --- MongoDB Client Initialization ---
mongo_client: Optional[MongoClient] = None
db = None

@app.on_event("startup")
async def startup_db_client():
    global mongo_client, db
    try:
        mongo_client = MongoClient(MONGODB_URI)
        db = mongo_client[DB_NAME]
        print(f"Connected to MongoDB database: {DB_NAME}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        # In a real production app, you might want to log this and gracefully handle
        # if DB connection is critical for app function, you might raise an exception here
        # or have a health check endpoint.

@app.on_event("shutdown")
async def shutdown_db_client():
    if mongo_client:
        mongo_client.close()
        print("MongoDB connection closed.")

# --- Global Variables for Models and Encoders ---
multi_clf = None # Exercise Classifier
multi_reg = None # Exercise Regressor
diet_regressor = None # Diet Model
label_encoders = None # Encoders for Exercise Model outputs (and gender for both, assuming commonality)
diet_label_encoders = None # Encoders specifically for Diet Model's categorical inputs (exercise_type, intensity_level, activity_level)

# Define the exact order of features for each model
EXERCISE_FEATURE_COLUMNS_ORDER = ["age", "gender", "height", "weight", "bmi", "calories_intake"]

# Diet model inputs: initial user data + exercise predictions + derived activity_level
# Note: "frequency_per_week" is now numerical for diet model, not encoded.
DIET_FEATURE_COLUMNS_ORDER = [
    "age", "gender", "height", "weight", "bmi", "calories_intake",
    "exercise_type", "intensity_level", "frequency_per_week", "activity_level"
]

# --- Load Models and Encoders on Startup ---
@app.on_event("startup")
async def load_models():
    global multi_clf, multi_reg, diet_regressor, label_encoders, diet_label_encoders

    models_path = "app/models/" # Path inside the Docker container

    # Load Exercise Models and their encoders
    try:
        multi_clf = joblib.load(os.path.join(models_path, "multi_classifier.pkl"))
        multi_reg = joblib.load(os.path.join(models_path, "multi_regressor.pkl"))
        label_encoders = joblib.load(os.path.join(models_path, "label_encoders.pkl"))
        print("Exercise prediction models and encoders loaded successfully!")
    except FileNotFoundError as e:
        print(f"Error loading exercise models: {e}. Make sure .pkl files are in {models_path}")
        raise HTTPException(status_code=500, detail=f"Server setup error: Missing exercise model files. {e}")
    except Exception as e:
        print(f"An unexpected error occurred loading exercise models: {e}")
        raise HTTPException(status_code=500, detail=f"Server setup error: Failed to load exercise models. {e}")

    # --- Load Diet Model ---
    try:
        diet_regressor = joblib.load(os.path.join(models_path, "diet_model_rf.pkl")) # Corrected filename based on your input
        diet_label_encoders = joblib.load(os.path.join(models_path, "diet_label_encoders.pkl")) # New encoder for diet model
        print("Diet prediction model and encoders loaded successfully!")
    except FileNotFoundError as e:
        print(f"Error loading diet model: {e}. Make sure diet_model_rf.pkl and diet_label_encoders.pkl are in {models_path}")
        # If diet prediction is optional, setting to None is fine. Otherwise, raise HTTPException.
        diet_regressor = None
        diet_label_encoders = None
    except Exception as e:
        print(f"An unexpected error occurred loading diet model: {e}")
        diet_regressor = None
        diet_label_encoders = None


# --- Pydantic Models for Request Body Validation ---
class UserInput(BaseModel):
    session_id: str = Field(..., description="Unique session ID from frontend to track user's predictions.")
    age: int = Field(..., gt=0, lt=120, description="User's age in years.")
    gender: Literal["Male", "Female", "Other"] = Field(..., description="User's gender.")
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


# --- Helper Functions (From your provided data generation logic) ---

def infer_activity_level(freq, intensity):
    """
    Infers activity level based on exercise frequency and intensity.
    This logic must match the data generation logic used for training the diet model.
    """
    if freq >= 5 and intensity == "high":
        return "very active"
    elif freq >= 3 and intensity in ["medium", "high"]: # Used "medium" as per your dataset generation snippet
        return "moderate"
    elif freq <= 2:
        return "light"
    else:
        return "sedentary"

def preprocess_user_data_for_exercise(data: UserInput, encoders: dict) -> tuple[pd.DataFrame, dict]:
    """
    Preprocesses raw user input into a DataFrame suitable for the exercise models.
    Returns the DataFrame and a dictionary of processed core features for later use.
    """
    # Unit Conversions
    height_in_inches = data.height_value
    if data.height_unit.lower() == 'cm':
        height_in_inches = data.height_value * 0.393701
    elif data.height_unit.lower() == 'feet':
        height_in_inches = data.height_value * 12

    weight_in_kg = data.weight_value
    if data.weight_unit.lower() == 'lbs':
        weight_in_kg = data.weight_value * 0.453592

    # BMI Calculation (BMI = weight (kg) / (height (m))^2)
    # Need height in meters for BMI calculation, convert inches to meters
    height_in_meters = height_in_inches * 0.0254
    bmi = weight_in_kg / (height_in_meters ** 2) if height_in_meters > 0 else 0.0

    # Gender Encoding (using the encoder from label_encoders for consistency with exercise model)
    gender_le = encoders.get('gender')
    if not gender_le:
        raise HTTPException(status_code=500, detail="Gender LabelEncoder not loaded for exercise model.")
    try:
        encoded_gender = gender_le.transform([data.gender])[0]
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid gender value: '{data.gender}'. Must be one of: {list(gender_le.classes_)}")

    # Prepare core processed data
    processed_core_features = {
        "age": data.age,
        "gender": encoded_gender,
        "height": height_in_inches, # Model expects height in inches
        "weight": weight_in_kg,     # Model expects weight in kg
        "bmi": bmi,
        "calories_intake": data.calories_intake
    }

    # Create DataFrame, ensuring correct column order for exercise model
    df_for_exercise_model = pd.DataFrame([processed_core_features])[EXERCISE_FEATURE_COLUMNS_ORDER]

    return df_for_exercise_model, processed_core_features

# --- API Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Fitness and Diet Prediction API!"}

@app.post("/predict")
async def predict_fitness_plan(user_input: UserInput):
    # Ensure exercise models are loaded
    if not all([multi_clf, multi_reg, label_encoders]):
        raise HTTPException(status_code=500, detail="Exercise models are not loaded. Server might be misconfigured.")

    # --- 1. Preprocess User Input for Exercise Model ---
    df_for_exercise, processed_core_features = preprocess_user_data_for_exercise(user_input, label_encoders)

    # --- 2. Exercise Predictions ---
    exercise_predictions = {}
    try:
        y_class_pred_encoded = multi_clf.predict(df_for_exercise)
        y_reg_pred = multi_reg.predict(df_for_exercise)

        # Decode exercise classification results back to original strings
        predicted_exercise_type = label_encoders['exercise_type'].inverse_transform([y_class_pred_encoded[0, 0]])[0]
        predicted_intensity_level = label_encoders['intensity_level'].inverse_transform([y_class_pred_encoded[0, 1]])[0]
        predicted_frequency_per_week_val = label_encoders['frequency_per_week'].inverse_transform([y_class_pred_encoded[0, 2]])[0]
        
        # Ensure frequency is an integer if it represents counts
        predicted_frequency_per_week_int = int(predicted_frequency_per_week_val)


        exercise_predictions = {
            "exercise_type": predicted_exercise_type,
            "intensity_level": predicted_intensity_level,
            "frequency_per_week": predicted_frequency_per_week_int,
            "duration_minutes": round(y_reg_pred[0, 0], 2),
            "estimated_calorie_burn": round(y_reg_pred[0, 1], 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during exercise prediction: {str(e)}")

    # --- 3. Diet Predictions (if model is loaded) ---
    diet_predictions = {}
    if diet_regressor and diet_label_encoders: # Ensure diet model and its encoders are loaded
        try:
            # Infer activity level based on exercise predictions
            activity_level = infer_activity_level(
                exercise_predictions["frequency_per_week"],
                exercise_predictions["intensity_level"]
            )
            
            # Encode categorical inputs for the diet model using diet_label_encoders
            # IMPORTANT: Ensure your diet_label_encoders.pkl contains encoders for these specific categories.
            # Use 'gender' encoder from diet_label_encoders if its classes differ from exercise_label_encoders for diet model.
            # If `gender` encoder is identical for both models, `processed_core_features["gender"]` is already encoded.
            
            # Re-encode gender specifically for diet model if diet_label_encoders['gender'] exists and is used
            # Otherwise, use processed_core_features["gender"] which is already encoded by label_encoders['gender']
            diet_encoded_gender = processed_core_features["gender"] # Assuming gender encoding is consistent

            # Check if diet_label_encoders has an explicit 'gender' encoder and use it if needed for diet model
            if 'gender' in diet_label_encoders and diet_label_encoders['gender'].classes_.tolist() != label_encoders['gender'].classes_.tolist():
                 # This block would re-encode gender if the diet model's gender encoder has different classes/mapping
                 try:
                     diet_encoded_gender = diet_label_encoders['gender'].transform([user_input.gender])[0]
                 except ValueError:
                     raise HTTPException(status_code=400, detail=f"Invalid gender for diet model: '{user_input.gender}'. Must be one of: {list(diet_label_encoders['gender'].classes_)}")


            encoded_exercise_type = diet_label_encoders['exercise_type'].transform([exercise_predictions["exercise_type"]])[0]
            encoded_intensity_level = diet_label_encoders['intensity_level'].transform([exercise_predictions["intensity_level"]])[0]
            # 'frequency_per_week' is NOT encoded for the diet model; it's used as a direct numerical input.
            encoded_activity_level = diet_label_encoders['activity_level'].transform([activity_level])[0]

            # Combine core processed features with exercise outputs and derived activity_level for diet model input
            diet_model_input_data = {
                "age": processed_core_features["age"],
                "gender": diet_encoded_gender, # Use possibly re-encoded gender
                "height": processed_core_features["height"],
                "weight": processed_core_features["weight"],
                "bmi": processed_core_features["bmi"],
                "calories_intake": processed_core_features["calories_intake"],
                "exercise_type": encoded_exercise_type,
                "intensity_level": encoded_intensity_level,
                "frequency_per_week": exercise_predictions["frequency_per_week"], # DIRECT numerical value, NOT encoded
                "activity_level": encoded_activity_level
            }
            
            # Create DataFrame for diet model, ensuring correct column order
            df_for_diet_model = pd.DataFrame([diet_model_input_data])[DIET_FEATURE_COLUMNS_ORDER]

            # Make diet predictions
            y_diet_pred = diet_regressor.predict(df_for_diet_model)
            diet_predictions = {
                "recommended_calories": round(y_diet_pred[0, 0], 2),
                "protein_grams_per_day": round(y_diet_pred[0, 1], 2),
                "carbs_grams_per_day": round(y_diet_pred[0, 2], 2),
                "fats_grams_per_day": round(y_diet_pred[0, 3], 2)
            }
        except Exception as e:
            print(f"Warning: Error during diet prediction: {str(e)}")
            diet_predictions = {"error": f"Could not generate diet plan due to internal error: {str(e)}"}
    else:
        diet_predictions = {"message": "Diet prediction model not available or not loaded."}


    # --- 4. Store Predictions in MongoDB (for report generation) ---
    if db:
        try:
            prediction_record = {
                "session_id": user_input.session_id,
                "timestamp": datetime.datetime.utcnow(),
                "raw_user_input": user_input.dict(), # Store raw input from frontend
                "processed_features": processed_core_features, # Store core processed features (from exercise preprocessing)
                "exercise_predictions": exercise_predictions,
                "diet_predictions": diet_predictions # Store diet predictions as well
            }
            # Upsert: update if session_id exists, insert otherwise
            db.predictions.update_one(
                {"session_id": user_input.session_id},
                {"$set": prediction_record},
                upsert=True
            )
            print(f"Predictions for session {user_input.session_id} stored/updated in MongoDB.")
        except Exception as e:
            print(f"Error storing predictions in MongoDB: {e}")
            # Do not block the API response if DB storage fails
    else:
        print("MongoDB client not initialized. Predictions not stored.")


    # --- 5. Return Combined Predictions ---
    return {
        "session_id": user_input.session_id,
        "exercise_plan": exercise_predictions,
        "diet_plan": diet_predictions
    }

@app.post("/generate_report", response_class=StreamingResponse)
async def generate_report(report_request: ReportRequest):
    if not db:
        raise HTTPException(status_code=500, detail="MongoDB client not initialized. Cannot generate report.")

    # Retrieve predictions from MongoDB
    # For PyMongo (synchronous), find_one is directly called. For Motor (async), it would be `await db.predictions.find_one`.
    # Given your current setup, assuming synchronous PyMongo for now.
    prediction_record = db.predictions.find_one({"session_id": report_request.session_id})

    if not prediction_record:
        raise HTTPException(status_code=404, detail=f"No predictions found for session ID: {report_request.session_id}")

    # --- PDF Generation Logic ---
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Fitness and Diet Plan Report", styles['h1']))
    elements.append(Spacer(1, 0.2 * inch))

    # User Personal Details
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

    # Raw User Input
    elements.append(Paragraph("Submitted Data:", styles['h2']))
    raw_input_data = []
    for key, value in prediction_record.get('raw_user_input', {}).items():
        raw_input_data.append([key.replace('_', ' ').title() + ":", str(value)])
    if raw_input_data:
        elements.append(Table(raw_input_data, style=TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,-1), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT')
        ])))
        elements.append(Spacer(1, 0.2 * inch))

    # Exercise Plan
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

    # Diet Plan
    elements.append(Paragraph("Diet Plan:", styles['h2']))
    diet_data = []
    for key, value in prediction_record.get('diet_predictions', {}).items():
        diet_data.append([key.replace('_', ' ').title() + ":", str(value)])
    if diet_data:
        elements.append(Table(diet_data, style=TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,-1), colors.lightblue),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT')
        ])))
        elements.append(Spacer(1, 0.2 * inch))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    # Return PDF as a stream
    filename = f"Fitness_Report_{report_request.session_id}_{datetime.date.today()}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})