# Use an official Python runtime as a parent image
# We choose a slim version for smaller image size
FROM --platform=linux/arm64 python:3.11-slim-buster

# Install system dependencies required by OpenCV (and therefore Ultralytics)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    libxrandr2 \
    && rm -rf /var/lib/apt/lists/* # Clean up apt cache to keep image small
# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
# We copy it separately to leverage Docker's layer caching
COPY requirements.txt .

# ...
# Install any needed packages specified in requirements.txt
# Explicitly use the CPU index URL for PyTorch to avoid downloading CUDA binaries
RUN pip install --no-cache-dir -r requirements.txt --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple/

# ... rest of your Dockerfile

# Copy the rest of the application code into the container
# This includes main.py and your model directories
COPY . .

# Expose the port that the FastAPI application will run on
# Default for Uvicorn is 8000
EXPOSE 8000

# Command to run the application using Uvicorn
# The --host 0.0.0.0 makes the app accessible from outside the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]