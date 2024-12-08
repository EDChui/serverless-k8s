FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose the app port
EXPOSE 8082

# Run the Flask app
CMD ["python", "-u", "controller.py"]
