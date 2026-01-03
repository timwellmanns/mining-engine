FROM python:3.11-slim

WORKDIR /app

# Set Python to unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Copy project files
COPY pyproject.toml .
COPY app ./app

# Install dependencies
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Run the application (using PORT env var from Render, fallback to 8000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
