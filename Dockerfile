# Stage 1: Builder - Install dependencies
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /code

# Set up a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final - Create the production image
FROM python:3.12-slim

# Set working directory
WORKDIR /code

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code
COPY ./app /code/app

# Set the path to use the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# Uvicorn will run on host 0.0.0.0 to be accessible from outside the container.
# The --port 8000 matches the EXPOSE instruction.
# app.main:app refers to the 'app' instance in the 'app/main.py' file.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
