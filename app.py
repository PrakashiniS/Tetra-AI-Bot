import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Google Gemini client
import google.generativeai as genai
# -----------------------------
# Configuration / API keys
# -----------------------------
# Recommended: set GEMINI_API_KEY in environment for production.
# For quick local testing you can hardcode a default below (NOT recommended in real apps).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_API_Key")
# Configure the google generative client
genai.configure(api_key=GEMINI_API_KEY)

# MySQL connection string (adjust user/host/password/db as needed)
MYSQL_URL = os.getenv("MYSQL_URL", "mysql+pymysql://root@127.0.0.1:3306/chatdb")

# Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
# Replace this secret key for production and keep it secret (env var recommended)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_API_Key")

# Database engine
engine = create_engine(
    MYSQL_URL,
    future=True,
    pool_pre_ping=True,
    pool_recycle=280
)
SessionLocal = sessionmaker(bind=engine, future=True)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Utility helpers
# -----------------------------

def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, username, created_at FROM users WHERE id=:id"),
            {"id": uid}
        ).mappings().first()
        return row


def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

# -----------------------------
# Routes: auth + chat UI
# -----------------------------

@app.get("/register")
def register():
    return render_template("register.html")


@app.post("/register")
def register_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Username and password required", "error")
        return redirect(url_for("register"))

    pwd_hash = generate_password_hash(password)

    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users(username, password_hash) VALUES (:u, :p)"),
                {"u": username, "p": pwd_hash}
            )
        flash("Registration successful!", "success")
        return redirect(url_for("login"))
    except Exception as e:
        logger.exception("Registration failed")
        flash("Username already exists or DB error.", "error")
        return redirect(url_for("register"))


@app.get("/login")
def login():
    return render_template("login.html")


@app.post("/login")
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, username, password_hash FROM users WHERE username=:u"),
            {"u": username}
        ).mappings().first()

    if not row or not check_password_hash(row["password_hash"], password):
        flash("Invalid credentials", "error")
        return redirect(url_for("login"))

    session["user_id"] = row["id"]
    flash("Welcome!", "success")
    return redirect(url_for("chat"))


@app.get("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


@app.get("/")
@login_required
def chat():
    user = get_current_user()
    return render_template("chat.html", user=user)

# -----------------------------
# Gemini LLM integration
# -----------------------------

def call_llm(prompt: str) -> str:
    """
    Call Google Gemini via the `google-generativeai` client.
    Returns a string response. Any exception is logged and returned as an error string.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY missing")
        return "GEMINI_API_KEY missing from app.py"

    try:
        # Prefer a chat-capable Gemini model; change model name if needed.
        # If your installed client uses a different call pattern, adapt accordingly.
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Simple generation from a prompt
        response = model.generate_content(prompt)

        # Handle common response shapes from different SDK versions
        if hasattr(response, "text") and response.text:
            return response.text

        # Some versions return .content or nested structures
        if hasattr(response, "content") and response.content:
            return response.content

        # If the SDK returned a dict-like object
        try:
            if isinstance(response, dict):
                # try common keys
                for k in ("text", "content", "output", "result"):
                    if k in response and response[k]:
                        return str(response[k])
        except Exception:
            pass

        # Fallback: stringify
        return str(response)

    except Exception as e:
        # Log full stacktrace so you can see if any underlying HTTP request still hits OpenRouter
        logger.exception("Gemini LLM call failed")
        return f"Error contacting Gemini LLM: {e}"

# Alternative (commented) pattern if your client version exposes a different API:
# def call_llm(prompt: str) -> str:
#     try:
#         resp = genai.generate_text(model="text-bison-001", prompt=prompt)
#         return resp.text if hasattr(resp, "text") else str(resp)
#     except Exception as e:
#         logger.exception("Gemini generate_text failed")
#         return f"Error contacting Gemini LLM: {e}"

# -----------------------------
# Ask endpoint
# -----------------------------

@app.post("/ask")
@login_required
def ask():
    user = get_current_user()

    data = request.get_json(silent=True) or {}
    user_query = (data.get("query") or "").strip()

    if not user_query:
        return jsonify({"response": "Please type a question."})

    prompt = f"You are a helpful programming assistant.\nUser: {user_query}"

    answer = call_llm(prompt)

    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO messages(user_id, role, content) VALUES (:uid, 'user', :c)"),
                {"uid": user["id"], "c": user_query}
            )
            conn.execute(
                text("INSERT INTO messages(user_id, role, content) VALUES (:uid, 'assistant', :c)"),
                {"uid": user["id"], "c": answer}
            )
    except Exception:
        logger.exception("Failed to write messages to DB")

    return jsonify({"response": answer})


@app.get("/test123")
def test123():
    return "APP IS RUNNING ✅"


if __name__ == "__main__":
    # If you want the Flask dev server to be visible on the network, change host to '0.0.0.0'
    app.run(debug=True)
