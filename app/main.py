from fastapi import FastAPI, HTTPException
from app.database import init_db, close_db
from app.schemas import IdentifyRequest, IdentifyResponse, ListUserData
from app.services import ContactService
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Postgres DB Startup done")
    yield
    # Shutdown
    await close_db()
    logger.info("Postgres DB Shutdown done")


app = FastAPI(title="Bitespeed Identity Service", version="1.0.0", lifespan=lifespan)


@app.post("/identify", response_model=IdentifyResponse)
async def identify_contact(request: IdentifyRequest):
    try:
        if not request.email and not request.phone_number:
            raise HTTPException(status_code=400, detail="Either email or phoneNumber is required")
        
        result = await ContactService.identify_contact(request)
        return result
    
    except Exception as e:
        logger.error(f"Error in identify endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/list_users", response_model=list[ListUserData])
async def list_users():
    try:
        return await ContactService.list_all_contacts()
    except Exception as e:
        logger.error(f"Error in identify endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/", include_in_schema=False)
async def root():
    return {
        "title": "Bitespeed Identity Service",
        "version": "1.0.0",
        "routes": {
            "/identify": {
                "method": "POST",
                "description": "Identifies contact by email or phone number.",
                "payload": {
                    "email": "string (optional)",
                    "phoneNumber": "string (optional)"
                },
                "response": {
                    "contact": {
                        "primaryContactId": "int",
                        "emails": ["list of strings"],
                        "phoneNumbers": ["list of strings"],
                        "secondaryContactIds": ["list of ints"]
                    }
                }
            },
            "/list_users": {
                "method": "GET",
                "description": "Lists all identified users and contacts.",
                "response": [
                    {
                        "id": "int",
                        "email": "string | null",
                        "phoneNumber": "string | null",
                        "linkedId": "int | null",
                        "linkPrecedence": "primary/secondary",
                        "createdAt": "datetime",
                        "updatedAt": "datetime",
                        "deletedAt": "datetime | null"
                    }
                ]
            },
            "/health": {
                "method": "GET",
                "description": "Health check endpoint.",
                "response": {"status": "healthy"}
            }
        },
        "docs": "/docs",
        "openapi": "/openapi.json"
    }
