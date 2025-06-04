### To run the backend
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

### To run the frontend
- To install the required dependencies
'npm install'

- To run frontend
'npm run dev'


### To run docker
- To execute the dockerfile
'docker build -t vitafit-backend .'

- To run the container
'docker run -d -p 8000:8000 --name vitafit-backend --env MONGODB_URI="mongodb+srv://VFManager:asdf12345@main.tudbo.mongodb.net/?retryWrites=true&w=majority&appName=Main" vitafit-backend'