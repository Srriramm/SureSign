from fastapi import FastAPI
from app.routes import auth_routes
from app.routes import seller_routes
from app.routes import buyer_routes
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="API for secure property registration platform",
    version=settings.APP_VERSION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:5173",  # Vite development server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include authentication routes
app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])

# Include seller routes - ensure prefix matches frontend URLs
app.include_router(seller_routes.router, prefix="/seller", tags=["Seller"])

# Include buyer routes
app.include_router(buyer_routes.router, prefix="/buyer", tags=["Buyer"])

@app.get("/")
async def root():
    return {
        "message": f"{settings.APP_NAME} Property Registration Platform API", 
        "version": settings.APP_VERSION,
        "docs_url": "/docs"
    }

