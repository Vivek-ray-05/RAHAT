"""
Ingestion adapter interface. One shape for turning any data source
(synthetic scenario now, real sensors/HTTP/MQTT later) into a
SensorEvent row, so the rest of the system never has to know where
the data came from.
"""
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Session

from app.models.sensor_event import SensorEvent


class NormalizedEvent(BaseModel):
    source: str
    zone_id: int
    event_type: str
    value: float
    confidence: float
    observed_at: datetime
    provenance: dict
    simulation_run_id: int | None = None


class AbstractIngestionAdapter(ABC):
    """One adapter = one data source. Subclasses implement how to get
    raw readings and how to turn one raw reading into a NormalizedEvent;
    ingest() handles persisting it the same way for every adapter."""

    source_name: str

    @abstractmethod
    def poll_or_receive(self) -> list[dict]:
        """Return a batch of raw readings from this source."""
        ...

    @abstractmethod
    def normalize(self, raw: dict) -> NormalizedEvent:
        """Turn one raw reading into the common event shape."""
        ...

    def ingest(self, session: Session, raw: dict) -> SensorEvent:
        event = self.normalize(raw)
        row = SensorEvent(
            simulation_run_id=event.simulation_run_id,
            source_adapter=event.source,
            zone_id=event.zone_id,
            event_type=event.event_type,
            value=event.value,
            confidence=event.confidence,
            provenance=event.provenance,
            received_at=event.observed_at,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def ingest_batch(self, session: Session) -> list[SensorEvent]:
        return [self.ingest(session, raw) for raw in self.poll_or_receive()]
