from fastapi import FastAPI


app = FastAPI(
    title="Nest Finder API",
    description="Property listings",
    version="0.1.0",
)


@app.get("/")
def home():
    return "Welcome to the Nest Finder API"


base_prefix = "/api/v1"
