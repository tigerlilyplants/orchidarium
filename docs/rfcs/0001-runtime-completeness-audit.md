# RFC 0001: Orchidarium runtime and subprocess completeness audit

- Status: Draft for technical review; no implementation or deployment authorization
- Audit date: 2026-10-12
- Repository: https://github.com/tigerlilyplants/orchidarium
- Baseline: `master` at `7f557f8dd7ec3072786f15b81b82b8f82bd84d25`
- Package version: `0.0.1` (pre-alpha)
- Accountable owner: Unassigned; maintainers must nominate runtime, persistence, controls, and validation owners
- Decision requested: Accept the gap inventory and staged acceptance gates; resolve the open contracts before implementing control behavior

## Table of contents

- [Client overview](#client-overview)
- [Scope, method, and limitations](#scope-method-and-limitations)
- [Runtime and ownership map](#runtime-and-ownership-map)
- [Gap register and technical handoff](#gap-register-and-technical-handoff)
  - [G01 — P1: Complete the child lifecycle contract](#g01--p1-complete-the-child-lifecycle-contract)
  - [G02 — P1: Shared snapshot replacement is not a cross-process transaction](#g02--p1-shared-snapshot-replacement-is-not-a-cross-process-transaction)
  - [G03 — P1: Readiness can remain true for a stalled metrics cycle](#g03--p1-readiness-can-remain-true-for-a-stalled-metrics-cycle)
  - [G04 — P0: Hardware and atmospheric management are scaffolds](#g04--p0-hardware-and-atmospheric-management-are-scaffolds)
  - [G05 — P0: Relay UI has no command/acknowledgment path](#g05--p0-relay-ui-has-no-commandacknowledgment-path)
  - [G06 — P1: InfluxDB lifecycle has partial-initialization and cleanup holes](#g06--p1-influxdb-lifecycle-has-partial-initialization-and-cleanup-holes)
  - [G07 — P1: Queue pressure and zero-sensor failure paths lack a complete policy](#g07--p1-queue-pressure-and-zero-sensor-failure-paths-lack-a-complete-policy)
  - [G08 — P1 before live telemetry: Sensor validity, units and bounded I/O](#g08--p1-before-live-telemetry-sensor-validity-units-and-bounded-io)
  - [G09 — P2: Define database bootstrap and schema/retention responsibilities](#g09--p2-define-database-bootstrap-and-schemaretention-responsibilities)
  - [G10 — P1 release gate: Establish reproducible runtime validation](#g10--p1-release-gate-establish-reproducible-runtime-validation)
- [Evidence from this audit](#evidence-from-this-audit)
- [Phased roadmap and SemVer-adjacent acceptance checklist](#phased-roadmap-and-semver-adjacent-acceptance-checklist)
  - [Phase A — 0.0.2 candidate: Runtime truth and bounded lifecycle](#phase-a--002-candidate-runtime-truth-and-bounded-lifecycle)
  - [Phase B — 0.1.0 candidate: Reliable telemetry and storage contract](#phase-b--010-candidate-reliable-telemetry-and-storage-contract)
  - [Phase C — 0.2.0 candidate: Simulated controls and acknowledged UI](#phase-c--020-candidate-simulated-controls-and-acknowledged-ui)
  - [Phase D — 0.3.0 pilot candidate; eventual 1.0 gate](#phase-d--030-pilot-candidate-eventual-10-gate)
- [Alternatives and open decisions](#alternatives-and-open-decisions)
- [Related RFCs](#related-rfcs)
- [Review and completion criteria](#review-and-completion-criteria)

## Client overview

Orchidarium has a functioning architectural skeleton for collecting metrics, publishing to InfluxDB, serving health endpoints, and displaying a UI. It is not yet a complete environmental controller. The hardware child currently publishes only a heartbeat. Relay controls change UI state, with no command/acknowledgment path to hardware, and the only enabled sensor is a random-value mock.

Several failure branches also need completion before unattended operation: child shutdown, concurrent runtime snapshots, freshness-aware readiness, bounded sensor failures, and database connection cleanup. The audit found working queue fanout and failed-write requeue behavior; it does not treat all database integration as absent.

The recommendation is to stabilize supervision and observability first, make telemetry reliable next, and introduce atmospheric control only behind explicit simulation and safety gates. No proposed version number promises a release date or readiness for live equipment.

## Scope, method, and limitations

“Branches” means reachable execution and failure paths beneath the spawned processes. At audit time, the GitHub branch list returned only `master`; there were no open PRs. All eight closed PRs returned by the complete first page were merged. There was no separate unmerged development branch to audit. These observations do not establish that private local work does not exist.

The complete, non-truncated repository tree contains no `AGENTS.md`, `SKILL.md`, `.agents/skills`, RFC directory, conventional automated test files, or GitHub Actions workflows. Existing README, BUILD, package metadata, Dockerfile, Compose file, pre-commit configuration, PR template, runtime modules, API, UI, publishers, sensors and relay code were inspected. The proposed `docs/rfcs/` location introduces a convention rather than claiming one already exists.

This is static analysis plus five narrow, dependency-free probes of AST-extracted functions/classes. No Orchidarium package import, real subprocess pool, device access, network request from project code, credential access, controller change, deployment, or full runtime test was performed. Probes ran under Python 3.12.14; the supported package interpreter is Python 3.13. Re-run acceptance tests under 3.13 before claiming runtime compatibility.

Classification:

- **Verified incomplete:** a concrete stub, missing call path, or reproducible failure branch in this baseline.
- **Implemented, unverified:** code exists but its real-system behavior has not been validated here.
- **Intentional/current scope:** documented limitations or disabled capabilities, not automatically defects.
- **Design decision:** behavior requires a product/safety contract before code can be judged complete.

P0 denotes a gate before enabling real actuators, not a claim that this idle baseline is currently operating unsafe hardware. P1 denotes runtime/telemetry correctness needed before unattended use. P2 denotes completeness and reproducibility work.

## Runtime and ownership map

| Parent/domain | Spawn and normal path | IPC/readiness | Failure, retry and cleanup state |
|---|---|---|---|
| Supervisor | Four fixed process specs through `ProcessPoolExecutor` | No child startup acknowledgment or boot-generation contract | Returns on first completed future, including clean exit; catches exceptions/KeyboardInterrupt; cancels futures and requests non-waiting executor shutdown; no explicit running-child stop, bounded join, escalation, or respawn policy |
| Metrics | One collection loop; sensor thread pool, then publisher thread pool | In-memory per-publisher queues; JSON runtime snapshot for API | Sensor task exceptions and publisher exceptions collected; no-enabled-sensor branch sleeps and skips queue publication; outer exception exits; hanging worker blocks progress; fixed interval retry rather than failure-class policy |
| API | Flask `app.run`, no reloader | Reads shared JSON; `/health`, `/ready`, queue and sensor endpoints | Exception returns 1; no explicit coordinated shutdown; readiness does not attest to real control capability |
| Hardware | Infinite one-second heartbeat loop | Updates hardware health snapshot | Exception/interrupt marked failed; no device ownership, actuation, control loop or safety teardown |
| UI | Display preflight followed by Qt/QML | Persisted interval/backlog settings; relay selections are QML-local | Display/Qt failure returns to supervisor; UI lifecycle is currently coupled to whole runtime; no hardware command acknowledgment |
| InfluxDB publisher | New publisher/client context for each nonempty queue each interval | Synchronous point writes; queue datum reinserted on exception/False | Three retries for initialization `ApiException`; no application connection verification; partial-init and cleanup holes described below |

Sources: [pkg/orchidarium/daemon/_processes.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/daemon/_processes.py#L76-L142); [pkg/orchidarium/daemon/metrics.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/daemon/metrics.py#L42-L201); [pkg/orchidarium/daemon/api.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/daemon/api.py#L21-L48); [pkg/orchidarium/daemon/hardware.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/daemon/hardware.py#L23-L46); [pkg/orchidarium/daemon/ui.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/daemon/ui.py#L211-L243); [pkg/orchidarium/publishers/influxdb.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/publishers/influxdb.py#L35-L104).

## Gap register and technical handoff

Every item is unassigned. Suggested owner roles are responsibilities to allocate, not assignments to individual contributors. “Reproduce” describes a safe mock test unless explicitly stated as static inspection.

### G01 — P1: Complete the child lifecycle contract

**Classification:** Verified missing lifecycle plumbing; exact OS/container exit timing remains unverified.

[pkg/orchidarium/daemon/_processes.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/daemon/_processes.py#L110-L140) submits all domains, returns the first future's exit code, calls `future.cancel()`, then `shutdown(wait=False, cancel_futures=True)`. These calls are not a cooperative stop protocol for already-running long-lived targets. No startup deadline, SIGTERM handling policy, restart budget, sibling shutdown acknowledgment, or bounded termination sequence appears in the supervisor.

**Impact:** A clean UI exit can start whole-runtime exit handling. A failed child can leave siblings running while interpreter/process-pool teardown waits. The current code cannot demonstrate a bounded shutdown or consistent degraded mode. Compose has restart configuration, but this audit did not verify an actual successful exit/restart sequence.

**Reproduce/acceptance:** Fake executor records submissions and completion of UI with 0, API with 1, thrown exception, and startup submission failure. Then isolated Python 3.13 process tests must prove all children exit within an agreed deadline after SIGTERM/SIGINT, partial startup and broken pool. Never use hardware targets. Specify whether UI is optional and whether failure causes fail-fast exit or bounded domain restart.

**Owner/dependencies:** Runtime owner; depends on G02 state generations and G04 safe-state contract before real actuation. Restart must invalidate stale state and cannot blindly replay actuator commands.

### G02 — P1: Shared snapshot replacement is not a cross-process transaction

**Classification:** Verified concurrency defect; reproduced with isolated writers.

[pkg/orchidarium/runtime/state.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/runtime/state.py#L22-L73) uses `threading.Lock` around read/modify/write plus atomic file replacement. Each process owns a different lock. Metrics and hardware can both read the same prior snapshot and replace it with disjoint updates; the last writer discards the other domain. Atomic replacement prevents partial JSON visibility, not lost updates.

**Impact:** Health, queue or hardware fields can disappear or regress. [pkg/orchidarium/runtime/queue.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/runtime/queue.py#L39-L60) falls back to the API process's local queue when the shared queue field is absent, which can misleadingly show zero backlog. A global `updated_at` advanced by hardware also cannot prove metrics freshness.

**Reproduce:** Two independently loaded copies of the exact update/read functions, each with its own lock and the same temporary file. A barrier after both reads forces the conflict. Concurrent `thread_pool` and `hardware_process` updates leave exactly one field. This deterministic probe passed in the audit; no real child processes were launched.

**Acceptance:** Choose single-writer IPC, process-safe serialization, or independent domain files. Test concurrent updates, interrupted writes, corrupt/missing file, disk full, stale generation, permissions failure and restart. API must distinguish unknown/missing backlog from a proven empty queue. Publish a domain timestamp, sequence and boot ID; read a coherent response snapshot.

**Owner/dependencies:** Runtime/IPC owner; prerequisite for reliable G03 and G05.

### G03 — P1: Readiness can remain true for a stalled metrics cycle

**Classification:** Verified missing freshness criterion; isolated predicate probe reproduced.

[pkg/orchidarium/runtime/health.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/runtime/health.py#L48-L77) has no metrics heartbeat/cycle deadline fields. [pkg/orchidarium/runtime/health.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/runtime/health.py#L310-L360) accepts `running` with `last_run_successful=True`, positive worker count and no failed workers. A worker can hang indefinitely while that predicate remains true. Hardware has a five-second heartbeat check, but it is an idle-loop heartbeat and does not validate sensors, relays or successful environmental control. [pkg/orchidarium/daemon/metrics.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/daemon/metrics.py#L149-L194) waits for futures without a deadline.

**Impact:** After one successful run, a stalled cycle can still appear healthy and ready if the independent hardware heartbeat continues and the last backlog snapshot is below the cap. A process heartbeat is not environmental-control readiness.

**Reproduce:** Supply `{'status':'running','expected_workers':1,'failed_workers':0,'last_run_successful':True}` to the exact health/readiness predicates; both return true without any timestamp. Probe passed. This is a predicate result, not a claimed end-to-end HTTP test.

**Acceptance:** Fake-clock tests for startup, first success, overdue cycle, ongoing publication, stale sensor, mock-only configuration, partial subsystem failure, clock adjustment and boot generation. Separate liveness, telemetry readiness and control readiness. Define deadlines relative to configured interval and bounded I/O; use monotonic timing inside a process and validated timestamp/generation across processes. Revalidate future-dated hardware heartbeats, because the current age check only applies an upper bound.

**Owner/dependencies:** Runtime/observability owner; depends on G02 and G07. Define whether database outage degrades telemetry while local control continues.

### G04 — P0: Hardware and atmospheric management are scaffolds

**Classification:** Verified incomplete integration; actual plant-specific control policy is a design decision.

[pkg/orchidarium/daemon/hardware.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/daemon/hardware.py#L23-L46) does not instantiate a relay or sensor, read setpoints, evaluate feedback, or issue commands. [pkg/orchidarium/hardware/i2c/conditioner.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/hardware/i2c/conditioner.py) is empty; pump and outlet directories contain placeholders. [pkg/orchidarium/runtime/config.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/runtime/config.py#L26-L39) persists only interval and maximum backlog. The implementation has no complete temperature/humidity controller, calibration registry, actuator mapping, schedule arbitration, heating/cooling interlock, compressor minimum dwell, stale-input inhibit, watchdog-driven safe-state transition, or latched-fault recovery path.

[pkg/orchidarium/hardware/relay/8x2_i2c_relay.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/hardware/relay/8x2_i2c_relay.py#L123-L144) provides concrete I2C relay methods, read-only checks, startup initialization and reset. This code is not a complete HVAC policy. [pkg/orchidarium/hardware/relay/8x2_i2c_relay.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/hardware/relay/8x2_i2c_relay.py#L146-L158) closes the bus without applying a configured actuator-safe state. [pkg/orchidarium/hardware/relay/8x2_i2c_relay.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/hardware/relay/8x2_i2c_relay.py#L184-L241) writes two registers sequentially without readback/partial-write reconciliation. Do not assume “all relays off” is safe for every device or wiring polarity.

**Impact:** A healthy hardware heartbeat currently means its scaffold is alive. It does not mean atmospheric management is present. Connecting the existing relay/UI pieces without the missing contract would risk uncontrolled state changes.

**Acceptance:** Before any live enablement, approve per-actuator safe states/polarity, permitted temperature/humidity envelope and units, sensor quality/freshness, mutually exclusive outputs, minimum on/off times, override expiry, emergency stop, watchdog, startup/restart behavior, and fault acknowledgment. A deterministic simulator must cover out-of-range and NaN input, stuck/disconnected sensor, bus failure between register writes, actuator feedback mismatch, process death, power loss, stale command, and repeated restart. Independent physical protections and supervised commissioning require a separate plan and authorization.

**Owner/dependencies:** Controls/safety owner with hardware reviewer; blocked on device inventory, plant/environment requirements and operator-approved limits. Depends on G01–G03, G05 and G08. No setpoint values are proposed by this RFC.

### G05 — P0: Relay UI has no command/acknowledgment path

**Classification:** Verified missing plumbing.

[pkg/orchidarium/ui/qml/Main.qml](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/ui/qml/Main.qml#L70-L74) changes `relayStates` in a local array. [pkg/orchidarium/ui/qml/ControlsPage.qml](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/ui/qml/ControlsPage.qml#L8-L18) emits state changes and implements local override/freeze behavior. [pkg/orchidarium/ui/config.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/ui/config.py#L88-L141) exposes relay naming and runtime settings, but no actuation command slot. Hardware has no command consumer. “Auto”, “on”, “off” and freeze therefore do not attest to physical state.

**Impact:** The UI can display a requested state without observed device state. Freeze is not currently a hardware safety mechanism. Persisted interval/backlog settings work through a separate path and should not be confused with relay integration.

**Acceptance:** Specify a single hardware owner; command IDs, boot generation, requested/accepted/applied/observed/rejected states, acknowledgment deadline, authorization boundary, idempotency, ordering and stale-command rejection. UI must show disconnected/simulated/pending/faulted states, distinguish demand from observed state, and never optimistically label an unacknowledged output as applied. Tests cover duplicate commands, lost/late acknowledgments, child restart, conflicting manual/automatic commands and override cancellation/expiry.

**Owner/dependencies:** UI/runtime owner jointly with controls; G02 and G04 are prerequisites. Do not wire UI directly to a bus as a shortcut.

### G06 — P1: InfluxDB lifecycle has partial-initialization and cleanup holes

**Classification:** Verified failure branches in otherwise implemented database integration.

[pkg/orchidarium/publishers/influxdb.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/publishers/influxdb.py#L35-L104) builds a client and synchronous writer. Connection success is inferred from client existence, not a verified authorized bucket write. It retries only initialization `ApiException`. If client creation succeeds but `write_api()` fails, the next retry overwrites the prior client without closing it. After all three failures, `_client` remains truthy and a subsequent `connect()` returns true even with no writer. `__enter__` ignores a false return. If writer close raises, client close is skipped. No explicit per-application timeout/backoff contract is set here; SDK defaults were not audited, so this is not a claim that the SDK has no timeouts or connection pool.

**Reproduce:** Fake client construction succeeds; writer creation raises `ApiException` three times. The extracted class creates three unclosed clients, returns false, then returns true on another connect with `_write_api is None`. Separately, a fake writer whose close raises leaves the client unclosed. Both probes passed.

**What already exists:** [pkg/orchidarium/publishers/_base.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/publishers/_base.py#L49-L78) requeues a popped datum on failed submit and balances `task_done`; empty queues skip publishers; publisher failures affect cycle health. One context is created per active backend per interval. That is a lifecycle choice, not a missing ORM/session pool.

**Acceptance:** Model disconnected/initializing/ready/failed/closing states. Failed initialization closes every acquired resource; close attempts both writer and client even if one fails; context entry must fail explicitly when unusable. Test construction, writer setup, unauthorized token, missing bucket/org, connection reset, timeout, write uncertainty, retry recovery and cleanup failure. Define bounded retries/backoff and at-least-once versus deduplicated delivery without claiming exactly-once semantics.

**Owner/dependencies:** Persistence owner; depends on G07 delivery policy and G03 degraded-readiness contract. Use fake credentials and mock transports in unit tests, then an explicitly isolated disposable database for integration tests.

### G07 — P1: Queue pressure and zero-sensor failure paths lack a complete policy

**Classification:** Verified missing pressure enforcement; non-durability is an explicitly documented current limitation.

[pkg/orchidarium/data/queue.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/data/queue.py#L146-L156) defaults to an unbounded in-memory queue. [pkg/orchidarium/data/queue.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/data/queue.py#L333-L339) registers queues with that default. `MAX_POINT_BACKLOG` gates API readiness but does not stop the internal collector or bound memory. [pkg/orchidarium/daemon/metrics.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/daemon/metrics.py#L143-L152) skips `_publish_ready_queues()` if no enabled sensors are discovered, so any existing backlog cannot drain through that branch. Once retries resume, a failed point is appended at the tail, so ordering/deduplication must be specified rather than assumed.

**Impact:** A prolonged database outage can grow memory even when readiness is false; restart loses queued observations. The README already documents non-durability, so durable storage is a product decision, not an undisclosed regression.

**Acceptance:** Select a bounded loss/retention policy: bounded memory with explicit drops, durable spool, or defined backpressure. Specify metrics for accepted, submitted, acknowledged, retried, dropped and oldest pending age. Test sustained outage, cap=0, cap boundaries, poison record, recovery, process death, fanout isolation and no-sensor backlog draining. If sensor enablement becomes dynamic, reconcile cached `sensor_count()` with live discovery.

**Owner/dependencies:** Persistence/runtime owner; agree retention and resource budget first. Durable spooling would add a separate storage/version/migration contract.

### G08 — P1 before live telemetry: Sensor validity, units and bounded I/O

**Classification:** Verified disabled/stub branches; parsing defects and missing calibration/quality contract; physical readings unverified.

[pkg/orchidarium/sensors/__init__.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/sensors/__init__.py#L1-L5) imports mock, humidity and soil classes. [pkg/orchidarium/sensors/mock.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/sensors/mock.py#L18-L50) is enabled; [pkg/orchidarium/sensors/humidity.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/sensors/humidity.py#L19-L85) and [pkg/orchidarium/sensors/soil.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/sensors/soil.py#L22-L33) are disabled. Soil collection returns false and publication contains an ellipsis. Humidity parsing labels output Fahrenheit without a verified device-unit/calibration contract. Its frame regex uses an unescaped decimal dot, accepts nondecimal separators, rejects negative temperatures, and has no range/finiteness validation. The exact patterns accepted `T: 72x5, RH: 60x0` and rejected `T: -5.0, RH: 60.0` in a safe regex probe. This does not prove what the physical sensor actually emits.

[pkg/orchidarium/lib/bus.py](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pkg/orchidarium/lib/bus.py#L34-L111) retries forever on timeout/busy. Other USB errors are logged and retried immediately by the outer loop, without a delay or attempt budget. Interface release/reattach also uses this retry helper, so failure cleanup can hang. Sensor-level retry count does not bound a nested bus call.

**Acceptance:** Separate explicit simulation mode from real sensor readiness. Inventory stable sensor IDs, model/firmware, raw protocol, units, calibration provenance/date, precision, plausible ranges and maximum sample age. Test captured synthetic frames including negatives, decimals, truncated frames, invalid UTF-8, unplug, timeout, persistent busy, non-busy USB errors and cleanup failure. Bound retries and cancellation; ensure every error produces unavailable/stale quality instead of a plausible value. Do not count abstract `NotImplementedError` declarations as missing concrete implementations.

**Owner/dependencies:** Sensors owner; atmospheric control G04 is blocked until valid real input and failure semantics are demonstrated. Disabled sensors remain disabled under this RFC.

### G09 — P2: Define database bootstrap and schema/retention responsibilities

**Classification:** Implemented deployment bootstrap, unverified operational contract; no evidence that an application SQL migration system is currently required.

[compose.yaml](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/compose.yaml#L72-L100) supplies InfluxDB initialization inputs and a persistent volume. [compose.yaml](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/compose.yaml#L101-L128) puts MySQL behind the dashboard profile; Grafana depends on it. The runtime publisher registry contains only InfluxDB. Do not invent a missing MySQL application connection, ORM session pool or relational migration layer from the presence of that container.

**Acceptance:** Document bucket/org creation ownership, retention, token scope, measurement/field/unit schema evolution, backup/restore and compatibility across upgrade/downgrade. Test empty-volume bootstrap versus existing-volume restart, missing/renamed bucket, insufficient authorization, field-type conflict and unavailable backend in an isolated approved environment. Record which migrations belong to upstream Grafana/MySQL and which, if any, Orchidarium owns. Keep all real secret values out of fixtures, logs and this RFC.

**Owner/dependencies:** Persistence/deployment owner; depends on G06/G07 and an explicit retention decision.

### G10 — P1 release gate: Establish reproducible runtime validation

**Classification:** Verification gap, not proof that every untested path is broken.

The baseline tree has no conventional automated tests or GitHub workflow. `.circleci/config.yml` is empty. [pyproject.toml](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/pyproject.toml#L1-L25) declares Python 3.13 and version 0.0.1. [.pre-commit-config.yaml](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/.pre-commit-config.yaml) includes lint/metadata hooks, while mypy/pylint are commented out; Docker build checks imports but does not exercise lifecycle branches. No full pre-commit run, dependency install, image build or runtime startup was performed by this audit.

**Acceptance:** Add a hardware/network-denied test target under Python 3.13 with injected clocks, transports and executors. Each finding needs normal, error, cancellation, cleanup and repeated/restart cases. Separately gate disposable-database integration, simulator soak and approved supervised hardware commissioning. Require explicit pass/fail/not-run reporting; no use of “tests pass” for import-only or mocked predicate checks.

**Owner/dependencies:** Validation owner; test infrastructure precedes acceptance of fixes to G01–G09.

## Evidence from this audit

| Probe | Observed result | What it does not prove |
|---|---|---|
| Two independent snapshot writers synchronized after read | One of two disjoint domain updates lost | Real process timing/frequency or a production incident |
| Metrics running snapshot after prior success, no timestamp | Health and readiness predicates both true | Complete Flask endpoint behavior |
| Three failing Influx writer initializations | Superseded clients unclosed; subsequent connect true with absent writer | Actual backend/SDK failure frequency |
| Writer close raises | Client close skipped | Resource behavior of a real client |
| Humidity frame regex | Nondecimal separator accepted; negative temperature rejected | Physical protocol and units |

All five isolated probes passed their assertions, meaning they reproduced the described gaps. Production behavior, Python 3.13 package integration, UI rendering, real SQL/Influx services, sensors, relays, HVAC and restart timing remain untested. Reproduction details above are intentionally dependency-free; proposed acceptance tests are future work, not reported passes.

## Phased roadmap and SemVer-adjacent acceptance checklist

Version labels below are planning milestones relative to the existing 0.0.1, not release assignments or package edits. Before 1.0, compatibility still needs an explicit policy; any change to API schemas, persisted state or device behavior must be documented even when the version increment is small.

### Phase A — 0.0.2 candidate: Runtime truth and bounded lifecycle

Goal: Make process status, startup and shutdown trustworthy without enabling hardware.

- [ ] Assign runtime and validation owners; agree mandatory/optional domains and failure policy.
- [ ] G01: bounded startup/stop protocol, partial-start cleanup and restart budget tested under Python 3.13.
- [ ] G02: process-safe domain updates, boot IDs and coherent snapshot reads.
- [ ] G03: freshness-aware health/readiness, including mock-only and stale-domain states.
- [ ] G10: isolated test target denies network/device access and reports branch coverage.

Validation gate: deterministic concurrency/fake-clock tests and isolated process lifecycle tests pass; documentation differentiates liveness, telemetry readiness and control readiness. Blockers: shutdown deadlines, UI optionality and IPC choice. No live-actuator enablement.

### Phase B — 0.1.0 candidate: Reliable telemetry and storage contract

Goal: Demonstrate bounded sensor-to-database behavior, including failure and recovery.

- [ ] G06: connection acquisition, failure classification and teardown contract.
- [ ] G07: resource cap, retention/loss policy, fanout isolation and zero-sensor drain behavior.
- [ ] G08: explicit simulation mode, sensor protocol/unit/quality contract and bounded bus operations.
- [ ] G09: bootstrap, schema evolution, retention and restore ownership documented.

Validation gate: offline tests plus separately approved disposable InfluxDB fault injection prove recovery, resource bounds and documented delivery semantics; no unreviewed production tokens or host devices. Blockers: real sensor protocol evidence, resource/retention requirements and isolated database test fixture. Dependencies: Phase A.

### Phase C — 0.2.0 candidate: Simulated controls and acknowledged UI

Goal: Complete a closed-loop controller in simulation with explicit operator-visible state.

- [ ] G04: approved control envelope, units, calibration, interlocks, dwell times and per-device safe states.
- [ ] G05: versioned command/acknowledgment contract and requested-versus-observed UI.
- [ ] Fault matrix covers stale/invalid inputs, partial actuator writes, death/restart, stuck outputs and manual override expiry.
- [ ] Freeze/emergency-stop meaning is specified and validated; a visual freeze is never presented as physical protection.

Validation gate: deterministic simulator and time-accelerated soak pass every safety invariant, with no hardware access. Blockers: actuator inventory, wiring polarity, sensor quality and accountable safety reviewer. Dependencies: Phases A and B. Control enablement remains off.

### Phase D — 0.3.0 pilot candidate; eventual 1.0 gate

Goal: Only after separate approval, commission a bounded installation with independent protections and rollback.

- [ ] Separate reviewed commissioning plan, manual stop, independent protection and safe-state verification.
- [ ] Supervised physical tests validate units/calibration, feedback and power-loss/restart behavior.
- [ ] Operator runbook covers alarms, override expiry, data gaps, backup/restore and recovery.
- [ ] Publish compatibility policy, supported devices, limits and release evidence before considering 1.0.

Validation gate: signed-off installation-specific results, not simulation success alone. Blockers: explicit hardware authorization and safety review. Dependencies: all earlier phases. This RFC does not authorize these actions or prescribe biological setpoints.

## Alternatives and open decisions

1. Keep the current monolithic supervisor versus separate services. Separate services may improve lifecycle isolation but add deployment/IPC complexity; do not redesign merely to fix atomicity.
2. Single-writer snapshot broker versus per-domain files versus process-safe transactional storage. Select based on failure isolation and testing, not solely performance.
3. Treat UI exit as noncritical versus stop the controller. Make headless behavior explicit.
4. Bounded lossy telemetry versus durable spool. Decide data-loss budget, storage wear and recovery behavior before implementation.
5. Separate database degradation from control degradation. Local safety must not depend on a remote metrics write unless explicitly required and justified.
6. Decide command authorization and auditability before exposing actuator endpoints; the present read-only API is not authorization infrastructure for control.
7. Confirm device/actuator inventory and what “safe” means for each load. A process watchdog alone is not an independent hardware safety system.

## Related RFCs

No prior Orchidarium RFC was found in the inspected tree or the repository RFC issue/PR search as of the audit date. This section intentionally does not fabricate RFC identifiers or import unrelated research proposals.

Verified related design history (merged PRs, not RFCs):

- [PR #3 — Decouple producers and consumers](https://github.com/tigerlilyplants/orchidarium/pull/3): queue fanout and collection/publication boundaries underpin G06/G07.
- [PR #8 — Wire UI to process state](https://github.com/tigerlilyplants/orchidarium/pull/8): persisted runtime settings underpin the distinction between working configuration plumbing and missing relay control in G05.
- [Runtime hierarchy and queue limitations](https://github.com/tigerlilyplants/orchidarium/blob/7f557f8dd7ec3072786f15b81b82b8f82bd84d25/README.md#runtime-hierarchy): baseline architecture and documented scope.

## Review and completion criteria

Reviewers should validate classifications and source anchors, assign owners, resolve the lifecycle/IPC/retention/control contracts, and accept or amend the phased gates. This RFC is complete as an audit when its evidence and decisions are reviewable; implementing fixes, changing controller behavior, merging, deploying, and commissioning are separate work.
