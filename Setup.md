## To run the backend
- To create a virtual python environment
'python -m venv .venv'

- To activate the virtual python environment
'.venv\Scripts\Activate.ps1'

- To Install the required dependencies
'pip install -r requirements.txt'

- To start backend
'uvicorn main:app --reload' or 'uvicorn main:app --reload --host 0.0.0.0 --port 8000'

- You need to define the following .env variables
MONGODB_URI (your mongodb atlas connection string)
DB_NAME (your mongodb atlas database name)
HF_TOKEN (your huggingface token)

## To run the frontend
- To install the required dependencies
'npm install'

- To run frontend
'npm run dev'

- You would also have to manually change the url in both FitnessPlanner.jsx and CalorieEstimation.jsx, if you dont plan to host or run it on your local machine.


## To run docker
- To build the dockerfile
'docker build -t vitafit-backend .' OR 'docker build --platform linux/arm64 -t vitafit-backend .'

- To run the container
docker run -d -p 8000:8000 --name vitafit-backend \
  --env MONGODB_URI=YOUR_CONNECTION_STRING \
  --env DB_NAME=YOUR_DATABASE_NAME \
  --env HF_TOKEN=YOUR_HF_TOKEN \
  vitafit-backend