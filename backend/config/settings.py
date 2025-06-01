# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Settings
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "vitafit")

# Get the directory where settings.py resides
SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))

# Go up one level to the backend directory
BACKEND_ROOT = os.path.abspath(os.path.join(SETTINGS_DIR, os.pardir)) # Ensure BACKEND_ROOT is absolute

# Define paths to model directories relative to the backend root, ensuring they are absolute
EXERCISE_MODELS_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "models", "Exercise_Models"))
DIET_MODELS_PATH = os.path.abspath(os.path.join(BACKEND_ROOT, "models", "Diet_Recommendation_Models"))