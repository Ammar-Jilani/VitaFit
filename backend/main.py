# backend/main.py
import os
import uuid
import datetime
from typing import Optional, Any
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
from config.settings import DB_NAME, IMAGE_CLASSIFIER_MODELS_PATH 
from database.mongodb_client import connect_to_mongodb, close_mongodb_connection, get_db_collection
from models.request_models import UserInput, UserPersonalDetails, ReportRequest, DietPlanRequest, ChatRequest
from services.exercise_service import load_exercise_models, predict_exercise
from services.diet_service import load_diet_models, predict_diet
from services.report_service import generate_report as generate_pdf_report
from models.Image_Classifier_Model.image_classifier_logic import ImageClassifier, DetectionResponse
from utils.helpers import convert_numpy_types
from services.rag_service import RAGAssistant, load_rag_knowledge_base, initialize_rag_components 

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Fitness and Diet Prediction API",
    description="API for predicting exercise and diet plans based on user data, and dish image classification, and AI-powered health overview.",
    version="1.0.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

image_classifier_model: Optional[ImageClassifier] = None
rag_assistant_instance: Optional[RAGAssistant] = None

# --- Startup Events ---
@app.on_event("startup")
async def startup_all():
    """
    Handles all necessary startup procedures:
    1. Connect to MongoDB.
    2. Load Machine Learning Models (Exercise, Diet, Image Classifier).
    3. Initialize RAG components (Knowledge Base, LLM, Retriever).
    """
    # 1. Connect to MongoDB
    try:
        await connect_to_mongodb()
        print("Connected to MongoDB database:", DB_NAME)
    except Exception as e:
        print(f"Application startup failed due to MongoDB connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Server startup error: Failed to connect to MongoDB. {e}")

    # 2. Load Machine Learning Models
    try:
        await load_exercise_models()
        print("Exercise models loaded successfully!")
        await load_diet_models()
        print("Diet models loaded successfully!")
        
        global image_classifier_model
        yolo_model_file_name = "image_classification.pt"
        full_yolo_model_path = os.path.join(IMAGE_CLASSIFIER_MODELS_PATH, yolo_model_file_name)
        
        try:
            image_classifier_model = ImageClassifier(model_path=full_yolo_model_path)
            if image_classifier_model.yolo_model is None:
                raise RuntimeError("YOLO model did not load correctly within ImageClassifier.")
            print(f"Image classifier model loaded successfully from {full_yolo_model_path}!")
        except Exception as e:
            print(f"Error loading image classifier model: {e}")
            image_classifier_model = None
            print("Warning: Image classification endpoint will not be available.")

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"An unexpected error occurred during ML model loading: {e}")
        raise HTTPException(status_code=500, detail=f"Server startup error: Failed to load ML models. {e}")

    # --- NEW: 3. Initialize RAG Components ---
    global rag_assistant_instance
    try:
        knowledge_base = await load_rag_knowledge_base() 
        
        rag_assistant_instance = await initialize_rag_components(knowledge_base=knowledge_base)
        
        print("RAG Assistant components loaded successfully!")
    except Exception as e:
        print(f"Error initializing RAG Assistant: {e}")
        rag_assistant_instance = None
        print("Warning: AI Health Overview endpoint will not be available.")


@app.on_event("shutdown")
async def shutdown_all():
    """Closes all necessary connections on application shutdown."""
    await close_mongodb_connection()
    print("Disconnected from MongoDB.")

# --- API Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Fitness and Diet Prediction API!"}

