"""
ABFRL Retail AI Agent — FastAPI Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file (before any agent imports)
load_dotenv()

from models.schemas import ChatRequest, ChatResponse, ReservationRequest, ReservationResponse
from agents import orchestrator
import uuid
import random
import string
from datetime import datetime, timezone

# In-memory session storage (sufficient for demo)
sessions: dict = {}


class RetailAIError:
    NO_RESULTS = "NO_RESULTS"
    INTENT_UNCLEAR = "INTENT_UNCLEAR"
    RETRIEVAL_FAILED = "RETRIEVAL_FAILED"
    BUDGET_TOO_LOW = "BUDGET_TOO_LOW"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


def build_error_response(code: str, session_id: str | None, intent: str = "error") -> dict:
    """Always returns a structurally valid ChatResponse dict."""
    return {
        "session_id": session_id or "",
        "intent": intent,
        "message": "",
        "products": [],
        "discount_info": None,
        "metadata": None,
        "error": code,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once at startup:
    - Indexes products into Qdrant Cloud (skips if already indexed)
    """
    print("[main] Starting up — running product indexer...")
    from rag import indexer
    indexer.run()  # skips if already indexed
    print("[main] Startup complete!")
    yield
    print("[main] Shutting down...")


app = FastAPI(
    title="ABFRL Retail AI Agent",
    description=(
        "Agentic Retail AI System for ABFRL. "
        "Multi-agent pipeline: NLU → Orchestrator → "
        "Recommendation/Inventory/Loyalty agents."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for teammates' React Native app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint — basic server info."""
    return {
        "name": "ABFRL Retail AI Agent",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "chat": "POST /chat",
            "docs": "/docs",
        },
    }


@app.get("/health")
def health():
    """Health check endpoint for Render."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.

    Accepts a user message and routes it through the multi-agent pipeline:
    1. NLU Agent extracts intent + entities
    2. Orchestrator routes to appropriate agent(s)
    3. Response assembled and returned

    Request body:
        - message: User's natural language query
        - user_id: Customer ID (maps to customers.json)
        - session_id: Optional session ID for conversation continuity

    Returns ChatResponse with products, discount info, etc.
    """
    # Create or retrieve session
    session_id = request.session_id or str(uuid.uuid4())
    session = sessions.setdefault(session_id, {"history": []})

    try:
        # Run the orchestrator pipeline
        result = orchestrator.run(
            message=request.message,
            user_id=request.user_id,
            session=session,
        )

        if result.get("error"):
            return build_error_response(RetailAIError.SERVICE_UNAVAILABLE, session_id)

        # Recommendation intent returned no products
        intent = result.get("intent") or "unknown"
        products = result.get("products") or []
        if intent == "recommendation" and not products:
            budget_max = None
            prior_intent = session.get("last_resolved_intent", {})
            if prior_intent.get("budget_max"):
                budget_max = prior_intent.get("budget_max")
            if budget_max and budget_max < 2000:
                return build_error_response(RetailAIError.BUDGET_TOO_LOW, session_id)
            return build_error_response(RetailAIError.NO_RESULTS, session_id)

        # Guarantee required fields are always present non-None strings
        result["session_id"] = session_id
        result["message"] = result.get("message") or ""
        result["intent"] = intent
        result["products"] = products
        result["discount_info"] = result.get("discount_info", None)
        result["metadata"] = result.get("metadata", None)
        result["error"] = None

        # Store in session history
        sessions[session_id]["history"].append({
            "user": request.message,
            "agent": result["message"],
        })

        return ChatResponse(**result)

    except ValueError:
        return build_error_response(RetailAIError.INTENT_UNCLEAR, session_id)
    except Exception as exc:
        # Outer catch-all — unhandled exceptions from the pipeline
        print(f"[chat] Unhandled exception for session {session_id}: {exc}")
        return build_error_response(RetailAIError.SERVICE_UNAVAILABLE, session_id)


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------

def _generate_reservation_id() -> str:
    """Generate a unique reservation ID in the format RES_<8 random uppercase chars>."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"RES_{suffix}"


@app.post("/reservations", response_model=ReservationResponse)
async def create_reservation(request: ReservationRequest):
    """
    Create a product reservation.

    Generates a unique reservation ID, persists the record to Firebase
    Realtime Database at ``reservations/<reservation_id>``, and returns
    the reservation details plus a QR payload.

    Firebase writes are best-effort: if the write fails the endpoint
    still returns a successful response so the client is never blocked.
    """
    try:
        reservation_id = _generate_reservation_id()
        created_at = datetime.now(timezone.utc).isoformat()

        firebase_record = {
            "reservation_id": reservation_id,
            "user_id": request.user_id,
            "product_id": request.product_id,
            "status": "waiting",
            "room": None,
            "created_at": created_at,
        }

        # --- Firebase write (best-effort) ---
        try:
            from agents.firebase_client import get_ref, FIREBASE_AVAILABLE
            if FIREBASE_AVAILABLE:
                ref = get_ref(f"reservations/{reservation_id}")
                if ref is not None:
                    ref.set(firebase_record)
                    print(f"[reservations] Written to Firebase: {reservation_id}")
                else:
                    print(f"[reservations] Firebase ref returned None for {reservation_id}")
            else:
                print("[reservations] Firebase unavailable — skipping DB write.")
        except Exception as fb_exc:
            # Log and continue — do NOT let Firebase crash the endpoint
            print(f"[reservations] Firebase write error for {reservation_id}: {fb_exc}")

        return ReservationResponse(
            reservation_id=reservation_id,
            status="waiting",
            qr_payload=reservation_id,
        )

    except Exception as exc:
        print(f"[reservations] Unhandled error: {exc}")
        raise HTTPException(status_code=500, detail="Reservation service unavailable")


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    """Quick lookup endpoint for customer info (useful for debugging)."""
    from agents.loyalty_agent import find_customer
    customer = find_customer(customer_id)
    if customer:
        return customer
    return {"error": f"Customer '{customer_id}' not found"}


@app.get("/inventory/{sku_id}")
def get_inventory(sku_id: str):
    """Quick lookup endpoint for inventory (useful for debugging)."""
    from agents.inventory_agent import run as check_inventory
    return check_inventory(sku_id)
