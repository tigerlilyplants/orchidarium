#! /usr/bin/env bash
# Set up a RPi from OS installation to up-and-running with Orchidarium.

set -euo pipefail

PYTHON_VERSION="${PYTHON_VERSION:-3.13.12}"
PYTHON_VERSION_FAMILY="${PYTHON_VERSION%.*}"
PYENV_ENV_NAME="${PYENV_ENV_NAME:-orchidarium}"
PYENV_ROOT="${PYENV_ROOT:-${HOME}/.pyenv}"
PYTHON_BIN=""

export PYENV_ROOT
PATH="${PYENV_ROOT}/bin:${PYENV_ROOT}/shims:${HOME}/.local/bin:${PATH}"
export PATH


##
# Print the newest pyenv-managed Python version matching PYTHON_VERSION_FAMILY.
#   -> version::string
_pyenv_version_installed()
{
    pyenv versions --bare | grep -E "^${PYTHON_VERSION_FAMILY}\.[0-9]+$" | sort -V | tail -n 1
}


##
# Check whether a Python executable matches PYTHON_VERSION_FAMILY.
#   python_bin::path -> status::int
_python_is_compatible()
{
    local python_bin="$1"

    PYTHON_VERSION_FAMILY="${PYTHON_VERSION_FAMILY}" "${python_bin}" -c \
        'import os, sys; expected = tuple(int(part) for part in os.environ["PYTHON_VERSION_FAMILY"].split(".")); raise SystemExit(0 if sys.version_info[:len(expected)] == expected else 1)' \
        >/dev/null 2>&1
}


##
# Print the path to an installed compatible Python executable.
#   -> python_bin::path
_find_compatible_python()
{
    local candidate

    for candidate in python3.13 python3; do
        if ! command -v "${candidate}" >/dev/null 2>&1; then
            continue
        fi

        if _python_is_compatible "${candidate}"; then
            command -v "${candidate}"
            return
        fi
    done

    return 1
}


##
# Check whether the target pyenv virtualenv already exists.
#   -> status::int
_pyenv_env_exists()
{
    pyenv versions --bare | grep -Fx "${PYENV_ENV_NAME}" >/dev/null 2>&1
}


##
# Install pyenv unless it is already available on PATH.
#   -> status::int
_install_pyenv()
{
    if command -v pyenv >/dev/null 2>&1; then
        printf "INFO: pyenv already installed at %s.\\n" "$(command -v pyenv)"
        return
    fi

    printf "INFO: Installing pyenv.\\n"
    curl -fsSL https://pyenv.run | bash

    if ! command -v pyenv >/dev/null 2>&1; then
        printf "ERROR: pyenv installation completed, but pyenv is not on PATH.\\n" >&2
        exit 1
    fi
}


##
# Ensure pyenv shell initialization is present in ~/.bashrc.
#   -> status::int
_install_pyenv_shell_init()
{
    if grep -qs 'pyenv init' "${HOME}/.bashrc"; then
        printf "INFO: pyenv shell init already present in ~/.bashrc.\\n"
        return
    fi

    pyenv init --install
}


##
# Install the system packages needed for pyenv to compile Python.
#   -> status::int
_install_python_build_dependencies()
{
    # Python build deps for pyenv.
    sudo apt-get install -y build-essential gdb lcov pkg-config \
        libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
        libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
        lzma-dev tk-dev uuid-dev zlib1g-dev libmpdec-dev libzstd-dev
}


##
# Ensure the configured Python version is installed through pyenv.
#   -> status::int
_install_python()
{
    local installed_version

    installed_version="$(_pyenv_version_installed || true)"
    if [ -n "${installed_version}" ]; then
        printf "INFO: Python %s is already installed with pyenv; skipping build.\\n" "${installed_version}"
        PYTHON_VERSION="${installed_version}"
        return
    fi

    _install_python_build_dependencies

    printf "INFO: Installing Python %s with pyenv.\\n" "${PYTHON_VERSION}"
    pyenv install --skip-existing "${PYTHON_VERSION}"
}


##
# Ensure the configured pyenv virtualenv exists.
#   -> status::int
_install_virtualenv()
{
    if ! pyenv commands | grep -Fx virtualenv >/dev/null 2>&1; then
        printf "ERROR: pyenv-virtualenv is not installed. Install it or rerun the pyenv installer.\\n" >&2
        exit 1
    fi

    if _pyenv_env_exists; then
        printf "INFO: pyenv virtualenv %s already exists; skipping creation.\\n" "${PYENV_ENV_NAME}"
        return
    fi

    pyenv virtualenv "${PYTHON_VERSION}" "${PYENV_ENV_NAME}"
}


##
# Activate an existing compatible pyenv virtualenv if one is available.
#   -> status::int
_use_existing_pyenv_env()
{
    if ! command -v pyenv >/dev/null 2>&1; then
        return 1
    fi

    _install_pyenv_shell_init
    eval "$(pyenv init -)"

    if ! _pyenv_env_exists; then
        return 1
    fi

    pyenv shell "${PYENV_ENV_NAME}"
    if _python_is_compatible python3; then
        PYTHON_BIN="$(command -v python3)"
        printf "INFO: Using existing pyenv virtualenv %s.\\n" "${PYENV_ENV_NAME}"
        return 0
    fi

    printf "INFO: Existing pyenv virtualenv %s is not Python %s; looking for another compatible Python.\\n" \
        "${PYENV_ENV_NAME}" "${PYTHON_VERSION_FAMILY}"
    pyenv shell --unset >/dev/null 2>&1 || true
    return 1
}


##
# Select an existing compatible Python runtime or install one with pyenv.
#   -> status::int
_setup_python_runtime()
{
    local compatible_python

    if _use_existing_pyenv_env; then
        return
    fi

    compatible_python="$(_find_compatible_python || true)"
    if [ -n "${compatible_python}" ]; then
        PYTHON_BIN="${compatible_python}"
        printf "INFO: Python %s already installed at %s; skipping pyenv install and Python build.\\n" \
            "${PYTHON_VERSION_FAMILY}" "${PYTHON_BIN}"
        return
    fi

    _install_pyenv
    _install_pyenv_shell_init
    eval "$(pyenv init -)"

    _install_python
    _install_virtualenv

    pyenv shell "${PYENV_ENV_NAME}"
    PYTHON_BIN="$(command -v python3)"
}


##
# Install Poetry unless it is already available on PATH.
#   -> status::int
_install_poetry()
{
    if command -v poetry >/dev/null 2>&1; then
        printf "INFO: Poetry already installed at %s.\\n" "$(command -v poetry)"
        return
    fi

    curl -sSL https://install.python-poetry.org | "${PYTHON_BIN:-python3}" -
}

# Install Docker.
sudo install -m 0755 -d /etc/apt/keyrings

sudo curl -fsSL https://download.docker.com/linux/debian/gpg \
  -o /etc/apt/keyrings/docker.asc

sudo chmod a+r /etc/apt/keyrings/docker.asc

. /etc/os-release
: > /etc/apt/sources.list.d/docker.list
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $VERSION_CODENAME stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update

sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Pi tooling.
sudo apt-get install -y inetutils-inetd i2c-tools

# Install latest Python 3.13, which this package depends on (see pyproject.toml).
_setup_python_runtime

# Install poetry.
_install_poetry

# There's a GPIO group by default.
sudo usermod -a -G gpio tigerlily

# Now, run: sudo i2cdetect -y 1 to see what's connected over the bus.
