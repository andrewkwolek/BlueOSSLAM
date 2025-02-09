FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    make \
    python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY app /app
RUN python -m pip install /app --extra-index-url https://www.piwheels.org/simple

RUN mkdir -p /app/slam_data

EXPOSE 9050

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
ENTRYPOINT cd /app && python main.py