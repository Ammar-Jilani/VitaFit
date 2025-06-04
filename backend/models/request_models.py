# backend/models/request_models.py
from typing import Optional, Literal
from pydantic import BaseModel, Field

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

class ChatRequest(BaseModel):
    session_id: str
    message: str