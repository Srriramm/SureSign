from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from app.routes.auth_routes import router as auth_router
from app.routes.seller_routes import router as seller_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SureSign Property API",
    description="API for secure property document management",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        process_time = time.time() - start_time
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "process_time": process_time},
        )

# Include routers
logger.info("Registering auth_router")
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

logger.info("Registering seller_router")
app.include_router(seller_router, prefix="/seller", tags=["Seller Operations"])

@app.get("/")
async def root():
    """API root endpoint"""
    return {"message": "Welcome to the Property Registration API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 