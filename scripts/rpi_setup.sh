#! /usr/bin/env bash
# Set up a RPi from OS installation to up-and-running with Orchidarium.

# curl -fsSL https://pyenv.run | sudo bash

# Install Docker.
sudo install -m 0755 -d /etc/apt/keyrings

sudo curl -fsSL https://download.docker.com/linux/debian/gpg \
  -o /etc/apt/keyrings/docker.asc

sudo chmod a+r /etc/apt/keyrings/docker.asc

. /etc/os-release

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $VERSION_CODENAME stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update

sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Python deps + i2c-tools
sudo apt-get install -y build-essential gdb lcov pkg-config \
    libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
    libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
    lzma-dev tk-dev uuid-dev zlib1g-dev libmpdec-dev libzstd-dev \
    inetutils-inetd i2c-tools

# Install latest Python 3.13, which this package depends on (see pyproject.toml).
pyenv install 3.13
pyenv virtualenv 3.13 orchidarium
pyenv init --install
pyenv activate orchidarium

# Install poetry.
curl -sSL https://install.python-poetry.org | python3 -

# There's a GPIO group by default.
sudo usermod -a -G gpio tigerlily

# Now, run: sudo i2cdetect -y 1 to see what's connected over the bus.