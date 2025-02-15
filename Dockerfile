FROM python:3.9-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

# Setup to prevent libc-bin triggers on arm64
RUN if [ "$(dpkg --print-architecture)" = "arm64" ]; then \
        mkdir -p /var/lib/dpkg/info && \
        touch /var/lib/dpkg/info/libc-bin.list && \
        touch /var/lib/dpkg/info/libc-bin.postinst && \
        chmod +x /var/lib/dpkg/info/libc-bin.postinst && \
        echo "exit 0" > /var/lib/dpkg/info/libc-bin.postinst; \
    fi && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gcc \
        libcairo2-dev \
        pkg-config \
        gobject-introspection \
        libgirepository1.0-dev \
        python3-gst-1.0 \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-libav && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app /app
RUN python -m pip install /app --extra-index-url https://www.piwheels.org/simple

RUN mkdir -p /app/slam_data

EXPOSE 9050
EXPOSE 14550/udp
EXPOSE 5600/udp
EXPOSE 9092/udp

LABEL version="1.0.1"
LABEL permissions='{\
  "ExposedPorts": {\
    "9050/tcp": {},\
    "14550/udp": {},\
    "5600/udp": {},\
    "9092/udp: {}"\
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
      ],\
      "9092/udp": [\
        {\
          "HostPort": "9092"\
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
