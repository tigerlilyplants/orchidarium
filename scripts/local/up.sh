#! /usr/bin/env bash
# Start the local Orchidarium stack.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
UDEV_RULES_DIR="/etc/udev/rules.d"

cd "${REPO_ROOT}"

_install_udev_rules()
{
    if [ ! -d "${UDEV_RULES_DIR}" ] || ! command -v udevadm >/dev/null 2>&1; then
        printf "INFO: udev is not available; skipping Orchidarium udev rule installation.\\n"
        return
    fi

    for rule in config/rules/*.rules; do
        if [ ! -f "${rule}" ]; then
            printf "ERROR: No udev rule files found under config/rules.\\n" >&2
            exit 1
        fi

        sudo install -m 0644 "${rule}" "${UDEV_RULES_DIR}/99-orchidarium-$(basename "${rule}")"
    done

    sudo udevadm control --reload-rules
    sudo udevadm trigger
}

_load_environment()
{
    if [ ! -f scripts/.env.sh ]; then
        printf "ERROR: Expected scripts/.env.sh to exist.\\n" >&2
        exit 1
    fi

    source scripts/.env.sh
}

_require_environment()
{
    local variable

    for variable in \
        DEBUG \
        DOCKER_INFLUXDB_INIT_ADMIN_TOKEN \
        DOCKER_INFLUXDB_INIT_BUCKET \
        DOCKER_INFLUXDB_INIT_MODE \
        DOCKER_INFLUXDB_INIT_ORG \
        DOCKER_INFLUXDB_INIT_PASSWORD \
        DOCKER_INFLUXDB_INIT_USERNAME \
        GF_DATABASE_PASSWORD \
        GF_DATABASE_USER \
        GF_INSTALL_PLUGINS \
        GF_PATHS_CONFIG \
        GF_PATHS_DATA \
        GF_SECURITY_ADMIN_PASSWORD \
        GF_SECURITY_ADMIN_USER \
        GF_USERS_ALLOW_SIGN_UP \
        GF_USERS_AUTO_ASSIGN_ORG \
        GF_USERS_AUTO_ASSIGN_ORG_ROLE \
        GF_USERS_AUTO_ASSIGN_ROLE \
        GF_USERS_DEFAULT_THEME \
        GF_USERS_VIEWERS_CAN_EDIT \
        GF_USERS_VIEWERS_CAN_SAVE_DASHBOARDS \
        GF_USERS_VIEWERS_CAN_SAVE_TEMPORARY \
        HEALTHCHECK_PORT \
        INFLUXDB_DATABASE \
        INFLUXDB_HOST \
        INFLUXDB_ORG \
        INFLUXDB_TOKEN \
        INFLUXDB_USERNAME \
        INFLUXDB_PASSWORD \
        INTERVAL \
        MAX_POINT_BACKLOG \
        MYSQL_DATABASE \
        MYSQL_PASSWORD \
        MYSQL_ROOT_PASSWORD \
        MYSQL_USER \
        ORCHIDARIUM_RUNTIME_DIR \
        TMPDIR \
        TERM; do
        if [ -z "${!variable:-}" ]; then
            printf "ERROR: Expected %s to be set by scripts/.env.sh.\\n" "${variable}" >&2
            exit 1
        fi
    done
}

_install_udev_rules
_load_environment
_require_environment

./scripts/generate-test-self-signed-certs.sh

docker compose up -d --build "$@"
