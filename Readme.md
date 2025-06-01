### To run the backend
- To create a virtual python environment
'python -m venv .venv'
- To activate the virtual python environment
'.venv\Scripts\Activate.ps1'
- To Install the required dependencies
'pip install -r requirements.txt'
- To start backend
'uvicorn main:app --reload' or 'uvicorn main:app --reload --host 0.0.0.0 --port 8000'

### To run the frontend
- To install the required dependencies
'npm install'
- To run frontend
'npm run dev'


### To run docker
- To execute a dockerfile
'docker build -t fitness-app-backend .'
- To run the container
'docker run -d -p 8000:8000 --name fitness-app-backend --env MONGODB_URI="mongodb+srv://VFManager:asdf12345@main.tudbo.mongodb.net/?retryWrites=true&w=majority&appName=Main" fitness-app-backend'