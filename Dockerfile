# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# System dependencies can be added here if needed in the future.

# Copy the requirements file into the container at /app
# We will create this file in a later step
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download Spacy models for Presidio (English and Italian)
RUN python -m spacy download en_core_web_lg
RUN python -m spacy download it_core_news_lg

# Copy the rest of the application code into the container at /app
COPY . .

# The command to run the application is specified in docker-compose.yml
# This keeps the container running for interactive development
CMD ["tail", "-f", "/dev/null"]
