import os
import hashlib
from pathlib import Path

from app.core.config import BASE_DIR


class LocalEvidenceStorage:
    """Local artifact storage behind a replaceable storage abstraction."""

    def __init__(self, root: Path | None = None):
        configured = os.getenv("EVIDENCE_STORAGE_PATH")
        self.root = Path(configured).resolve() if configured else (BASE_DIR / "storage" / "evidence").resolve()

    def key_for(self, organization_id: str, dispute_id: str, evidence_id: str) -> str:
        dispute_slug = hashlib.sha256(dispute_id.encode("utf-8")).hexdigest()
        return "/".join((organization_id, "disputes", dispute_slug, "evidence", evidence_id, "artifact"))

    def _path(self, storage_key: str) -> Path:
        path = (self.root / Path(storage_key)).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError("Invalid evidence storage key.")
        return path

    def write(self, storage_key: str, content: bytes) -> None:
        path = self._path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def read(self, storage_key: str) -> bytes:
        return self._path(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self._path(storage_key)
        if path.exists():
            path.unlink()


storage = LocalEvidenceStorage()
