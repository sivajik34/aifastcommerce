import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

def initialize_embeddings_and_retriever():
    """
    Initialize OpenAI embeddings and load the FAISS vectorstore retriever.
    
    Returns:
        embeddings: OpenAIEmbeddings instance
        retriever: FAISS retriever instance
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
    
    retriever = FAISS.load_local(
        "vectorstores/adobe_docs",
        embeddings,
        allow_dangerous_deserialization=True
    ).as_retriever(search_type="similarity", k=4)
    
    return embeddings, retriever
