# In interview-flow-dev/services/ai_orchestration_service/Dockerfile

FROM python:3.12-slim
WORKDIR /app

# This will now copy the pyproject.toml from the service's directory
COPY pyproject.toml .

# Install the project and its dependencies
RUN pip install --no-cache-dir .

# Copy the service's application code
COPY app /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]