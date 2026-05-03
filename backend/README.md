# 🛍️ ABFRL Retail AI Agent — ML Backend API

> A Machine Learning–powered backend API that recommends fashion products using natural language understanding, sentence embeddings, and semantic search.

---

## 📌 Overview

This project is the **ML backend** of a Retail AI system built for **ABFRL (Aditya Birla Fashion & Retail Limited)**. A user types something like *"Show me red kurtas for Diwali under ₹3000"* and the API understands the intent, searches through a product catalog using AI-powered similarity matching, and returns the most relevant products — complete with personalized discount info.

The API is built with **FastAPI**, uses **sentence-transformers** (MiniLM) to convert text into embeddings, stores product vectors in **Qdrant** (a vector database), and leverages **Groq LLM** (Llama 3.1) for intent extraction and natural language generation.

---

## 👤 My Role in the Team

This is a team project. The responsibilities are split as follows:

| Area | Handled By |
|------|------------|
| **ML Backend API** (this repo) | **Me** ✅ |
| Frontend (React Native App) | Teammates |
| UI/UX Design | Teammates |
| System Integration | Teammates |

### What I Built

- Designed and implemented the **complete ML pipeline** (embedding → search → rerank → response)
- Built a **REST API** using FastAPI with structured endpoints for the frontend team
- Integrated **sentence-transformers** (all-MiniLM-L6-v2) for generating text embeddings
- Set up **Qdrant Cloud** as the vector database for semantic product search
- Used **Groq API** (Llama 3.1 8B) for natural language understanding and response generation
- Deployed the API on **Render** (free tier, production-ready)
- Tested all endpoints using **Postman** and wrote automated tests with **pytest**

---

## 🔄 System Flow

Here is how a user request flows through the system:

```
User (React Native App)
        │
        ▼
   POST /chat  ──────────────►  FastAPI Server (Render)
                                      │
                                      ▼
                              ┌───────────────┐
                              │   NLU Agent    │  ← Extracts intent & entities
                              │  (Groq LLM)   │    using Llama 3.1
                              └───────┬───────┘
                                      │
                                      ▼
                              ┌───────────────┐
                              │  Orchestrator  │  ← Routes to the right agent
                              └───────┬───────┘
                                      │
                    ┌─────────────────┼──────────────────┐
                    ▼                 ▼                   ▼
           ┌──────────────┐  ┌──────────────┐   ┌──────────────┐
           │ Recommend.   │  │  Inventory   │   │   Loyalty    │
           │   Agent      │  │   Agent      │   │   Agent      │
           │ (Embeddings  │  │ (Stock data) │   │ (Discounts)  │
           │  + Qdrant)   │  │              │   │              │
           └──────┬───────┘  └──────────────┘   └──────────────┘
                  │
                  ▼
           JSON Response  ───────────────────►  Frontend App
```

---

## 🧠 ML Pipeline (Step-by-Step)

This is the core of the project — how the recommendation engine works:

### Step 1: Receive User Query
The user sends a natural language message like:
> *"Show me blue kurtas for a wedding under ₹5000"*

### Step 2: Intent & Entity Extraction (NLU)
The **NLU Agent** sends the message to **Groq's Llama 3.1 8B** model, which returns structured JSON:
```json
{
  "intent": "recommendation",
  "entities": {
    "category": "ethnic_wear",
    "subcategory": "kurta",
    "color": "blue",
    "budget_max": 5000,
    "occasion": "wedding"
  }
}
```

### Step 3: Build Search Query & Generate Embedding
The extracted entities are combined into a search string (e.g., `"blue wedding kurta under 5000"`), which is then converted into a **384-dimensional vector** using the `all-MiniLM-L6-v2` model:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
query_vector = model.encode("blue wedding kurta under 5000")
# → [0.023, -0.041, 0.078, ...]  (384 numbers)
```

### Step 4: Semantic Search in Qdrant
The query vector is compared against all pre-indexed product vectors in **Qdrant Cloud** using **cosine similarity**. The top 10 most similar products are retrieved.

### Step 5: Filtering & Reranking
The raw search results are refined:
- ❌ **Out-of-stock** products are removed
- 📊 A **composite reranking score** is computed:
  - 40% — Semantic similarity score
  - 30% — Budget fit (how close the price is to the user's budget)
  - 20% — Occasion match
  - 10% — Color match

### Step 6: Personalized Response
The top 5 products are returned, each with:
- An LLM-generated **"Why this is perfect for you"** message
- **Loyalty-based discounted pricing** (if the customer has a tier discount)

---

## 🛠️ Technologies Used

| Technology | Purpose |
|------------|---------|
| **FastAPI** | Web framework for building the REST API |
| **sentence-transformers** (MiniLM) | Converting text into 384-dim embeddings |
| **Qdrant Cloud** | Vector database for semantic similarity search |
| **Groq API** (Llama 3.1 8B) | LLM for intent extraction and text generation |
| **LangChain Core** | Foundational utilities for agent design |
| **Pydantic** | Request/response data validation |
| **Uvicorn** | ASGI server to run FastAPI |
| **Render** | Cloud deployment (free tier) |
| **Postman** | API testing and endpoint validation |
| **pytest** | Automated test suite |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Returns basic server info and available endpoints |
| `GET` | `/health` | Health check (used by Render for uptime monitoring) |
| `POST` | `/chat` | **Main endpoint** — accepts a user message and returns product recommendations |
| `GET` | `/customers/{customer_id}` | Look up customer info (loyalty tier, points) |
| `GET` | `/inventory/{sku_id}` | Check stock availability for a specific product |
| `GET` | `/docs` | Auto-generated Swagger UI for interactive API testing |

### Example: `/chat` Request

```bash
POST /chat
Content-Type: application/json

