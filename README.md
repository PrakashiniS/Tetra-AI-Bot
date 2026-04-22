# Chatbot (MySQL root, no password example)

This package is configured to use MySQL only. It is prefilled to use `root` with no password on port `3306`.

## Steps

1. Import `schema.sql` into phpMyAdmin to create `chatdb` and the `users` and `messages` tables.
2. Copy `.env.example` → `.env` if you want to change settings; by default it points to `root` with no password.
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `python app.py`
5. Open http://127.0.0.1:5000 and register/login.

> Security note: This configuration (root with no password) is only for local testing. Do not use in production.
