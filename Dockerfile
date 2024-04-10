FROM python:3.9-slim

# Install system dependencies required for ZBar and any other needs
RUN apt-get update && apt-get install -y libzbar0 && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Command to run the application
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:$PORT", "qr_food_app.main:app"]
#CMD gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT qr_food_app.main:app