{
  "message": "Show me red kurtas for Diwali under 3000",
  "user_id": "customer_001"
}
```

### Example: `/chat` Response

```json
{
  "session_id": "a1b2c3d4-...",
  "intent": "recommendation",
  "message": "Here are 5 ethnic wear picks perfect for you! 15% Gold Member Discount applied.",
  "products": [
    {
      "id": "SKU_003",
      "name": "Festive Silk Kurta",
      "price": 2799,
      "discounted_price": 2379.15,
      "colors": ["Red", "Maroon"],
      "occasion_tags": ["festive", "wedding"],
      "why_for_you": "Perfect red silk kurta for your Diwali celebration at a great price.",
      "in_stock": true,
      "rating": 4.5
    }
  ],
  "discount_info": "15% Gold Member Discount"
}
```

---

## 📂 Project Structure

```
retail-ai-agent/
│
├── main.py                   # FastAPI app entry point, endpoint definitions
│
├── agents/                   # All agent modules
│   ├── nlu_agent.py          # Intent & entity extraction (Groq LLM)
│   ├── orchestrator.py       # Routes intents to the correct agent
│   ├── recommendation_agent.py  # Embedding search + reranking pipeline
│   ├── inventory_agent.py    # Stock lookup from inventory data
│   └── loyalty_agent.py      # Customer tier & discount calculation
│
├── rag/                      # Retrieval-Augmented Generation modules
│   ├── embedder.py           # Sentence-transformer model (MiniLM)
│   ├── indexer.py            # One-time product indexing into Qdrant
│   └── vectorstore.py        # Qdrant client wrapper (search, upsert)
│
├── models/
│   └── schemas.py            # Pydantic models (ChatRequest, ChatResponse)
│
├── data/                     # Static JSON datasets
│   ├── products.json         # Product catalog (~50 ABFRL products)
│   ├── inventory.json        # Stock quantities per store
│   ├── customers.json        # Customer profiles & loyalty tiers
│   └── promotions.json       # Discount rules & coupon codes
│
├── tests/                    # Automated tests
│   ├── test_api.py           # Endpoint tests
│   ├── test_nlu.py           # NLU agent tests
│   └── test_recommendation.py  # Recommendation pipeline tests
│
├── requirements.txt          # Python dependencies
├── render.yaml               # Render deployment configuration
├── .env.example              # Environment variable template
└── .gitignore
```

---

## 🚀 Deployment

The API is deployed on **[Render](https://render.com/)** using the free tier.

**How it works:**
1. Render detects the `render.yaml` configuration file
2. It installs PyTorch (CPU-only build to save memory) and all dependencies
3. Starts the server with `uvicorn main:app`
4. On first startup, the app automatically indexes all products into Qdrant Cloud
5. A `/health` endpoint is used for Render's uptime monitoring

**Environment variables** (configured in Render dashboard):
| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | API key for Groq LLM access |
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `ENVIRONMENT` | Set to `production` on Render |

---

## ✅ Key Features

- 🔍 **Semantic Search** — Finds products by *meaning*, not just keyword matching (e.g., "something elegant for a party" works)
- 🤖 **Natural Language Understanding** — Users can type in plain English/Hinglish; the LLM extracts structured intent and entities
- 📊 **Smart Reranking** — Results aren't just based on similarity; budget fit, occasion, and color preferences are factored in
- 💰 **Loyalty-Aware Pricing** — Discounts are automatically applied based on the customer's tier (Gold, Silver, Platinum)
- 📦 **Real-Time Stock Filtering** — Out-of-stock items are removed before showing results
- 💬 **Personalized Explanations** — Each recommendation includes an LLM-generated "why this is perfect for you" message
- 🧪 **Tested Endpoints** — Automated tests with pytest + manual testing with Postman
- ☁️ **Cloud Deployed** — Live on Render, ready for frontend integration

---

## 🔮 Future Improvements

- **Conversation Memory** — Store chat history in a database so the assistant remembers past preferences across sessions
- **Image-Based Search** — Allow users to upload a photo and find visually similar products using image embeddings
- **User Behavior Learning** — Track clicks and purchases to improve recommendations over time using collaborative filtering

---

## 🏃 Running Locally

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/retail-ai-agent.git
cd retail-ai-agent

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install torch==2.3.0+cpu --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 4. Set up environment variables
copy .env.example .env       # Then fill in your API keys

# 5. Start the server
uvicorn main:app --reload

# 6. Open in browser
# API docs → http://localhost:8000/docs
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

<p align="center">
  Built with ❤️ as a Final Year Project
</p>
