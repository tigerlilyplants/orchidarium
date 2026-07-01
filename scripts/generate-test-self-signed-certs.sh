#! /usr/bin/env bash
# Generate self-signed certificates for local development.

set -euo pipefail


printf "INFO: Generating self-signed certificates for local development.\\n"

CERT_DIR="certs"
CERT_FILE="${CERT_DIR}/cert.pem"
KEY_FILE="${CERT_DIR}/key.pem"
CERT_EMAIL="${EMAIL:-orchidarium@example.local}"

if command -v git >/dev/null 2>&1; then
    GIT_EMAIL="$(git config --global --get user.email || true)"
    CERT_EMAIL="${GIT_EMAIL:-${CERT_EMAIL}}"
fi


_validate_file_path()
{
    local path="${1}"

    if [ -d "${path}" ]; then
        printf "ERROR: Expected %s to be a file, but it is a directory. Remove it and run this script again.\\n" "${path}" >&2
        exit 1
    fi
}


_generate()
{
    mkdir -p "${CERT_DIR}"

    # https://medium.com/@maciej.skorupka/hostname-mismatch-ssl-error-in-python-2901d465683
    openssl req \
        -x509 \
        -newkey rsa:4096 \
        -keyout "${KEY_FILE}" \
        -out "${CERT_FILE}" \
        -sha256 \
        -days 10 \
        -nodes \
        -subj "/C=US/ST=Georgia/L=Atlanta/O=TigerLilyPlants/CN=grafana/emailAddress=${CERT_EMAIL}" \
        -addext "subjectAltName=DNS:grafana" # ,DNS:grafana"

    chmod 600 "${KEY_FILE}"
}


# Generate self-signed certificates if they don't exist.
if [ -e "${CERT_DIR}" ] && [ ! -d "${CERT_DIR}" ]; then
    printf "ERROR: Expected %s to be a directory.\\n" "${CERT_DIR}" >&2
    exit 1
fi

_validate_file_path "${CERT_FILE}"
_validate_file_path "${KEY_FILE}"

if [ ! -f "${CERT_FILE}" ] || [ ! -f "${KEY_FILE}" ]; then
    _generate
else
    printf "INFO: Self-signed certificates already exist.\\n"
fi
