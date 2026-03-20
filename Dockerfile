ARG IMAGE=python
ARG TAG=3.12

FROM ${IMAGE}:${TAG} AS base

SHELL [ "/bin/bash", "-c" ]

ENV PYTHONUNBUFFERED=1

ARG TINI_VERSION=0.19.0 \
    ARCHITECTURE=amd64

# https://github.com/opencontainers/image-spec/blob/main/annotations.md#pre-defined-annotation-keys
LABEL org.opencontainers.image.description="© Emma Doyle 2025"
LABEL org.opencontainers.image.licenses="GPLv3"
LABEL org.opencontainers.image.authors="Emma Doyle <emma.ann.doyle@gmail.com>"
LABEL org.opencontainers.image.documentatio="https://github.com/tigerlilyobservatory/orchidarium"

USER root

RUN apt update \
    && apt install -y --no-install-recommends libhidapi-dev \
    && rm -rf /var/lib/apt/lists/*

ENV TINI_VERSION=${TINI_VERSION}
# https://github.com/krallin/tini
RUN curl -sL https://github.com/krallin/tini/releases/download/v"${TINI_VERSION}"/tini-"${ARCHITECTURE}" -o /tini \
    && chmod +x /tini

# Add 'orchidarium' user and group.
RUN groupadd orchidarium \
    && useradd -rm -d /opt/orchidarium -s /bin/bash -g orchidarium -u 10001 orchidarium \
    && mkdir /opt/orchidarium/healthcheck

WORKDIR /opt/orchidarium

# Ensure that the 'operator' user owns the directory and set up a Git hook that prevents the user from pushing.
RUN chown -R orchidarium:orchidarium .

USER 10001

COPY --chown=orchidarium:orchidarium --chmod=550 bin/cmd.sh /cmd.sh

FROM base AS develop

COPY src/ ./src/
COPY README.md LICENSE poetry.lock pyproject.toml ./

ENV PATH=/opt/orchidarium/.local/bin:${PATH}

RUN curl -sSL https://install.python-poetry.org | python3 -

# Separate the package installation layer from the Poetry installation layer.
RUN poetry install
    # && poetry run orchidarium --version

ENTRYPOINT ["/tini", "--"]
CMD [ "/cmd.sh" ]
