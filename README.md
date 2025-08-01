# 🧠 AI-Powered Magento/Adobe Commerce Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-async--ready-green.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-Agents-blue)](https://www.langchain.com/)
[![License](https://img.shields.io/github/license/sivajik34/aifastcommerce)](./LICENSE)

An AI Assistant to interact with **Magento 2 / Adobe Commerce** via natural language — powered by **LangChain** and **FastAPI**.  
Ideal for automating product, order, customer, and inventory management workflows using AI agents.

---

## 🚀 Features

- ✅ Natural language interface for Magento 2 APIs
- ✅ Multi-agent LangChain architecture (Product, Order, Customer, etc.)
- ✅ Supervisor-of-supervisors agent router
- ✅ Human-in-the-loop fallback mechanism
- ✅ Product creation, order placement, cart handling, and more
- ✅ Built-in support for guest and logged-in customers
- ✅ FastAPI-based backend with Swagger docs
- ✅ REST endpoints for chat
  
---

## 📦 Tech Stack

- **AI/LLM**: LangChain, OpenAI (or other LLM providers)
- **API**: FastAPI
- **Database**: PostgreSQL (for chat history)
- **Magento API**: OAuth 1.0 REST API

## 🧰 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/sivajik34/aifastcommerce.git
cd aifastcommerce
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

.env file
MAGENTO_BASE_URL=http://magento.test
MAGENTO_CONSUMER_KEY=your_key
MAGENTO_CONSUMER_SECRET=your_secret
MAGENTO_ACCESS_TOKEN=your_token
MAGENTO_ACCESS_TOKEN_SECRET=your_token_secret

OPENAI_API_KEY=your_openai_key
POSTGRES_URL=your_postgres

uvicorn app.main:app --reload