@app.post("/predict_exercise")
async def predict_exercise_plan_endpoint(user_input: UserInput):
    predictions_collection = get_db_collection("predictions")
    exercise_predictions = predict_exercise(user_input)
    prediction_record = {
        "session_id": user_input.session_id,
        "timestamp": datetime.datetime.utcnow(),
        "raw_user_input": convert_numpy_types(user_input.dict()),
        "processed_features": None,
        "exercise_predictions": convert_numpy_types(exercise_predictions),
        "diet_predictions": {}
    }
    from services.exercise_service import preprocess_user_data_for_exercise, label_encoders as exercise_label_encoders
    if exercise_label_encoders is None:
         raise HTTPException(status_code=500, detail="Exercise label encoders not loaded during initial startup.")
    
    _, processed_core_features = preprocess_user_data_for_exercise(user_input)
    prediction_record["processed_features"] = convert_numpy_types(processed_core_features)

    try:
        predictions_collection.update_one(
            {"session_id": user_input.session_id},
            {"$set": prediction_record},
            upsert=True
        )
        print(f"Exercise predictions for session {user_input.session_id} stored/updated in MongoDB.")
    except Exception as e:
        print(f"Error storing exercise predictions in MongoDB: {e}")
        print(f"Invalid document: {prediction_record}")
        raise HTTPException(status_code=500, detail=f"Failed to store exercise predictions in database: {e}")

    return {
        "session_id": user_input.session_id,
        "exercise_plan": exercise_predictions,
        "message": "Exercise plan generated. You can now generate a diet plan with more details if desired."
    }

@app.post("/predict_diet")
async def predict_diet_plan_endpoint(diet_request: DietPlanRequest):
    predictions_collection = get_db_collection("predictions")
    prediction_record = predictions_collection.find_one({"session_id": diet_request.session_id})

    if not prediction_record:
        raise HTTPException(status_code=404, detail=f"No exercise predictions found for session ID: {diet_request.session_id}. Please submit initial user data first.")

    processed_core_features = prediction_record.get('processed_features', {})
    exercise_predictions = prediction_record.get('exercise_predictions', {})
    raw_user_input = prediction_record.get('raw_user_input', {})

    if not processed_core_features or not exercise_predictions:
        raise HTTPException(status_code=500, detail="Incomplete stored data for session. Cannot generate diet plan.")

    diet_predictions = predict_diet(processed_core_features, exercise_predictions, raw_user_input)

    try:
        predictions_collection.update_one(
            {"session_id": diet_request.session_id},
            {"$set": {
                "diet_predictions": convert_numpy_types(diet_predictions),
                "last_updated": datetime.datetime.utcnow()
            }}
        )
        print(f"Diet predictions for session {diet_request.session_id} updated in MongoDB.")
    except Exception as e:
        print(f"Error updating diet predictions in MongoDB: {e}")
        print(f"Invalid diet document for update: {convert_numpy_types(diet_predictions)}")
        raise HTTPException(status_code=500, detail=f"Failed to update diet predictions in database: {e}")

    return {
        "session_id": diet_request.session_id,
        "diet_plan": diet_predictions,
        "message": "Diet plan generated successfully!"
    }

@app.post("/generate_report", response_class=StreamingResponse)
async def generate_report_endpoint(report_request: ReportRequest):
    return await generate_pdf_report(report_request)

@app.post("/classify_dish", response_model=DetectionResponse)
async def classify_dish_endpoint(file: UploadFile = File(...)):
    if image_classifier_model is None:
        raise HTTPException(status_code=500, detail="Dish detection model is not loaded or available.")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    try:
        image_bytes = await file.read()
        detection_response = image_classifier_model.predict_dish_from_image(image_bytes)
        return detection_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dish detection failed: {str(e)}")

@app.post("/ai/overview")
async def get_ai_overview_endpoint(report_content: ChatRequest):
    if rag_assistant_instance is None:
        raise HTTPException(status_code=500, detail="AI Health Overview service is not loaded or available.")
    
    user_report_text = report_content.message 

    try:
        response = await rag_assistant_instance.get_initial_overview(user_report_text)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI overview: {str(e)}")

@app.post("/ai/chat")
async def ai_chat_endpoint(chat_request: ChatRequest):
    """
    Handles follow-up questions within the AI chat interface.
    """
    if rag_assistant_instance is None:
        raise HTTPException(status_code=500, detail="AI Health Overview service is not loaded or available.")
    
    user_question = chat_request.message
    session_id = chat_request.session_id

    try:
        response = await rag_assistant_instance.chat_with_ai(user_question, session_id)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process AI chat message: {str(e)}")