FROM python:3.12-slim

WORKDIR /app

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

# Application code is copied directly into /app, so the FastAPI instance
# lives in main.py at the root of the working directory. The previous
# command attempted to import ``app.main`` which looked for /app/app
# and failed with ``ModuleNotFoundError``. Import ``main:app`` instead.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
