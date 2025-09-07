FROM python:3.12-slim

# Place the repository under /code so all modular services are importable.
WORKDIR /code

# Allow every helper service under /code/services to be imported without an
# install step.  This lets the orchestrator reach the interviewer, monitor,
# scoring engine, and other modules in the same container.
ENV PYTHONPATH=/code/services


COPY pyproject.toml /tmp/pyproject.toml
RUN python - <<'PY'
import tomllib, pathlib
with open('/tmp/pyproject.toml', 'rb') as f:
    deps = tomllib.load(f)['project']['dependencies']
pathlib.Path('/tmp/requirements.txt').write_text('\n'.join(deps))
PY
RUN pip install --no-cache-dir -r /tmp/requirements.txt
# Install a Unicode TrueType font (DejaVu) for PDF generation
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN rm /tmp/requirements.txt /tmp/pyproject.toml

# Copy the entire source tree so orchestrator and helper services are available
COPY . /code

# Expose the API port; the default command launches the API service
# but any helper can be run by overriding CMD.
EXPOSE 8000
CMD ["uvicorn", "api_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
