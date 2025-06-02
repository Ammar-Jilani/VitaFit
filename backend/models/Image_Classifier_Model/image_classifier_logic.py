# backend/models/Image_Classifier_Model/image_classifier_logic.py

import os
import io
from PIL import Image
from typing import List, Dict, Union, Any, Optional
from ultralytics import YOLO # type: ignore
from pydantic import BaseModel # You'll need pydantic if you don't have it (pip install pydantic)


# --- Pydantic Models for API Response ---
# These models are used to define the structure of the data returned by the API
class DishInfo(BaseModel):
    """Model for detailed information about a detected dish."""
    class_name: str
    confidence: float
    box: List[float] # [x1, y1, x2, y2]
    origin: Union[str, None] = None
    description: Union[str, None] = None
    estimated_calories: Union[str, None] = None

class DetectionResponse(BaseModel):
    """Model for the overall API response."""
    status: str
    message: str
    detections: List[DishInfo]

# --- Mock MongoDB Data (Can be replaced with actual DB integration later) ---
# This dictionary simulates your MongoDB collection for dish information.
DISH_DATABASE = {
    "Burger": {
        "origin": "United States/Germany (disputed)",
        "description": "A sandwich consisting of a cooked patty of ground meat, usually beef, placed inside a sliced bun.",
        "estimated_calories": "300-600 kcal"
    },
    "Pizza": {
        "origin": "Italy (Naples)",
        "description": "A savory dish of Italian origin consisting of a usually round, flattened base of leavened wheat-based dough topped with tomatoes, cheese, and various other ingredients, baked at a high temperature.",
        "estimated_calories": "250-400 kcal per slice"
    },
    "Donut": {
        "origin": "Netherlands/United States",
        "description": "A small fried cake of sweetened dough, typically in the form of a ring or disk.",
        "estimated_calories": "200-450 kcal"
    },
    "Hotdog": {
        "origin": "Germany/United States",
        "description": "A grilled or steamed sausage sandwich where the sausage is served in the slit of a partially sliced bun.",
        "estimated_calories": "250-500 kcal"
    },
    "FriedChicken": {
        "origin": "Scotland/Southern United States",
        "description": "Dish consisting of chicken pieces that have been coated in a seasoned flour or batter and fried.",
        "estimated_calories": "300-600 kcal per serving"
    }
}

class ImageClassifier:
    def __init__(self, model_path: str):
        """
        Initializes the Image Classifier by loading the YOLOv8 model.
        Args:
            model_path (str): The absolute path to the YOLOv8 .pt model file.
        """
        self.yolo_model: Optional[YOLO] = None
        self.model_path = model_path
        self._load_model() # Load model during initialization

    def _load_model(self):
        """
        Loads the YOLOv8 model. This is called during the class initialization.
        """
        try:
            # Ultralytics YOLO automatically handles device selection (CPU/GPU)
            self.yolo_model = YOLO(self.model_path)
            print(f"YOLOv8 model loaded successfully from {self.model_path}")
        except Exception as e:
            print(f"Error loading YOLOv8 model from {self.model_path}: {e}")
            self.yolo_model = None # Ensure model is None if loading fails

    def predict_dish_from_image(self, image_bytes: bytes) -> DetectionResponse:
        """
        Performs dish detection on an image provided as bytes.
        Args:
            image_bytes (bytes): The raw bytes of the image file.
        Returns:
            DetectionResponse: A Pydantic model containing detection results.
        Raises:
            Exception: If the model is not loaded or an error occurs during prediction.
        """
        if self.yolo_model is None:
            raise Exception("Image detection model is not loaded. Cannot perform prediction.")

        try:
            # Open image using PIL for YOLOv8
            img = Image.open(io.BytesIO(image_bytes))

            # Perform inference
            # conf: Confidence threshold (e.g., 0.25 means only show detections with >25% confidence)
            # iou: IoU threshold for Non-Maximum Suppression (NMS)
            # imgsz: Image size for inference
            # verbose: False suppresses detailed Ultralytics output during prediction
            results = self.yolo_model.predict(source=img, conf=0.25, iou=0.7, imgsz=640, verbose=False)

            detected_dishes_info: List[DishInfo] = []

            # Process results for each image (predict returns a list, usually one item for single image)
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0].item())
                    name = self.yolo_model.names[cls] # Get class name from model
                    conf = round(box.conf[0].item(), 2)
                    x1, y1, x2, y2 = [round(x) for x in box.xyxy[0].tolist()]

                    # Fetch additional info from mock database
                    dish_details = DISH_DATABASE.get(name)

                    detected_dishes_info.append(
                        DishInfo(
                            class_name=name,
                            confidence=conf,
                            box=[x1, y1, x2, y2],
                            origin=dish_details.get("origin") if dish_details else None,
                            description=dish_details.get("description") if dish_details else None,
                            estimated_calories=dish_details.get("estimated_calories") if dish_details else None
                        )
                    )
            
            if not detected_dishes_info:
                return DetectionResponse(
                    status="success",
                    message="No known dishes detected in the image.",
                    detections=[]
                )

            return DetectionResponse(
                status="success",
                message="Dishes detected successfully.",
                detections=detected_dishes_info
            )

        except Exception as e:
            raise Exception(f"An error occurred during dish prediction: {e}")