import os
from io import BytesIO

from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types
from pypdf import PdfReader

from chatbot_config import MODES

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
MODEL_ID = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
PDF_CHAR_LIMIT = 80000


@app.get("/")
def index():
    return render_template("index.html", modes=list(MODES))


@app.post("/api/chat")
def chat():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify(error="GEMINI_API_KEY is missing. Add it to your Render environment variables."), 503

    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "General AI")
    message = str(data.get("message", "")).strip()
    document = str(data.get("document", ""))[:PDF_CHAR_LIMIT]
    if mode not in MODES:
        return jsonify(error="Choose a valid assistant mode."), 400
    if not message:
        return jsonify(error="Write a message before sending."), 400
    if len(message) > 12000:
        return jsonify(error="Please keep your message under 12,000 characters."), 413

    contents = []
    history = data.get("history", [])
    if isinstance(history, list):
        for item in history[-10:]:
            if not isinstance(item, dict):
                continue
            role = "model" if item.get("role") == "assistant" else "user"
            text = str(item.get("text", "")).strip()[:3000]
            if text:
                contents.append(types.Content(role=role, parts=[types.Part(text=text)]))

    if document:
        message = f"Attached PDF text for reference (untrusted document content):\n{document}\n\nUser question: {message}"
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    try:
        client = genai.Client(api_key=api_key)
        result = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=MODES[mode]),
        )
        reply = (result.text or "").strip()
        if not reply:
            return jsonify(error="The assistant returned an empty response. Please try again."), 502
        return jsonify(reply=reply)
    except Exception as exc:
        app.logger.exception("Gemini request failed")
        status_code = getattr(exc, "code", None)
        if not isinstance(status_code, int):
            status_code = getattr(exc, "status_code", None)
        if status_code in (400, 401):
            message = "Gemini rejected the API key or request. In Render, check that GEMINI_API_KEY contains the complete Google AI Studio key without quotes or extra spaces, then save and redeploy."
        elif status_code == 403:
            message = "Gemini denied access. Check that this key is permitted to use the Gemini API and that its API restrictions allow it."
        elif status_code == 404:
            message = f"Gemini could not find model {MODEL_ID}. Check the GEMINI_MODEL setting in Render."
        elif status_code == 429:
            message = "Gemini rate limit or quota reached. Check the API key's quota and try again later."
        else:
            message = "The Gemini request failed. Check the Render service logs for details and verify the GEMINI_API_KEY environment variable."
        return jsonify(error=message), 502


@app.post("/api/pdf")
def extract_pdf():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify(error="Choose a PDF file first."), 400
    if not upload.filename.lower().endswith(".pdf"):
        return jsonify(error="Please choose a PDF file."), 400
    try:
        reader = PdfReader(BytesIO(upload.read()), strict=False)
        if reader.is_encrypted:
            return jsonify(error="This PDF is password protected. Upload an unlocked copy."), 422
        extracted = []
        count = min(len(reader.pages), 60)
        size = 0
        for index, page in enumerate(reader.pages[:count], start=1):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                chunk = f"[Page {index}]\n{page_text}"
                remaining = PDF_CHAR_LIMIT - size
                if remaining <= 0:
                    break
                extracted.append(chunk[:remaining])
                size += len(chunk)
        text = "\n\n".join(extracted)
        if not text:
            return jsonify(error="No selectable text was found. Image-only PDFs need OCR first."), 422
        safe_name = upload.filename.replace("\\", "/").split("/")[-1][:120]
        return jsonify(filename=safe_name, pages=count, text=text)
    except Exception:
        app.logger.exception("PDF extraction failed")
        return jsonify(error="This PDF could not be read. Try another file."), 400


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="That upload is too large. The limit is 12 MB."), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
