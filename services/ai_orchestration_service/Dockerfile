FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app /app
# Application code is copied directly into /app, so the FastAPI instance
# lives in main.py at the root of the working directory. The previous
# command attempted to import ``app.main`` which looked for /app/app
# and failed with ``ModuleNotFoundError``. Import ``main:app`` instead.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
