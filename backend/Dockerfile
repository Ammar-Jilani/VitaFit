# Use an official Python runtime as a parent image
# We choose a slim version for smaller image size
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
# We copy it separately to leverage Docker's layer caching
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# This includes main.py and your model directories
COPY . .

# Expose the port that the FastAPI application will run on
# Default for Uvicorn is 8000
EXPOSE 8000

# Command to run the application using Uvicorn
# The --host 0.0.0.0 makes the app accessible from outside the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]