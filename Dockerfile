FROM --platform=$TARGETPLATFORM python:3.9-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libcairo2-dev \
        pkg-config \
        gobject-introspection \
        libgirepository1.0-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY app /app
RUN python -m pip install /app --extra-index-url https://www.piwheels.org/simple

RUN mkdir -p /app/slam_data

EXPOSE 9050
EXPOSE 14550/udp
EXPOSE 5600/udp

LABEL version="1.0.1"
LABEL permissions='{\
  "ExposedPorts": {\
    "9050/tcp": {},\
    "14550/udp": {},\
    "5600/udp": {}\
  },\
  "HostConfig": {\
    "Binds":["/usr/blueos/extensions/blueos-slam:/app/logs"],\
    "PortBindings": {\
      "9050/tcp": [\
        {\
          "HostPort": "9050"\
        }\
      ],\
      "14550/udp": [\
        {\
          "HostPort": "14550"\
        }\
      ],\
      "5600/udp": [\
        {\
          "HostPort": "5600"\
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