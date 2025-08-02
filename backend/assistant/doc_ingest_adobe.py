import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://experienceleague.adobe.com/en/docs/commerce"
HEADERS = {"User-Agent": "Mozilla/5.0"}
ALLOWED_DOMAIN = "experienceleague.adobe.com"

visited = set()
all_docs = []

def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.netloc.endswith(ALLOWED_DOMAIN) and "/docs/commerce" in parsed.path and not any(x in url for x in ["#", "?"])

def get_all_links(page_url):
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        anchors = soup.find_all("a", href=True)

        links = set()
        for tag in anchors:
            href = tag.get("href")
            if not href:
                continue
            absolute_url = urljoin(page_url, href)
            if is_valid_url(absolute_url):
                links.add(absolute_url)
        return links
    except Exception as e:
        print(f"Error fetching links from {page_url}: {e}")
        return []

def get_page_text(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.get_text(separator="\n", strip=True)
        return content
    except Exception as e:
        print(f"Error fetching page {url}: {e}")
        return None

def crawl(start_url, max_pages=300):
    to_visit = [start_url]
    while to_visit and len(visited) < max_pages:
        current = to_visit.pop(0)
        if current in visited:
            continue
        print(f"🔍 Crawling: {current}")
        visited.add(current)
        page_text = get_page_text(current)
        if page_text:
            doc = Document(page_content=page_text, metadata={"source": current})
            all_docs.append(doc)

        links = get_all_links(current)
        for link in links:
            if link not in visited and link not in to_visit:
                to_visit.append(link)
        time.sleep(1)  # polite crawling

def embed_and_save():
    print(f"📄 Total documents: {len(all_docs)}")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(all_docs)

    print(f"🔢 Total chunks: {len(chunks)}")
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("vectorstores/adobe_docs")
    print("✅ Saved vectorstore at vectorstores/adobe_docs")

if __name__ == "__main__":
    crawl(BASE_URL)
    embed_and_save()
