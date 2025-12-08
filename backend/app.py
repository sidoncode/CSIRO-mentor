"""
CSIRO Mentor - Backend API
FastAPI application for Azure App Service deployment
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CSIRO Mentor API",
    description="RAG-powered AI Assistant for CSIRO",
    version="1.0.0"
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# SYSTEM PROMPT / CONTEXT CONFIGURATION
# ============================================
SYSTEM_PROMPT = """You are CSIRO Mentor, an intelligent AI research assistant developed for CSIRO (Commonwealth Scientific and Industrial Research Organisation).

## Your Role
You are a knowledgeable, helpful, and professional AI mentor designed to assist researchers, scientists, and staff with their queries about CSIRO's research, projects, and documentation.

## Your Personality
- **Professional**: Maintain a professional and academic tone
- **Helpful**: Always aim to provide comprehensive and accurate answers
- **Clear**: Explain complex concepts in an understandable way
- **Supportive**: Encourage learning and exploration

## How to Handle Queries

### When information IS found in the knowledge base:
- Provide detailed answers based on the retrieved documents
- Always cite which documents you're referencing
- Summarize key points clearly

### When information is NOT found or is incomplete:
- DO NOT just say "information not available"
- Instead, provide helpful general knowledge about the topic
- Mention that you're providing general information since specific documents weren't found
- Suggest related topics the user might search for

### When the query is general or conversational:
- Respond naturally and helpfully
- You don't need documents for general greetings or simple questions
- Use your general knowledge to assist

## Response Guidelines
- Be conversational and helpful, not robotic
- If documents are retrieved, use them to enhance your answer
- If documents aren't relevant, still try to help with general knowledge
- Always aim to provide VALUE to the user

## Available Documents
The knowledge base contains CSIRO research documents including:
- Thermal Energy Storage materials
- Research presentations and reports
- Scientific documentation

Remember: Your goal is to HELP the user, not to refuse them. Always try to provide useful information.
"""

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", SYSTEM_PROMPT)


# ============================================
# Configuration from environment
# ============================================
class Config:
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
    AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
    ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    TOP_N_DOCUMENTS = int(os.getenv("TOP_N_DOCUMENTS", "5"))
    
    # RAG Settings
    RAG_QUERY_TYPE = os.getenv("RAG_QUERY_TYPE", "simple")  # semantic, simple, vector
    RAG_STRICTNESS = int(os.getenv("RAG_STRICTNESS", "1"))    # 1-5, lower = more flexible
    RAG_IN_SCOPE = os.getenv("RAG_IN_SCOPE", "false").lower() == "true"  # false = can use general knowledge

config = Config()


# ============================================
# Request/Response Models
# ============================================
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    use_rag: Optional[bool] = True

class Citation(BaseModel):
    content: Optional[str] = None
    title: Optional[str] = None
    filepath: Optional[str] = None

class ChatResponse(BaseModel):
    content: str
    citations: List[Citation] = []

class HealthResponse(BaseModel):
    status: str
    environment: str
    rag_enabled: bool


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Serve the frontend"""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint for Azure App Service"""
    return HealthResponse(
        status="healthy",
        environment=os.getenv("ENVIRONMENT", "development"),
        rag_enabled=config.ENABLE_RAG
    )


@app.get("/api/config")
async def get_config():
    """Get public configuration (no secrets)"""
    return {
        "rag_enabled": config.ENABLE_RAG,
        "deployment": config.AZURE_OPENAI_DEPLOYMENT,
        "search_index": config.AZURE_SEARCH_INDEX,
        "query_type": config.RAG_QUERY_TYPE,
        "strictness": config.RAG_STRICTNESS,
        "in_scope": config.RAG_IN_SCOPE
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint with RAG support"""
    
    if not config.AZURE_OPENAI_ENDPOINT or not config.AZURE_OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Azure OpenAI not configured")
    
    try:
        # Build endpoint URL
        url = f"{config.AZURE_OPENAI_ENDPOINT}/openai/deployments/{config.AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={config.AZURE_OPENAI_API_VERSION}"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": config.AZURE_OPENAI_API_KEY
        }
        
        # Build messages with system prompt
        messages = []
        
        # Add system prompt as first message
        messages.append({
            "role": "system",
            "content": SYSTEM_PROMPT
        })
        
        # Add user conversation messages
        for m in request.messages:
            messages.append({"role": m.role, "content": m.content})
        
        # Build request body
        body = {
            "messages": messages,
            "max_tokens": config.MAX_TOKENS,
            "temperature": config.TEMPERATURE
        }
        
        # Add RAG data source if enabled
        if request.use_rag and config.ENABLE_RAG and config.AZURE_SEARCH_ENDPOINT:
            body["data_sources"] = [
                {
                    "type": "azure_search",
                    "parameters": {
                        "endpoint": config.AZURE_SEARCH_ENDPOINT,
                        "index_name": config.AZURE_SEARCH_INDEX,
                        "authentication": {
                            "type": "api_key",
                            "key": config.AZURE_SEARCH_API_KEY
                        },
                        # IMPROVED RAG SETTINGS
                        "query_type": config.RAG_QUERY_TYPE,      # semantic for better understanding
                        "strictness": config.RAG_STRICTNESS,       # 1 = most flexible
                        "in_scope": config.RAG_IN_SCOPE,           # false = can use general knowledge
                        "top_n_documents": config.TOP_N_DOCUMENTS,
                        
                        # Role information to help the model understand context
                        "role_information": "You are an AI assistant helping users with CSIRO research documents. If the retrieved documents don't contain relevant information, use your general knowledge to help the user while noting that you're providing general information."
                    }
                }
            ]
        
        logger.info(f"Sending request to Azure OpenAI: {url}")
        logger.info(f"RAG settings - query_type: {config.RAG_QUERY_TYPE}, strictness: {config.RAG_STRICTNESS}, in_scope: {config.RAG_IN_SCOPE}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=body)
            
            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Azure OpenAI error: {error_data}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("error", {}).get("message", "API Error")
                )
            
            data = response.json()
            
        # Extract response
        assistant_message = data["choices"][0]["message"]["content"]
        
        # Extract citations if available
        citations = []
        if "context" in data["choices"][0]["message"]:
            for c in data["choices"][0]["message"]["context"].get("citations", []):
                citations.append(Citation(
                    content=c.get("content"),
                    title=c.get("title"),
                    filepath=c.get("filepath")
                ))
        
        return ChatResponse(content=assistant_message, citations=citations)
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Mount static files (must be after API routes)
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
