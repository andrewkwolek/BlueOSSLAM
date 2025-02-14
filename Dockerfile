FROM python:3.11-slim

# Install system dependencies, including 'patch' and build tools for compiling packages like opencv-python
RUN apt-get update && \
    apt-get install -y patch build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy the app directory and pyproject.toml
COPY app /app

# Install Python dependencies from the pyproject.toml
RUN python -m pip install --upgrade pip && \
    python -m pip install /app --extra-index-url https://www.piwheels.org/simple

# Create directories as needed
RUN mkdir -p /app/slam_data

# Expose the necessary port
EXPOSE 9050

# Set metadata labels
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

# Define entrypoint to run the app
ENTRYPOINT cd /app && python main.py
