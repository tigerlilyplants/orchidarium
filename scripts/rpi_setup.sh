#! /usr/bin/env bash
# Set up a RPi from OS installation to up-and-running with Orchidarium.

curl -fsSL https://pyenv.run | bash

# Python deps + i2c-tools
sudo apt-get install build-essential gdb lcov pkg-config \
    libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
    libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
    lzma-dev tk-dev uuid-dev zlib1g-dev libmpdec-dev libzstd-dev \
    inetutils-inetd i2c-tools

# Install latest Python 3.13, which this package depends on (see pyproject.toml).
pyenv install 3.13
pyenv virtualenv 3.13 orchidarium
pyenv activate orchidarium

# Install poetry.
curl -sSL https://install.python-poetry.org | python3 -

# There's a GPIO group by default.
sudo usermod -a -G gpio tigerlily

# Now, run: sudo i2cdetect -y 1 to see what's connected over the bus.