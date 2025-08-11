from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
import time
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from magento.client import get_magento_client
load_dotenv()
# Initialize Magento API client
magento_client = get_magento_client()

# Initialize OpenAI Embeddings
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

# Product fetching configuration
page_size = 100
current_page = 1
documents = []

while True:
    endpoint = f"products?searchCriteria[pageSize]={page_size}&searchCriteria[currentPage]={current_page}"
    response = magento_client.send_request(endpoint, method="GET")

    if not response or "items" not in response or len(response["items"]) == 0:
        print("✅ Finished loading all products.")
        break

    for product in response["items"]:
        sku = product.get("sku", "")
        name = product.get("name", "")
        if sku and name:
            doc = Document(
                page_content=f"{name} ({sku})",
                metadata={"sku": sku, "name": name}
            )
            documents.append(doc)

    print(f"📦 Fetched page {current_page} with {len(response['items'])} products.")
    current_page += 1
    time.sleep(0.2)  # avoid overwhelming Magento server

# Create FAISS vector store
vectorstore = FAISS.from_documents(documents, embeddings)

# Save locally for reuse
vectorstore.save_local("vectorstores/faiss_catalog")

print("✅ Vector store created and saved to 'faiss_catalog'")
