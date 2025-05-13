from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import sys
import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from sample import chat_with_gemini, initialize_chat
from fastapi.responses import StreamingResponse, JSONResponse
import io
import json
from typing import List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)


app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,

    allow_origins=["http://localhost:3000",  # For local development
        "https://ai-travel-planning-ch-git-b1948c-chetana-muralidharans-projects.vercel.app",
        "https://ai-travel-planning-chatbot-d2gh.vercel.app",
        "https://ai-travel-planning-ch-git-b1948c-chetana-muralidharans-projects.vercel.app"],  # Updated to match frontend port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chat
initialize_chat()

# --- Database setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    messages = relationship("ChatMessage", back_populates="user")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    sender = Column(String, nullable=False)  # 'user' or 'bot'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="messages")

Base.metadata.create_all(bind=engine)

# --- Auth utils ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "supersecretkey"  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def get_current_user(token: str = Depends(lambda x: x), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None
        user = db.query(User).filter(User.email == email).first()
        return user
    except:
        return None

# --- Pydantic models ---
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str
    token: Optional[str] = None


class MessageResponse(BaseModel):
    id: int
    sender: str
    content: str
    timestamp: datetime

# --- Auth endpoints ---
@app.post("/api/signup")
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(request.password)
    new_user = User(
        name=request.name, email=request.email, hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token = create_access_token({"sub": new_user.email})
    logger.info(f"New user registered: {new_user.name}, {new_user.email}")
    return {"token": token, "name": new_user.name}


@app.post("/api/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.email})
    logger.info(f"User logged in: {user.name}, {user.email}")
    return {"token": token, "name": user.name}


# --- Chat endpoint (existing) ---
@app.post("/api/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        logger.info(f"Received message: {request.message}")
        user = None
        
        # Try to authenticate the user if token is provided
        if request.token:
            user = get_current_user(request.token, db)
            
        response = chat_with_gemini(request.message)
        logger.info(f"Generated response: {response}")
        
        # Save the conversation if user is authenticated
        if user and not isinstance(response, dict):
            # Save user message
            user_message = ChatMessage(
                user_id=user.id,
                sender="user",
                content=request.message
            )
            db.add(user_message)
            
            # Save bot response
            bot_message = ChatMessage(
                user_id=user.id,
                sender="bot",
                content=response
            )
            db.add(bot_message)
            db.commit()

        # If the response is a PDF, stream it as a file
        # if isinstance(response, dict) and response.get("type") == "pdf":
        #     pdf_bytes = response["data"]
        #     filename = response["filename"]
        #     return StreamingResponse(
        #         io.BytesIO(pdf_bytes),
        #         media_type="application/pdf",
        #         headers={"Content-Disposition": f"attachment; filename={filename}"}
        #     )
        # Otherwise, return as JSON
        return JSONResponse({"response": response})
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat-history")
async def get_chat_history(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    messages = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).order_by(ChatMessage.timestamp).all()
    
    return {"messages": [
        {
            "id": message.id,
            "sender": message.sender,
            "content": message.content,
            "timestamp": message.timestamp
        } for message in messages
    ]}


# @app.post("/api/download_pdf")
# async def download_pdf(request: Request):
#     data = await request.json()
#     itinerary = data.get("itinerary")
#     destination = data.get("destination")
#     duration = data.get("duration")
#     if not itinerary or not destination or not duration:
#         raise HTTPException(status_code=400, detail="Missing itinerary data")
#     pdf_buffer = generate_itinerary_pdf(itinerary, destination, duration)
#     filename = f"itinerary_{destination}.pdf"
#     return StreamingResponse(
#         io.BytesIO(pdf_buffer.getvalue()),
#         media_type="application/pdf",
#         headers={"Content-Disposition": f"attachment; filename={filename}"}
#     )


if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 
