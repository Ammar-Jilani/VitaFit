import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "vitafit")

SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))

BACKEND_ROOT = os.path.abspath(os.path.join(SETTINGS_DIR, os.pardir))

EXERCISE_MODELS_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "models", "Exercise_Models"))
DIET_MODELS_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "models", "Diet_Recommendation_Models"))
IMAGE_CLASSIFIER_MODELS_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "models", "Image_Classifier_Model"))

KNOWLEDGE_BASE_DATA_DIR = os.path.abspath(os.path.join(BACKEND_ROOT, "data"))
VECTOR_DB_PERSIST_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "vector_db"))

LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

HF_TOKEN = os.getenv("HF_TOKEN")

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")