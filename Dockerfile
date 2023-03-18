# Base image
FROM python:3.10-slim-buster

# Install Graphviz
RUN apt-get update && apt-get install -y graphviz

# Set the working directory
WORKDIR /app

# Copy the Flask app code to the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the default Flask port
EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENVIRONMENT=production
ENV FLASK_DEBUG=0

# Start the Flask app
#CMD ["python", "app.py"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
