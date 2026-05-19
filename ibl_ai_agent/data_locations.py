from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Any

import yaml


DEFAULT_CONFIG_NAMES = ("data_locations.local.yaml", "data_locations.yaml")
ENV_CONFIG_PATH = "IBL_AGENT_DATA_LOCATIONS"


class DataLocationError(RuntimeError):
    """Raised when a configured local data location is missing or invalid."""


@dataclass(frozen=True)
class DatasetLocation:
    name: str
    root: Path | None
    preferred_version: str = "latest"


@dataclass(frozen=True)
class DataLocations:
    config_path: Path | None
    datasets: dict[str, DatasetLocation]
    one_cache: Path | None = None

    def dataset_root(self, name: str) -> Path:
        location = self.datasets.get(name)
        if location is None or location.root is None:
            source = self.config_path or Path("data_locations.local.yaml")
            raise DataLocationError(f"Dataset {name!r} is not configured in {source}.")
        return location.root


def find_data_locations_file(start: Path | str | None = None) -> Path | None:
    env_path = os.environ.get(ENV_CONFIG_PATH, "").strip()
    if env_path:
        return Path(env_path).expanduser()

    current = Path(start or Path.cwd()).expanduser()
    if current.is_file():
        current = current.parent
    current = current.resolve()

    for directory in (current, *current.parents):
        for name in DEFAULT_CONFIG_NAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate
    return None


def load_data_locations(
    config_path: Path | str | None = None,
    *,
    start: Path | str | None = None,
) -> DataLocations:
    resolved_path = Path(config_path).expanduser() if config_path is not None else find_data_locations_file(start)
    if resolved_path is None:
        return DataLocations(config_path=None, datasets={})
    if not resolved_path.exists():
        raise DataLocationError(f"Data locations file does not exist: {resolved_path}")

    payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise DataLocationError(f"Data locations file must contain a mapping: {resolved_path}")

    datasets_raw = payload.get("datasets", {})
    if not isinstance(datasets_raw, dict):
        raise DataLocationError(f"`datasets` must be a mapping in {resolved_path}")

    datasets: dict[str, DatasetLocation] = {}
    base_dir = resolved_path.parent
    for name, raw in datasets_raw.items():
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise DataLocationError(f"Dataset entry {name!r} must be a mapping in {resolved_path}")
        root = _optional_path(raw.get("root"), base_dir=base_dir)
        preferred = str(raw.get("preferred_version") or "latest")
        datasets[str(name)] = DatasetLocation(name=str(name), root=root, preferred_version=preferred)

    one_cache_raw = payload.get("one_cache", {})
    one_cache: Path | None = None
    if isinstance(one_cache_raw, dict):
        one_cache = _optional_path(one_cache_raw.get("root"), base_dir=base_dir)

    return DataLocations(config_path=resolved_path, datasets=datasets, one_cache=one_cache)


def find_dataset_versions(name: str, locations: DataLocations | None = None) -> list[Path]:
    locations = locations or load_data_locations()
    root = locations.dataset_root(name)
    if not root.exists():
        raise DataLocationError(f"Configured root for {name!r} does not exist: {root}")

    if (root / "schema.yaml").exists():
        return [root]

    versions = [path for path in root.iterdir() if path.is_dir() and (path / "schema.yaml").exists()]
    return sorted(versions, key=lambda path: _version_key(path.name))


def resolve_dataset_dir(name: str, locations: DataLocations | None = None) -> Path:
    locations = locations or load_data_locations()
    location = locations.datasets.get(name)
    if location is None:
        raise DataLocationError(f"Dataset {name!r} is not configured.")

    versions = find_dataset_versions(name, locations)
    if not versions:
        raise DataLocationError(
            f"No dataset versions with schema.yaml found for {name!r} under {location.root}."
        )

    if location.preferred_version == "latest":
        return versions[-1]

    root = locations.dataset_root(name)
    if root.name == location.preferred_version and (root / "schema.yaml").exists():
        return root

    selected = root / location.preferred_version
    if not (selected / "schema.yaml").exists():
        raise DataLocationError(
            f"Configured version {location.preferred_version!r} for {name!r} lacks schema.yaml: {selected}"
        )
    return selected


def _version_key(value: str) -> tuple[Any, ...]:
    parts = re.split(r"(\d+)", value)
    return tuple(int(part) if part.isdigit() else part for part in parts)


def _optional_path(raw: object, *, base_dir: Path) -> Path | None:
    if raw is None:
        return None
    if isinstance(raw, str) and raw.strip() == "":
        return None
    path = Path(str(raw)).expanduser()
    if path.is_absolute():
        return path
    return base_dir / path
