# Orchidarium 🪴

![GitHub Release](https://img.shields.io/github/v/release/tigerlilyplants/orchidarium)

<p align="left" width="100%">
  <img width="20%" src="./img/orchid.png" alt="orchid">
</p>

*Orchidarium* is a monitoring and control agent designed for terrariums that require precise environmental conditions, particularly high-humidity setups for mini and micro orchids. The project leverages key parameters such as humidity, nutrients, temperature, and lighting while enabling automated control to maintain stable habitat conditions. Its goal is to simplify the management of delicate terrarium ecosystems and help keep both plants and animals thriving with minimal manual intervention, replacing every point of contact with a configurable control loop.

See [BUILD.md](./BUILD.md) for terrarium build photos, sourced components, supported sensors, and notes on previous builds.

## Table of Contents

- [Orchidarium 🪴](#orchidarium-)
  - [Table of Contents](#table-of-contents)
  - [How it works by example](#how-it-works-by-example)
  - [Development](#development)
    - [Setup](#setup)
    - [Docker Compose](#docker-compose)

## How it works by example

See the below screenshots from the Grafana dashboard.

## Development

### Setup

1. Copy the [`udev.rules`](./rules/.rules) to `/etc/udev/rules.d/orchidarium.rules`. You'll notice I've matched the IDs of the USB devices purchased at the links above to the IDs found via [`lsusb -v`](./refs/lsusb.out).
2. Plug in USB devices or run `sudo udevadm control --reload-rules` to reload rules.
3. Source [`./scripts/.env.sh`](./scripts/.env.sh) to get started with environment variables populated from a Linux pass store.
4. The [`compose.yaml`](./compose.yaml) contains the configuration required to get this project started.

### Docker Compose

Start the local stack. This generates the self-signed Grafana certificates if they do not already exist, then runs `docker compose up -d --build`.

   ```text
   ./scripts/local/up.sh
   ```

Stop the local stack.

   ```text
   ./scripts/local/down.sh
   ```


```
$ sudo i2cdetect -y 1 -F
Functionalities implemented by /dev/i2c-1:
I2C                              yes
SMBus Quick Command              yes
SMBus Send Byte                  yes
SMBus Receive Byte               yes
SMBus Write Byte                 yes
SMBus Read Byte                  yes
SMBus Write Word                 yes
SMBus Read Word                  yes
SMBus Process Call               no
SMBus Block Write                yes
SMBus Block Read                 yes
SMBus Block Process Call         no
SMBus PEC                        no
I2C Block Write                  yes
I2C Block Read                   yes
SMBus Host Notify                no
10-bit addressing                yes
Target mode                      no
```
