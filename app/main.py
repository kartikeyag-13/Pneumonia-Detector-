from fastapi import FastAPI

from app.routers import auth, images, predictions

app = FastAPI(
    title="Pneumonia Detection API",
    description="Backend foundation for the pneumonia-detection service.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(images.router)
app.include_router(predictions.router)
app.include_router(predictions.history_router)


@app.get("/")
def read_root():
    """
    Basic health-check / welcome endpoint.
    """
    return {"message": "Pneumonia Detection API is running"}
