FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app:/app/..

# Install Python dependencies defined for this service

COPY pyproject.toml /tmp/pyproject.toml
RUN python - <<'PY'
import tomllib, pathlib
deps = tomllib.load(open('/tmp/pyproject.toml', 'rb'))['project']['dependencies']
pathlib.Path('/tmp/requirements.txt').write_text('\n'.join(deps))
PY

RUN pip install --no-cache-dir -r /tmp/requirements.txt
RUN rm /tmp/requirements.txt /tmp/pyproject.toml

# Copy the service application code into the image
COPY app /app


# Like the AI orchestration service, the source files are placed directly
# in /app, so the FastAPI application resides in main.py. Referencing
# ``app.main`` results in a missing module error. Import ``main:app``
# to start the server correctly.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
