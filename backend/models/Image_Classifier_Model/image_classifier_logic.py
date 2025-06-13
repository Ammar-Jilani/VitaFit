# backend/models/Image_Classifier_Model/image_classifier_logic.py

import os
import io
from PIL import Image
from typing import List, Dict, Union, Any, Optional
from ultralytics import YOLO
from pydantic import BaseModel


class DishInfo(BaseModel):
    class_name: str
    confidence: float
    box: List[float] 
    origin: Union[str, None] = None
    description: Union[str, None] = None
    estimated_calories: Union[str, None] = None

class DetectionResponse(BaseModel):
    status: str
    message: str
    detections: List[DishInfo]

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
        self.yolo_model: Optional[YOLO] = None
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        try:
            self.yolo_model = YOLO(self.model_path)
            print(f"YOLOv8 model loaded successfully from {self.model_path}")
        except Exception as e:
            print(f"Error loading YOLOv8 model from {self.model_path}: {e}")
            self.yolo_model = None

    def predict_dish_from_image(self, image_bytes: bytes) -> DetectionResponse:
        if self.yolo_model is None:
            raise Exception("Image detection model is not loaded. Cannot perform prediction.")

        try:
            img = Image.open(io.BytesIO(image_bytes))

            results = self.yolo_model.predict(source=img, conf=0.4, iou=0.7, imgsz=640, verbose=False)

            best_dish_info: Optional[DishInfo] = None
            max_confidence = -1.0 

            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        cls = int(box.cls[0].item())
                        name = self.yolo_model.names[cls]
                        conf = round(box.conf[0].item(), 2)
                        x1, y1, x2, y2 = [round(x) for x in box.xyxy[0].tolist()]

                        if conf > max_confidence:
                            max_confidence = conf
                            dish_details = DISH_DATABASE.get(name)
                            best_dish_info = DishInfo(
                                class_name=name,
                                confidence=conf,
                                box=[x1, y1, x2, y2],
                                origin=dish_details.get("origin") if dish_details else None,
                                description=dish_details.get("description") if dish_details else None,
                                estimated_calories=dish_details.get("estimated_calories") if dish_details else None
                            )
            
            if best_dish_info:
                return DetectionResponse(
                    status="success",
                    message="Most confident dish detected.",
                    detections=[best_dish_info] 
                )
            else:
                return DetectionResponse(
                    status="success",
                    message="No known dishes detected in the image.",
                    detections=[]
                )

        except Exception as e:
            raise Exception(f"An error occurred during dish prediction: {e}")