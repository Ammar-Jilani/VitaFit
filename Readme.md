# VitaFit AI: Your Personalized Fitness & Nutrition Assistant

Welcome to VitaFit AI, an intelligent web application designed to help you achieve your fitness and nutrition goals through personalized exercise and diet plans, powered by AI-driven insights and image-based calorie estimation.

## Features
- Personalized Fitness Plans: Generate tailored daily exercise recommendations based on your age, gender, height, weight, and calorie intake.

- Customized Diet Plans: Receive a suggested diet plan with recommended calories, protein, carbs, and fats, designed to complement your fitness goals.

- BMI Calculation: Automatically calculates your Body Mass Index (BMI) as you input your physical details.

- Comprehensive Fitness Reports: Download a detailed PDF report summarizing your personalized exercise and diet plans.

- AI Fitness Assistant Chat: Interact with an intelligent AI chatbot to get answers to your fitness and nutrition questions, providing real-time guidance and support.

- Image-Based Calorie Estimation: Upload photos of your food to instantly get estimated calorie counts and dish details using advanced object detection.

## Technologies Used
This project leverages a modern tech stack to deliver a robust and interactive experience:

### Frontend:

React.js: A powerful JavaScript library for building user interfaces.

Axios: A promise-based HTTP client for making API requests to the backend.

### Backend:

Python: The core programming language for the backend logic.

FastAPI: A modern, fast (high-performance) web framework for building APIs with Python 3.7+.

Uvicorn: An ASGI server for running asynchronous Python web applications, providing high concurrency.

Machine Learning/AI: (Implicitly) Models for exercise prediction, diet planning, and image-based food detection/calorie estimation.

## How It Works (High-Level)
The application guides you through a seamless process:

Input Your Data: You start by providing essential personal and fitness-related information.

Generate Plans: The backend processes your data to generate a personalized exercise plan.

Diet Plan (Optional): You can then opt to generate a complementary diet plan.

Interactive AI: Engage with the AI chat assistant for deeper insights or specific queries related to your health and fitness.

Food Analysis: Use the calorie estimation feature to upload images of your meals, which are analyzed by the backend to identify dishes and estimate calorie content.

Download Report: A comprehensive PDF report compiling all your personalized data and plans is available for download.
