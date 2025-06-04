FROM python:3.11-slim-buster

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    libxrandr2 \
    && rm -rf /var/lib/apt/lists/* # Clean up apt cache to keep image smaller
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple/

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]