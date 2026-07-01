"""
ABC that defines the API for publishing metrics.
"""


from __future__ import annotations

from abc import abstractmethod, ABC

from orchidarium.data.queue import DataQueue, MetricDatum


class Publisher(ABC):

    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def submit(self, datum: MetricDatum) -> bool:
        raise NotImplementedError

    def publish(self, data_queue: DataQueue) -> int:
        """
        Pull data points from a queue and submit them to this publisher.

        Args:
            data_queue (DataQueue): queue of metric data to publish.

        Returns:
            int: number of data points submitted.

        Raises:
            RuntimeError: if a datum is pulled from the queue but submission returns False.
            Exception: any exception raised by submit after the datum has been restored to the queue.
        """
        submitted = 0

        while True:
            datum = data_queue.pull()
            if datum is None:
                return submitted

            try:
                if not self.submit(datum):
                    raise RuntimeError(f'Failed to submit metric datum "{datum}"')
                submitted += 1
            except Exception:
                data_queue.append(datum)
                raise
            finally:
                data_queue.task_done()
