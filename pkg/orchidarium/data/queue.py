"""
Provide a thread-safe queue for sensor data points.
"""


from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from queue import Empty, Queue
from threading import Lock
from typing import Literal, Mapping

from attrs import define, field


MetricField = bool | int | float | str
_QueueAction = Literal['initialized', 'enqueued', 'dequeued']


def _coerce_fields(fields: Mapping[str, MetricField]) -> dict[str, MetricField]:
    result = {str(key): value for key, value in fields.items()}

    if not result:
        raise ValueError('MetricDatum.fields must include at least one field')

    for key, value in result.items():
        if not isinstance(value, (bool, int, float, str)):
            raise TypeError(f'Metric field "{key}" has unsupported value type "{type(value).__name__}"')

    return result


def _coerce_tags(tags: Mapping[str, object] | None) -> dict[str, str]:
    if tags is None:
        return {}

    return {str(key): str(value) for key, value in tags.items()}


def _coerce_timestamp(timestamp: datetime | None) -> datetime:
    if timestamp is None:
        return datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)

    return timestamp


def _coerce_measurement(measurement: object) -> str:
    result = str(measurement).strip()

    if not result:
        raise ValueError('MetricDatum.measurement must not be empty')

    return result


@define(frozen=True)
class MetricDatum:
    measurement: str = field(converter=_coerce_measurement)
    fields: dict[str, MetricField] = field(converter=_coerce_fields)
    tags: dict[str, str] = field(factory=dict, converter=_coerce_tags)
    timestamp: datetime = field(factory=lambda: datetime.now(timezone.utc), converter=_coerce_timestamp)


@define(frozen=True)
class _QueueLengthSample:
    timestamp: datetime
    queue_length: int
    action: _QueueAction


@define(frozen=True)
class QueueActivitySummary:
    current_backlog: int
    window_seconds: int
    sample_count: int
    min_queue_length: int
    max_queue_length: int
    average_queue_length: float
    enqueued: int
    dequeued: int
    last_enqueued_at: str | None
    last_dequeued_at: str | None


class DataQueue:
    """
    Thread-safe queue for moving collected data points from producers to consumers.
    """

    def __init__(self, maxsize: int = 0, history_window: timedelta = timedelta(hours=1)) -> None:
        self._queue: Queue[MetricDatum] = Queue(maxsize=maxsize)
        self._history: deque[_QueueLengthSample] = deque()
        self._history_lock = Lock()
        self._history_window = history_window
        self._record_activity('initialized')

    def __len__(self) -> int:
        return self.size

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def empty(self) -> bool:
        return self._queue.empty()

    def append(self, datum: MetricDatum) -> None:
        """
        Append a metric datum to the queue.

        Args:
            datum (MetricDatum): metric datum to enqueue.
        """
        self._queue.put(datum)
        self._record_activity('enqueued')

    def pull(self, block: bool = False, timeout: float | None = None) -> MetricDatum | None:
        """
        Pull a metric datum from the queue.

        Args:
            block (bool): whether to wait for a datum when the queue is empty.
            timeout (float | None): optional maximum number of seconds to wait.

        Returns:
            MetricDatum | None: dequeued metric datum, or None when no datum is available.
        """
        try:
            if timeout is None:
                datum = self._queue.get(block=block)
            else:
                datum = self._queue.get(block=block, timeout=timeout)
        except Empty:
            return None

        self._record_activity('dequeued')
        return datum

    def task_done(self) -> None:
        """
        Mark one pulled datum as fully handled by a consumer.
        """
        self._queue.task_done()

    def join(self) -> None:
        """
        Wait until all enqueued data has been fully handled.
        """
        self._queue.join()

    def pull_all(self) -> list[MetricDatum]:
        """
        Pull every currently available metric datum from the queue.

        Returns:
            list[MetricDatum]: all queued data available at call time.
        """
        data: list[MetricDatum] = []

        while True:
            datum = self.pull()
            if datum is None:
                return data

            data.append(datum)

    def activity_summary(self, window: timedelta | None = None) -> QueueActivitySummary:
        """
        Return a rolling queue length summary.

        Args:
            window (timedelta | None): time window to summarize.

        Returns:
            QueueActivitySummary: summary of queue length activity.
        """
        now = datetime.now(timezone.utc)
        history_window = window or self._history_window
        cutoff = now - history_window
        current_backlog = self.size

        with self._history_lock:
            self._prune_history(now)
            samples = [sample for sample in self._history if sample.timestamp >= cutoff]

        if samples:
            queue_lengths = [sample.queue_length for sample in samples]
            enqueued_samples = [sample for sample in samples if sample.action == 'enqueued']
            dequeued_samples = [sample for sample in samples if sample.action == 'dequeued']
        else:
            queue_lengths = [current_backlog]
            enqueued_samples = []
            dequeued_samples = []

        return QueueActivitySummary(
            current_backlog=current_backlog,
            window_seconds=int(history_window.total_seconds()),
            sample_count=len(samples),
            min_queue_length=min(queue_lengths),
            max_queue_length=max(queue_lengths),
            average_queue_length=sum(queue_lengths) / len(queue_lengths),
            enqueued=len(enqueued_samples),
            dequeued=len(dequeued_samples),
            last_enqueued_at=self._format_sample_time(enqueued_samples[-1]) if enqueued_samples else None,
            last_dequeued_at=self._format_sample_time(dequeued_samples[-1]) if dequeued_samples else None
        )

    def _record_activity(self, action: _QueueAction) -> None:
        now = datetime.now(timezone.utc)

        with self._history_lock:
            self._history.append(
                _QueueLengthSample(
                    timestamp=now,
                    queue_length=self.size,
                    action=action
                )
            )
            self._prune_history(now)

    def _prune_history(self, now: datetime) -> None:
        cutoff = now - self._history_window

        while self._history and self._history[0].timestamp < cutoff:
            self._history.popleft()

    @staticmethod
    def _format_sample_time(sample: _QueueLengthSample) -> str:
        return sample.timestamp.isoformat()


metric_queue = DataQueue()
