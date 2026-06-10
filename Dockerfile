#docker official python image as parent image
FROM python:3.12-slim

# Prevent python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1
# Set the working directory in the container
WORKDIR /app
# Copy the requirements file into the container
COPY requirements.txt .
# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the application code into the container
COPY . .
# Expose the port that the application will run on
EXPOSE 8000
# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# To build the Docker image, run the following command in the terminal:
# docker build -t devops-ready-app .
# To run the Docker container, use the following command:
# docker run -d -p 8000:8000 --env-file .env devops-ready-app


