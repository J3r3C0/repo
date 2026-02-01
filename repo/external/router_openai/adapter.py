from __future__ import annotations
import os, httpx
from fastapi import FastAPI, Body, HTTPException

app = FastAPI(title="Sheratan Router (OpenAI)")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/models")
def models():
    allow = os.getenv("OPENAI_MODEL_ALLOWLIST", "").strip()
    if allow:
        return [m.strip() for m in allow.split(",") if m.strip()]
    return ["gpt-4o-mini"]

@app.post("/complete")
def complete(body: dict = Body(...)):
    if not OPENAI_API_KEY:
        raise HTTPException(500, "missing OPENAI_API_KEY")
    prompt = str(body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(422, "prompt required")
    max_tokens = int(body.get("max_tokens") or 128)
    model = body.get("model") or (models()[0])

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    try:
        url = f"{OPENAI_BASE_URL}/v1/chat/completions"
        r = httpx.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        return {"model": model, "output": text}
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500] if e.response is not None else str(e)
        raise HTTPException(e.response.status_code if e.response else 502, f"openai error: {detail}")
    except Exception as e:
        raise HTTPException(500, f"adapter error: {e}")
