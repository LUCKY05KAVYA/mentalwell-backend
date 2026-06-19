import os
import re
import google.generativeai as genai
from fastapi import FastAPI, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import shutil
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

app = FastAPI(title="MentalWell Backend - RAG Enhanced")

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Database setup
DATABASE_URL = "sqlite:///./chat_history.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String)
    content = Column(String)

Base.metadata.create_all(bind=engine)

# ✅ Gemini Setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("⚠️ Missing GEMINI_API_KEY in environment variables.")

genai.configure(api_key=GEMINI_API_KEY)

# ✅ RAG Setup
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = None
PERSIST_DIR = "mentalwell_knowledge"

def init_rag():
    global vectorstore
    if os.path.exists(PERSIST_DIR):
        vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
    else:
        # Initial mental wellness knowledge base
        sample_docs = [
            "Cognitive Behavioral Therapy helps identify and change negative thought patterns.",
            "Practicing mindfulness daily reduces stress and improves emotional regulation.",
            "Deep breathing exercises can quickly activate the body's relaxation response.",
            "Regular physical activity releases endorphins and improves mood.",
            "Journaling helps process emotions and gain clarity on personal challenges.",
            "Building strong social connections is vital for mental wellbeing.",
        ]
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        documents = text_splitter.create_documents(sample_docs)
        
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=PERSIST_DIR
        )

init_rag()  # Initialize on startup

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def clean_response(text):
    if text:
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)
    return text.strip()

class ChatResponse(BaseModel):
    reply: str

# ✅ Main Chat Endpoint with RAG
@app.post("/chat/")
async def chat(
    message: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        # Save user message
        db.add(ChatHistory(role="user", content=message))
        db.commit()

        # Get recent history
        chat_history = db.query(ChatHistory).order_by(ChatHistory.id.desc()).limit(6).all()
        chat_history.reverse()

        # RAG Retrieval
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        relevant_docs = retriever.invoke(message)
        context = "\n".join([doc.page_content for doc in relevant_docs])

        # Enhanced Prompt with RAG
        system_prompt = f"""
You are Mindful, a compassionate mental health companion.
Use the following context to give warm, helpful, and accurate responses.

Context:
{context}

Guidelines:
- Be empathetic and supportive
- Never give medical diagnosis or treatment advice
- Encourage professional help when needed
- Keep responses warm and concise
"""

        # Build full prompt
        prompt_text = system_prompt
        for msg in chat_history:
            prompt_text += f"{msg.role.capitalize()}: {msg.content}\n"
        prompt_text += "Assistant:"

        # Use Gemini with RAG context
        model = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0.7
        )

        response = model.invoke(prompt_text)
        bot_reply = clean_response(response.content)

        # Save AI response
        db.add(ChatHistory(role="assistant", content=bot_reply))
        db.commit()

        # Handle image if uploaded
        if image:
            os.makedirs("uploads", exist_ok=True)
            image_path = f"uploads/{image.filename}"
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

        return {"reply": bot_reply}

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat-history/")
async def get_chat_history(db: Session = Depends(get_db)):
    history = db.query(ChatHistory).order_by(ChatHistory.id.desc()).limit(10).all()
    return [{"role": record.role, "content": record.content} for record in history]
