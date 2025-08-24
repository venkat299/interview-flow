FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app /app
# Like the AI orchestration service, the source files are placed directly
# in /app, so the FastAPI application resides in main.py. Referencing
# ``app.main`` results in a missing module error. Import ``main:app``
# to start the server correctly.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
