import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import requests

OPENROUTER_API_KEY = "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"
MYSQL_URL = "mysql+pymysql://root@127.0.0.1:3306/chatdb"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "6b2ba3b17dba0c01e37473c7777895e5ecf92007f8107801ce6a73aed1aec93a"

engine = create_engine(
    MYSQL_URL,
    future=True,
    pool_pre_ping=True,
    pool_recycle=280
)
SessionLocal = sessionmaker(bind=engine, future=True)

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
    except Exception:
        flash("Username already exists.", "error")
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

def call_llm(prompt: str) -> str:

    if not OPENROUTER_API_KEY:
        return "OPENROUTER_API_KEY missing from app.py"

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {

        "model": "meta-llama/llama-4-scout:free",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)

        print("LLM Status Code:", resp.status_code)
        print("LLM Response:", resp.text)

        resp.raise_for_status()

        return resp.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Error contacting LLM: {e}"

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
        pass

    return jsonify({"response": answer})

@app.get("/test123")
def test123():
    return "APP IS RUNNING ✅"

if __name__ == "__main__":
    app.run(debug=True)
