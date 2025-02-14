# Use the official Python 3.12 slim image as the base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for OpenCV and other packages
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install poetry to manage dependencies
RUN pip install --no-cache-dir poetry

# Copy the pyproject.toml into the container
COPY pyproject.toml /app/

# Install the Python dependencies from pyproject.toml
RUN poetry install --no-dev

# Copy the application code into the container (if any)
COPY . /app

# Set the command to run your application (if needed)
CMD ["python", "main.py"]

# Expose the required port for the application
EXPOSE 9050

# Add metadata labels to the Docker image
LABEL version="1.0.1"
LABEL permissions='{\
  "ExposedPorts": {\
    "9050/tcp": {}\
  },\
  "HostConfig": {\
  "Binds":["/usr/blueos/extensions/blueos-slam:/app/logs"],\
    "PortBindings": {\
      "9050/tcp": [\
        {\
          "HostPort": "9050"\
        }\
      ]\
    }\
  }\
}'
LABEL authors='[\
    {\
        "name": "Andrew Kwolek",\
        "email": "andrewkwolek2025@u.northwestern.edu"\
    }\
]'
LABEL company='{\
        "about": "",\
        "name": "Northwestern University",\
    }'
LABEL requirements="core >= 1.1"

