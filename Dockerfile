# Container image for the EdgeRoute API.
# Build and run it with `docker compose up --build` (see docker-compose.yaml).

# Base image: a minimal Debian with Python preinstalled.
FROM python:3.10-slim

# Copy the project into /app inside the image and install its dependencies.
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Document the port the server listens on, then start it. 0.0.0.0 accepts connections
# from outside the container, not only from inside it.
EXPOSE 80
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
