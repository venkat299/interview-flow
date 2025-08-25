FROM python:3.12-slim

# Place the code under /code/interview_services so that the package
# "interview_services" is importable without extra path tweaks.
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
RUN rm /tmp/requirements.txt /tmp/pyproject.toml

COPY . /code/interview_services

CMD ["uvicorn", "interview_services.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

