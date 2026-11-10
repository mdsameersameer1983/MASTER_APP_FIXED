# MASTER_AI

An all-in-one Gemini chatbot dashboard with one conversation and 10 specialist modes plus General AI. Includes PDF text extraction and document question answering.

## Render deployment

Create a Render Web Service from this project, or use `render.yaml` as a Blueprint. The build and start settings are configured there. In the Render service's Environment settings, add `GEMINI_API_KEY` with your Google AI Studio API key. The key is read from the Render environment; it is not stored in this project. `GEMINI_MODEL` is optional and defaults to `gemini-3.8-flash`.

The Render build command installs the dependencies with Python, and the start command runs Gunicorn through that same Python environment to serve Flask's WSGI app directly. Keep Render's Root Directory blank so `app.py` and `requirements.txt` are found at the project root.

If the app reports an API key error, confirm the Render variable is named exactly `GEMINI_API_KEY` and contains the complete key from Google AI Studio without quote marks or added spaces. Save the environment change and redeploy the service. Do not share the key in chat or commit it to source control. Error messages distinguish invalid credentials or requests, access restrictions, model selection, and quota limits without exposing the key.

## PDF support

PDF upload accepts files up to 12 MB and extracts text from at most 60 pages. Scanned image-only PDFs need OCR before upload. Extracted text stays in the current browser session and is submitted with questions while the file is selected.
