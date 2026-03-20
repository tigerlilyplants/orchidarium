#! /usr/bin/env bash
# Set up a RPi from OS installation to up-and-running with Orchidarium.

curl -fsSL https://pyenv.run | bash

# Python deps.
sudo apt-get install build-essential gdb lcov pkg-config \
    libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
    libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
    lzma-dev tk-dev uuid-dev zlib1g-dev libmpdec-dev libzstd-dev \
    inetutils-inetd

# Install latest Python 3.12, which this package depends on (see pyproject.toml).
pyenv install 3.12
pyenv virtualenv 3.12 orchidarium
pyenv activate orchidarium

# Install poetry.
curl -sSL https://install.python-poetry.org | python3 -

# There's a GPIO group by default.
sudo usermod -a -G gpio tigerlily