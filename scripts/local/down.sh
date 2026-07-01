#! /usr/bin/env bash
# Stop the local Orchidarium stack.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
UDEV_RULES_DIR="/etc/udev/rules.d"

cd "${REPO_ROOT}"

_set_default_environment()
{
    local default_qt_qpa_platform
    local default_qt_quick_backend
    local default_wayland_runtime_dir
    local default_xdg_runtime_dir
    local host_os

    host_os="$(uname -s)"

    if [ "${host_os}" = 'Darwin' ]; then
        default_qt_qpa_platform='offscreen'
        default_qt_quick_backend='software'
        default_wayland_runtime_dir='/tmp'
        default_xdg_runtime_dir='/tmp/orchidarium'
    else
        default_qt_qpa_platform='wayland'
        default_qt_quick_backend=''
        default_wayland_runtime_dir="/run/user/$(id -u)"
        default_xdg_runtime_dir='/wayland-runtime'
    fi

    export DEBUG="${DEBUG:-}"
    export DISPLAY="${DISPLAY:-}"
    export DOCKER_INFLUXDB_INIT_ADMIN_TOKEN="${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN:-}"
    export DOCKER_INFLUXDB_INIT_BUCKET="${DOCKER_INFLUXDB_INIT_BUCKET:-}"
    export DOCKER_INFLUXDB_INIT_MODE="${DOCKER_INFLUXDB_INIT_MODE:-}"
    export DOCKER_INFLUXDB_INIT_ORG="${DOCKER_INFLUXDB_INIT_ORG:-}"
    export DOCKER_INFLUXDB_INIT_PASSWORD="${DOCKER_INFLUXDB_INIT_PASSWORD:-}"
    export DOCKER_INFLUXDB_INIT_USERNAME="${DOCKER_INFLUXDB_INIT_USERNAME:-}"
    export GF_DATABASE_PASSWORD="${GF_DATABASE_PASSWORD:-}"
    export GF_DATABASE_USER="${GF_DATABASE_USER:-}"
    export GF_INSTALL_PLUGINS="${GF_INSTALL_PLUGINS:-}"
    export GF_PATHS_CONFIG="${GF_PATHS_CONFIG:-}"
    export GF_PATHS_DATA="${GF_PATHS_DATA:-}"
    export GF_SECURITY_ADMIN_PASSWORD="${GF_SECURITY_ADMIN_PASSWORD:-}"
    export GF_SECURITY_ADMIN_USER="${GF_SECURITY_ADMIN_USER:-}"
    export GF_USERS_ALLOW_SIGN_UP="${GF_USERS_ALLOW_SIGN_UP:-}"
    export GF_USERS_AUTO_ASSIGN_ORG="${GF_USERS_AUTO_ASSIGN_ORG:-}"
    export GF_USERS_AUTO_ASSIGN_ORG_ROLE="${GF_USERS_AUTO_ASSIGN_ORG_ROLE:-}"
    export GF_USERS_AUTO_ASSIGN_ROLE="${GF_USERS_AUTO_ASSIGN_ROLE:-}"
    export GF_USERS_DEFAULT_THEME="${GF_USERS_DEFAULT_THEME:-}"
    export GF_USERS_VIEWERS_CAN_EDIT="${GF_USERS_VIEWERS_CAN_EDIT:-}"
    export GF_USERS_VIEWERS_CAN_SAVE_DASHBOARDS="${GF_USERS_VIEWERS_CAN_SAVE_DASHBOARDS:-}"
    export GF_USERS_VIEWERS_CAN_SAVE_TEMPORARY="${GF_USERS_VIEWERS_CAN_SAVE_TEMPORARY:-}"
    export HEALTHCHECK_PORT="${HEALTHCHECK_PORT:-}"
    export INFLUXDB_DATABASE="${INFLUXDB_DATABASE:-}"
    export INFLUXDB_HOST="${INFLUXDB_HOST:-}"
    export INFLUXDB_ORG="${INFLUXDB_ORG:-}"
    export INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-}"
    export INFLUXDB_USERNAME="${INFLUXDB_USERNAME:-}"
    export INFLUXDB_PASSWORD="${INFLUXDB_PASSWORD:-}"
    export INTERVAL="${INTERVAL:-}"
    export MAX_POINT_BACKLOG="${MAX_POINT_BACKLOG:-}"
    export MYSQL_DATABASE="${MYSQL_DATABASE:-}"
    export MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
    export MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
    export MYSQL_USER="${MYSQL_USER:-}"
    export ORCHIDARIUM_GID="${ORCHIDARIUM_GID:-$(id -g)}"
    export ORCHIDARIUM_HOME="${ORCHIDARIUM_HOME:-/tmp/orchidarium}"
    export ORCHIDARIUM_RUNTIME_DIR="${ORCHIDARIUM_RUNTIME_DIR:-/tmp/orchidarium}"
    export ORCHIDARIUM_UID="${ORCHIDARIUM_UID:-$(id -u)}"
    export ORCHIDARIUM_XDG_RUNTIME_DIR="${ORCHIDARIUM_XDG_RUNTIME_DIR:-${default_xdg_runtime_dir}}"
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-${default_qt_qpa_platform}}"
    export QT_QUICK_BACKEND="${QT_QUICK_BACKEND:-${default_qt_quick_backend}}"
    export TMPDIR="${TMPDIR:-/tmp/orchidarium}"
    export WAYLAND_CONTAINER_RUNTIME_DIR="${WAYLAND_CONTAINER_RUNTIME_DIR:-/wayland-runtime}"
    export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
    export WAYLAND_RUNTIME_DIR="${WAYLAND_RUNTIME_DIR:-${default_wayland_runtime_dir}}"
    export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/orchidarium/cache}"
    export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-/tmp/orchidarium/config}"
    export TERM="${TERM:-}"
}

_set_default_environment

docker compose down "$@"

_remove_udev_rules()
{
    if [ ! -d "${UDEV_RULES_DIR}" ] || ! command -v udevadm >/dev/null 2>&1; then
        printf "INFO: udev is not available; skipping Orchidarium udev rule cleanup.\\n"
        return
    fi

    for rule in config/rules/*.rules; do
        if [ -f "${rule}" ]; then
            sudo rm -f "${UDEV_RULES_DIR}/99-orchidarium-$(basename "${rule}")"
        fi
    done

    sudo udevadm control --reload-rules
    sudo udevadm trigger
}

_remove_udev_rules
