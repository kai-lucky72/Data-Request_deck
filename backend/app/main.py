from fastapi import FastAPI, Request


app = FastAPI(
    title="Dataset-Request-deck",
    docs_url="/docs",
)

# setting up the home route of the app
@app.get("/")
def home():
    return {"message":"Welcome Home to the dataset-request-deck"}


# setting up the endpoint to check the health of the app
@app.get("/health")
def health_check():
    return{
        "status":"ok",
        "app":"Dataset-Request-Deck"
    }
