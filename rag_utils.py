# rag_utils.py
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import dotenv

dotenv.load_dotenv()

# Initialize embeddings (free & good quality)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Persistent vector store
vectorstore = None

def load_knowledge_base():
    """Initialize or load RAG knowledge base"""
    global vectorstore
    persist_directory = "mentalwell_knowledge"
    
    if os.path.exists(persist_directory):
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
        print("✅ Loaded existing knowledge base")
    else:
        # Sample mental wellness knowledge base (expand this!)
        texts = [
            "Cognitive Behavioral Therapy (CBT) helps reframe negative thoughts.",
            "Mindfulness meditation reduces anxiety and improves emotional regulation.",
            "Deep breathing exercises activate the parasympathetic nervous system.",
            "Journaling helps process emotions and identify thought patterns.",
            "Regular exercise releases endorphins and improves mood significantly.",
            # Add more content from psychology books, articles, WHO guidelines, etc.
        ]
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        documents = text_splitter.create_documents(texts)
        
        vectorstore = Chroma.from_documents(
            documents, 
            embeddings, 
            persist_directory=persist_directory
        )
        print("✅ Created new RAG knowledge base")

def get_rag_chain():
    """Get RAG-powered QA chain"""
    global vectorstore
    if vectorstore is None:
        load_knowledge_base()
    
    # Custom prompt for mental wellness context
    prompt_template = """
    You are a compassionate mental wellness assistant. Use the following context to answer 
    the user's question empathetically and helpfully. If you don't know, say so gently.
    
    Context: {context}
    Question: {question}
    
    Answer:
    """
    
    PROMPT = PromptTemplate(
        template=prompt_template, 
        input_variables=["context", "question"]
    )
    
    llm = ChatOpenAI(
        model_name="gpt-4o-mini",  # or "gpt-3.5-turbo"
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 4}),
        chain_type_kwargs={"prompt": PROMPT}
    )
    return qa_chain
