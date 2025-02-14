FROM python:3.11-slim

RUN apt-get update && \
        apt-get install -y --no-install-recommends \
        build-essential cmake git pkg-config libgtk-3-dev \
        libavcodec-dev libavformat-dev libswscale-dev libv4l-dev \
        libxvidcore-dev libx264-dev libjpeg-dev libpng-dev libtiff-dev gfortran \
        python3-dev python3-numpy

    ARG OPENCV_VERSION=4.9.0
    ARG OPENCV_CONTRIB_VERSION=4.9.0

    RUN git clone --depth 1 --branch ${OPENCV_VERSION} https://github.com/opencv/opencv.git && \
        git clone --depth 1 --branch ${OPENCV_CONTRIB_VERSION} https://github.com/opencv/opencv_contrib.git && \
        mkdir -p /opencv/build && cd /opencv/build

    RUN cmake -D CMAKE_BUILD_TYPE=RELEASE \
        -D CMAKE_INSTALL_PREFIX=/usr/local \
        -D INSTALL_PYTHON_EXAMPLES=OFF \
        -D INSTALL_C_EXAMPLES=OFF \
        -D OPENCV_ENABLE_NONFREE=ON \
        -D OPENCV_EXTRA_MODULES_PATH=/opencv/opencv_contrib/modules \
        -D BUILD_EXAMPLES=OFF .. && \
        make -j$(nproc) && \
        make install && \
        ldconfig

WORKDIR /

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