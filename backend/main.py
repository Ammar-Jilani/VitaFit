# backend/main.py
import os
import uuid
import datetime
import json # Import json for stringifying MongoDB data
from typing import Optional, Any
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, Depends
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
knowledge_base_instance: Any = None 

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
    global knowledge_base_instance, rag_assistant_instance 
    try:
        knowledge_base_instance = await load_rag_knowledge_base() 
        rag_assistant_instance = await initialize_rag_components(knowledge_base=knowledge_base_instance)
        print("RAG Assistant components loaded successfully!")
    except Exception as e:
        print(f"FATAL ERROR: Error initializing RAG Assistant: {e}")
        rag_assistant_instance = None 
        knowledge_base_instance = None 
        raise HTTPException(status_code=500, detail=f"Server startup error: Failed to initialize AI services. {e}")


@app.on_event("shutdown")
async def shutdown_all():
    """Closes all necessary connections on application shutdown."""
    await close_mongodb_connection()
    print("Disconnected from MongoDB.")

# --- Dependency to get the RAG Assistant instance ---
async def get_rag_assistant_dependency():
    if rag_assistant_instance is None:
        raise HTTPException(status_code=503, detail="AI services are not initialized or failed to load during startup.")
    return rag_assistant_instance

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
async def get_ai_overview_endpoint(chat_request: ChatRequest, rag: RAGAssistant = Depends(get_rag_assistant_dependency)):
    predictions_collection = get_db_collection("predictions")
    session_id = chat_request.session_id # Get session_id from the request

    # Fetch user's data from MongoDB
    user_data_record = predictions_collection.find_one({"session_id": session_id})

    if not user_data_record:
        raise HTTPException(status_code=404, detail=f"No fitness data found for session ID: {session_id}. Please submit your personal details and generate a plan first.")

    # Format the user data for the LLM
    # Exclude MongoDB's _id and timestamp for cleaner input to LLM
    user_data_for_llm = {
        k: v for k, v in user_data_record.items() 
        if k not in ["_id", "timestamp", "processed_features"]
    }
    # Convert to JSON string for the LLM
    user_data_context_str = json.dumps(user_data_for_llm, indent=2)

    try:
        # Pass the formatted user data as context to the RAG assistant
        response = await rag.get_initial_overview(user_data_context_str)
        return {"response": response}
    except Exception as e:
        print(f"Error generating AI overview for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate AI overview: {str(e)}")

@app.post("/ai/chat")
async def ai_chat_endpoint(chat_request: ChatRequest, rag: RAGAssistant = Depends(get_rag_assistant_dependency)):
    """
    Handles follow-up questions within the AI chat interface.
    """
    user_question = chat_request.message
    session_id = chat_request.session_id # Session ID is also relevant for chat context if needed later

    try:
        response = await rag.chat_with_ai(user_question, session_id)
        return {"response": response}
    except Exception as e:
        print(f"Error processing AI chat message for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process AI chat message: {str(e)}")