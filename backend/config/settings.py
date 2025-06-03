import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Settings
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "vitafit")

# Get the directory where settings.py resides
SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))

# Go up one level to the backend directory
BACKEND_ROOT = os.path.abspath(os.path.join(SETTINGS_DIR, os.pardir))

# Define paths to model directories relative to the backend root, ensuring they are absolute
EXERCISE_MODELS_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "models", "Exercise_Models"))
DIET_MODELS_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "models", "Diet_Recommendation_Models"))
IMAGE_CLASSIFIER_MODELS_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "models", "Image_Classifier_Model"))

# --- RAG System Settings ---
KNOWLEDGE_BASE_DATA_DIR = os.path.abspath(os.path.join(BACKEND_ROOT, "data"))
VECTOR_DB_PERSIST_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "vector_db"))

# LLM settings for Hugging Face
# Changed to TinyLlama
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

# Hugging Face Token (optional, but recommended for consistent use)
HF_TOKEN = os.getenv("HF_TOKEN")

# Embedding model to use - BAAI/bge-small-en-v1.5 is excellent and stays!
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")