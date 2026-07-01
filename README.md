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

Orchidarium has one supervisor process and separate child processes for each long-running runtime domain. Metrics and hardware run today; the UI process is planned but not started yet.

```text
orchidarium command
└── orchidarium
    ├── metrics / orchidarium-metrics
    │   ├── metrics main thread
    │   │   ├── metrics queue pub/sub
    │   │   ├── sensor collection interval loop
    │   │   ├── sensor ThreadPoolExecutor
    │   │   │   └── sensor_* worker thread(s)
    │   │   └── InfluxDB publisher
    │   └── metrics-api thread
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
- `orchidarium`: supervisor process title; starts child processes with `ProcessPoolExecutor` from `orchidarium.daemon.processes`.
- `metrics`: child process spec; process title is `orchidarium-metrics`; owns metrics queue pub/sub, the Flask API, sensor collection, and InfluxDB publication.
- `hardware`: child process spec; process title is `orchidarium-hardware`; currently an idle scaffold for relay and device control.
- `ui`: planned future child process; not registered in `PROCESS_SPECS` yet.
- `metrics-api`: daemon thread inside `orchidarium-metrics`; health and backlog state are local to the metrics process.
- `sensor_*`: worker threads created by the metrics process during each collection interval, with one submitted task per discovered sensor.

The publisher is not a separate thread yet. It runs after sensor collection completes in the metrics process main thread, pulling data from `metric_queue` and writing it to InfluxDB.

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
