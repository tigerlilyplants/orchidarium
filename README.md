# Orchidarium

![GitHub Release](https://img.shields.io/github/v/release/tigerlilyplants/orchidarium) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

<p align="left" width="100%">
  <img width="20%" src="./img/orchid.png" alt="orchid">
</p>

- [Orchidarium](#orchidarium)
  - [Development](#development)
    - [Docker Compose](#docker-compose)

*Orchidarium* is a monitoring and control agent designed for terrariums that require precise environmental conditions, particularly high-humidity setups for mini and micro orchids. The project leverages key parameters such as humidity, nutrients, temperature, and lighting while enabling automated control to maintain stable habitat conditions. Its goal is to simplify the management of delicate terrarium ecosystems and help keep both plants and animals thriving with minimal manual intervention, replacing every point of contact with a configurable control loop.

See [BUILD.md](./BUILD.md) for terrarium build photos, sourced components, supported sensors, and notes on previous builds.

## Development

### Docker Compose

Start the local stack. This installs and reloads the Orchidarium udev rules when udev is available, sources [`scripts/.env.sh`](./scripts/.env.sh), generates the self-signed Grafana certificates if they do not already exist, then runs `docker compose up -d --build`.

   ```text
   ./scripts/local/up.sh
   ```

Stop the local stack. This runs `docker compose down`, removes the Orchidarium udev rules when udev is available, then reloads udev.

   ```text
   ./scripts/local/down.sh
   ```