FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY app ./app

# Install dependencies
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
