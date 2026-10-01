from sqlalchemy import select
from .models import Dataset, Event
from .quality import assess
from .engine import digest


def persist_dataset(session, data):
    if session.get(Dataset, data["id"]):
        raise ValueError("Dataset ID already exists; datasets are immutable")
    metadata = {k: v for k, v in data.items() if k != "events"}
    row = Dataset(id=data["id"], name=data["name"], kind=data["kind"], metadata_json=metadata, quality=assess(data), content_hash=digest(data))
    session.add(row)
    session.flush()
    session.add_all([Event(dataset_id=data["id"], event_id=e["id"], ts=e["ts"], type=e["type"], token=e["token"], wallet=e.get("wallet"), payload=e) for e in data["events"]])
    session.commit()
    return row


def load_dataset(session, dataset_id):
    row = session.get(Dataset, dataset_id)
    if not row:
        raise ValueError("Dataset not found")
    # Canonical event ordering is retained independently of database query ordering.
    events = list(session.scalars(select(Event).where(Event.dataset_id == dataset_id).order_by(Event.id)))
    return {**row.metadata_json, "events": [e.payload for e in events]}


def dataset_summary(row):
    return {**row.metadata_json, "quality": row.quality, "content_hash": row.content_hash, "created_at": row.created_at}
