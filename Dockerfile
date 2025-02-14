FROM python:3.9-slim-bullseye

RUN apt-get update && apt-get install -y \
    libopus0 \
    libxcursor1 \
    libx264-160 \
    libchromaprint1 \
    libwayland-cursor0 \
    libvorbis0a \
    libxvidcore4 \
    libvpx6 libgme0 \
    libtheora0 \
    libxcb-shm0 \
    libcairo-gobject2 \
    libudfread0 \
    libtwolame0 \
    libdrm2 \
    ocl-icd-libopencl1 \
    libopenjp2-7 \
    libthai0 \
    libwayland-egl1 \
    libmp3lame0 \
    libgraphite2-3 \
    libcairo2 \
    libwebpmux3 \
    libzmq5 \
    libva-x11-2 \
    libvdpau1 \
    libopenmpt0 \
    libepoxy0 \
    libswscale5 \
    libpangoft2-1.0-0 \
    libwayland-client0 \
    libxi6 \
    libxfixes3 \
    libharfbuzz0b \
    libogg0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libspeex1 \
    libsoxr0 \
    libswresample3 \
    libwebpdemux2 \
    libxcb-render0 \
    libsodium23 \
    libvorbisfile3 \
    libavutil56 \
    libdatrie1 \
    libgdk-pixbuf-2.0-0 \
    libshine3 \
    libxrandr2 \
    libsrt1.4-gnutls \
    librsvg2-2 \
    libx265-192 \
    libxcomposite1 \
    libva2 libnorm1 \
    librabbitmq4 \
    libpango-1.0-0 \
    libcodec2-0.9 \
    libgsm1 \
    libxrender1 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libva-drm2 \
    libavformat58 \
    libatlas3-base \
    libsnappy1v5 \
    libpgm-5.3-0 \
    libzvbi0 \
    libxdamage1 \
    libbluray2 \
    libavcodec58 \
    libwavpack1 \
    libmpg123-0 \
    libgfortran5 \
    libgtk-3-0 \
    libaom0 \
    libpixman-1-0 \
    libxkbcommon0 \
    libssh-gcrypt-4 \
    libdav1d4 \
    libopenblas0-pthread \
    libvorbisenc2 \
    libxinerama1 \
    && rm -rf /var/lib/apt/lists/*

COPY app /app
RUN python -m pip install /app --extra-index-url https://www.piwheels.org/simple

RUN mkdir -p /app/slam_data

EXPOSE 9050
EXPOSE 14550/udp

LABEL version="1.0.1"
LABEL permissions='{\
  "ExposedPorts": {\
    "9050/tcp": {}\
    "14550/udp: {}"\
  },\
  "HostConfig": {\
  "Binds":["/usr/blueos/extensions/blueos-slam:/app/logs"],\
    "PortBindings": {\
      "9050/tcp": [\
        {\
          "HostPort": "9050"\
        }\
      ]\
      "14550/udp": [\
        {\
          "HostPort": "14550"\
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