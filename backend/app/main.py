from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth

# setting up the app
app = FastAPI(
    title=settings.APP_NAME,
    description="A FastAPI application for dataset request management",
    version="0.1.0",
    docs_url="/docs",
)

# setting up the cors middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

# setting up the home route of the app
@app.get("/")
def home():
    return {"message":"Welcome Home to the dataset-request-deck"}


# setting up the endpoint to check the health of the app
@app.get("/health")
def health_check():
    return{
        "status":"ok",
        "app":settings.APP_NAME
    }
