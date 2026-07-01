ARG IMAGE=python
ARG TAG=3.13

FROM ${IMAGE}:${TAG} AS base

SHELL [ "/bin/bash", "-c" ]

ENV PATH=/opt/orchidarium/.local/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG TINI_VERSION=0.19.0 \
    ARCHITECTURE=arm64

# https://github.com/opencontainers/image-spec/blob/main/annotations.md#pre-defined-annotation-keys
LABEL org.opencontainers.image.description="© Emma Doyle 2026"
LABEL org.opencontainers.image.licenses="GPLv3"
LABEL org.opencontainers.image.authors="Emma Doyle <emma.ann.doyle@gmail.com>"
LABEL org.opencontainers.image.documentatio="https://github.com/tigerlilyplants/orchidarium"

USER root

RUN apt update \
    && apt install -y --no-install-recommends \
        libdbus-1-3 \
        libegl1 \
        libfontconfig1 \
        libgl1 \
        libglib2.0-0 \
        libhidapi-dev \
        libice6 \
        libopengl0 \
        libsm6 \
        libx11-6 \
        libx11-xcb1 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-render0 \
        libxcb-shape0 \
        libxcb-shm0 \
        libxcb-sync1 \
        libxcb-util1 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
        libxcb-xkb1 \
        libxcb1 \
        libxi6 \
        libxkbcommon-x11-0 \
        libxkbcommon0 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

ENV TINI_VERSION=${TINI_VERSION}
# https://github.com/krallin/tini
RUN curl -sL https://github.com/krallin/tini/releases/download/v"${TINI_VERSION}"/tini-"${ARCHITECTURE}" -o /tini \
    && chmod +x /tini

# Add 'orchidarium' user and group.
RUN groupadd orchidarium \
    && useradd -rm -d /opt/orchidarium -s /bin/bash -g orchidarium -u 10001 orchidarium

WORKDIR /opt/orchidarium

# Ensure that the 'orchidarium' user owns the directory and set up a Git hook that prevents the user from pushing.
RUN chown -R orchidarium:orchidarium .

USER 10001

COPY --chown=orchidarium:orchidarium --chmod=550 bin/cmd.sh /cmd.sh

ENTRYPOINT ["/tini", "--"]
CMD [ "/cmd.sh" ]


FROM base AS package-source

COPY --chown=orchidarium:orchidarium pkg/ ./pkg/
COPY --chown=orchidarium:orchidarium README.md LICENSE poetry.lock pyproject.toml ./


FROM package-source AS develop

ENV POETRY_VIRTUALENVS_IN_PROJECT=true

RUN curl -sSL https://install.python-poetry.org | python3 -

# Separate the package installation layer from the Poetry installation layer.
RUN poetry install \
    && poetry run python -c "import orchidarium"


FROM package-source AS production

RUN python -m pip install --user --no-cache-dir --no-compile . \
    && python -c "import orchidarium" \
    && python -c "from PySide6.QtGui import QGuiApplication" \
    && rm -rf ./pkg ./README.md ./LICENSE ./poetry.lock ./pyproject.toml
