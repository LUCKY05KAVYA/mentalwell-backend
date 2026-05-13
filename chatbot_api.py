import os
import re  # ✅ For cleaning AI responses
import google.generativeai as genai
from fastapi import FastAPI, Depends, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import shutil

app = FastAPI()

# ✅ Enable CORS (for Flutter to communicate with backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change "*" to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Database setup (Stores chat history)
DATABASE_URL = "sqlite:///./chat_history.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ✅ Chat history model
class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String)
    content = Column(String)

Base.metadata.create_all(bind=engine)

# ✅ Load Google Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("⚠️ Missing API Key! Set GEMINI_API_KEY in your environment.")

genai.configure(api_key=GEMINI_API_KEY)

# ✅ Function to clean AI response
def clean_response(text):
    if text:
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Removes **bold**
        text = re.sub(r"_([^_]+)_", r"\1", text)  # Removes _italic_
    return text.strip()

# ✅ Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Folder for image uploads
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ✅ Chatbot API Endpoint (Handles both text and images)
@app.post("/chat/")
async def chat(
    message: str = Form(...), 
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    print(f"📥 Received message: {message}")  # Debugging logs

    # ✅ Save user message to the database
    db.add(ChatHistory(role="user", content=message))
    db.commit()

    # ✅ Retrieve last 5 messages for context
    chat_history = db.query(ChatHistory).order_by(ChatHistory.id.desc()).limit(5).all()
    chat_history.reverse()  # Maintain correct order

    # ✅ System prompt
    system_prompt = """
You are Mindful, a compassionate and empathetic AI mental health assistant.
- Be warm, supportive, and non-judgmental.
- Never give medical advice. Always encourage consulting a professional if needed.
- Keep responses concise (3-6 sentences).
- Use encouraging and calming language.
"""

    # ✅ Add conversation history
    prompt_text = system_prompt
    for msg in chat_history:
        prompt_text += f"{msg.role}: {msg.content}\n"
    prompt_text += "Assistant:"

    # ✅ If an image is uploaded, save it
    image_path = None
    if image:
        image_path = os.path.join(UPLOAD_FOLDER, image.filename)
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        print(f"✅ Image saved at: {image_path}")

    # ✅ Call Google Gemini API for text processing
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(message)

        # ✅ Handle AI response correctly
        bot_reply = getattr(response, "text", "⚠️ AI did not generate a response.")
        bot_reply = clean_response(bot_reply)

        # ✅ Save AI response to chat history
        db.add(ChatHistory(role="assistant", content=bot_reply))
        db.commit()

        print(f"📤 Gemini Response: {bot_reply}")
        return {"reply": bot_reply}

    except Exception as e:
        print(f"❌ Google Gemini API Error: {str(e)}")
        return {"reply": f"⚠️ AI service unavailable: {str(e)}"}

# ✅ Endpoint to get the last 10 messages
@app.get("/chat-history/")
async def get_chat_history(db: Session = Depends(get_db)):
    chat_history = db.query(ChatHistory).order_by(ChatHistory.id.desc()).limit(10).all()
    return [{"role": record.role, "content": record.content} for record in chat_history]
