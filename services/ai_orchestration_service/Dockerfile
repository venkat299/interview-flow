FROM python:3.12-slim

# Place the code under /code/ai_orchestration_service so that the package
# "ai_orchestration_service" is importable without extra path tweaks.
WORKDIR /code
ENV PYTHONPATH=/code


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

COPY . /code/ai_orchestration_service

CMD ["uvicorn", "ai_orchestration_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
