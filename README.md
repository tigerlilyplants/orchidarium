# Orchidarium

![GitHub Release](https://img.shields.io/github/v/release/tigerlilyplants/orchidarium) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

<p align="left" width="100%">
  <img width="20%" src="./img/orchid.png" alt="orchid">
</p>

- [Orchidarium](#orchidarium)
  - [Documentation](#documentation)
    - [Runtime Hierarchy](#runtime-hierarchy)
  - [Development](#development)
    - [Docker Compose](#docker-compose)

*Orchidarium* is a monitoring and control agent designed for terrariums that require precise environmental conditions, particularly high-humidity setups for mini and micro orchids. The project leverages key parameters such as humidity, nutrients, temperature, and lighting while enabling automated control to maintain stable habitat conditions. Its goal is to simplify the management of delicate terrarium ecosystems and help keep both plants and animals thriving with minimal manual intervention, replacing every point of contact with a configurable control loop.

See [BUILD.md](./BUILD.md) for terrarium build photos, sourced components, supported sensors, and notes on previous builds.

## Documentation

### Runtime Hierarchy

Orchidarium has one supervisor process and separate child processes for each long-running runtime domain. Metrics, API, and hardware run today; the UI process is planned but not started yet.

```text
tini
└── orchidarium
    ├── metrics / orchidarium-metrics
    │   ├── metrics main thread
    │   │   ├── metrics queue pub/sub
    │   │   ├── sensor collection interval loop
    │   │   ├── sensor ThreadPoolExecutor
    │   │   │   └── sensor_* worker thread(s)
    │   │   └── InfluxDB publisher
    ├── api / orchidarium-api
    │   └── Flask main thread
    │       ├── /health
    │       ├── /ready
    │       ├── /queue/backlog
    │       └── /sensors/active
    ├── hardware / orchidarium-hardware
    │   └── hardware main thread
    └── ui
        └── planned, not registered yet
```

- `orchidarium command`: CLI entrypoint in `orchidarium.entrypoint`; calls `orchidarium.daemon.run()`.
- `orchidarium`: supervisor process title; starts child processes with `ProcessPoolExecutor` from `orchidarium.daemon._processes`.
- `metrics`: child process spec; process title is `orchidarium-metrics`; owns metrics queue pub/sub, sensor collection, and InfluxDB publication.
- `api`: child process spec; process title is `orchidarium-api`; serves Flask API endpoints using runtime snapshots published by the metrics process.
- `hardware`: child process spec; process title is `orchidarium-hardware`; currently an idle scaffold for relay and device control. It publishes a heartbeat used by `/health` and `/ready`.
- `ui`: planned future child process; not registered in `PROCESS_SPECS` yet.
- `sensor_*`: worker threads created by the metrics process during each collection interval, with one submitted task per discovered sensor.

The publisher is not a separate thread yet. It runs after sensor collection completes in the metrics process main thread, pulling data from `metric_queue` and writing it to InfluxDB.

`/ready` fails when the published point backlog reaches `MAX_POINT_BACKLOG`, so schedulers can stop sending new work to a container that is falling behind.

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
