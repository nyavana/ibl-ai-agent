from __future__ import annotations

from dataclasses import dataclass
import json
from tempfile import mkdtemp
import os
from pathlib import Path
import shutil
from time import perf_counter
from typing import Any

from brainbox.singlecell import calculate_peths
import numpy as np
import pandas as pd
import yaml

from ibl_ai_agent.datasets import bwm_ephys, bwm_session_assets, bwm_shared


DATASET_NAME = "bwm_ephys"
SOURCE_DATASET_VERSION = "1.0.0"
TARGET_DATASET_VERSION = "1.1.0"
PASSIVE_RESPONSE_PRE_TIME_S = 0.2
PASSIVE_RESPONSE_POST_TIME_S = 0.3
PASSIVE_RESPONSE_BIN_SIZE_S = 0.005
PASSIVE_RESPONSE_SMOOTHING_S = 0.02
PASSIVE_RESPONSE_PEAK_WINDOW_S = (0.0, 0.2)
PASSIVE_RESPONSE_WINDOW_SPEC = (
    f"pre={PASSIVE_RESPONSE_PRE_TIME_S:.3f}|post={PASSIVE_RESPONSE_POST_TIME_S:.3f}|"
    f"bin={PASSIVE_RESPONSE_BIN_SIZE_S:.3f}|smooth={PASSIVE_RESPONSE_SMOOTHING_S:.3f}|"
    f"peak={PASSIVE_RESPONSE_PEAK_WINDOW_S[0]:.3f}:{PASSIVE_RESPONSE_PEAK_WINDOW_S[1]:.3f}"
)


@dataclass(frozen=True)
class UpgradeOutputs:
    dataset_dir: Path
    passive_sessions_path: Path
    passive_events_path: Path
    passive_response_features_path: Path
    schema_path: Path
    provenance_path: Path
    build_report_path: Path
    summary_path: Path
    manifest_path: Path
    archive_path: Path | None = None
    archive_checksum_path: Path | None = None


def upgrade_bwm_ephys_dataset_with_passive(
    *,
    source_dataset_dir: Path,
    output_root: Path,
    cache_root: Path,
    jobs: int = max(1, (os.cpu_count() or 2) // 2),
    resume: bool = True,
    verbose: bool = True,
    release_root: Path | None = None,
) -> UpgradeOutputs:
    reporter = bwm_ephys.BuildProgressReporter(verbose=verbose)
    if jobs <= 0:
        raise RuntimeError("jobs must be positive")
    if not source_dataset_dir.exists():
        raise FileNotFoundError(f"Missing source dataset: {source_dataset_dir}")

    target_dir = output_root / DATASET_NAME / TARGET_DATASET_VERSION

    tmp_parent = target_dir.parent
    tmp_parent.mkdir(parents=True, exist_ok=True)
    use_existing_target = target_dir.exists()
    if use_existing_target and not resume:
        raise RuntimeError(f"Target dataset already exists: {target_dir}")
    work_dir, resumed = _resolve_passive_upgrade_dir(tmp_parent, target_dir=target_dir, resume=resume)
    _write_upgrade_state(work_dir, {"status": "running", "resumed": resumed, "started_at": bwm_shared.now_iso()})

    reporter.emit(f"Upgrading {source_dataset_dir} -> {target_dir}")
    if resumed:
        reporter.emit(f"Resume: reusing partial upgrade workdir {work_dir}")
    build_started = perf_counter()
    try:
        if not (work_dir / "metadata" / "sessions.parquet").exists():
            started = perf_counter()
            _copy_tree_hardlink_preferred(source_dataset_dir, work_dir)
            reporter.emit(f"Cloned base dataset in {perf_counter() - started:.2f}s")
        else:
            if work_dir == target_dir:
                reporter.emit("Resume: existing target dataset already present; updating missing passive artifacts in place.")
            else:
                reporter.emit("Resume: base dataset clone already present; skipping clone step.")

        sessions = pd.read_parquet(work_dir / "metadata" / "sessions.parquet")
        units = pd.read_parquet(work_dir / "metadata" / "units.parquet")

        passive_sessions_path = work_dir / "metadata" / "passive_sessions.parquet"
        passive_events_path = work_dir / "metadata" / "passive_events.parquet"
        passive_features_path = work_dir / "features" / "passive_response_features.parquet"

        if passive_sessions_path.exists():
            passive_sessions = pd.read_parquet(passive_sessions_path)
            reporter.emit(f"Resume: reusing passive session availability table ({len(passive_sessions):,} rows).")
        else:
            passive_sessions = _build_passive_session_availability(sessions_df=sessions, cache_root=cache_root, reporter=reporter)
            passive_sessions.to_parquet(passive_sessions_path, engine=bwm_ephys.PARQUET_ENGINE, compression=bwm_ephys.PARQUET_COMPRESSION, index=False)
            reporter.emit(f"Saved passive session availability table to {passive_sessions_path}")
        _write_upgrade_state(work_dir, {"status": "passive_sessions_ready", "updated_at": bwm_shared.now_iso()})

        if passive_events_path.exists():
            passive_events = pd.read_parquet(passive_events_path)
            reporter.emit(f"Resume: reusing passive events table ({len(passive_events):,} rows).")
        else:
            passive_events = _build_passive_events(sessions_df=sessions, passive_sessions_df=passive_sessions, cache_root=cache_root, reporter=reporter)
            passive_events.to_parquet(passive_events_path, engine=bwm_ephys.PARQUET_ENGINE, compression=bwm_ephys.PARQUET_COMPRESSION, index=False)
            reporter.emit(f"Saved passive events table to {passive_events_path}")
        _write_upgrade_state(work_dir, {"status": "passive_events_ready", "updated_at": bwm_shared.now_iso()})

        if passive_features_path.exists():
            passive_features = pd.read_parquet(passive_features_path)
            reporter.emit(f"Resume: reusing passive response features table ({len(passive_features):,} rows).")
        else:
            passive_features = _build_passive_response_features(
                dataset_dir=work_dir,
                units_df=units,
                passive_events_df=passive_events,
                jobs=jobs,
                reporter=reporter,
            )
            passive_features.to_parquet(passive_features_path, engine=bwm_ephys.PARQUET_ENGINE, compression=bwm_ephys.PARQUET_COMPRESSION, index=False)
            reporter.emit(f"Saved passive response features table to {passive_features_path}")
        _write_upgrade_state(work_dir, {"status": "passive_features_ready", "updated_at": bwm_shared.now_iso()})

        _refresh_sidecars(
            dataset_dir=work_dir,
            passive_sessions_df=passive_sessions,
            passive_events_df=passive_events,
            passive_response_features_df=passive_features,
            cache_root=cache_root,
        )
        _write_upgrade_state(work_dir, {"status": "finalizing", "updated_at": bwm_shared.now_iso()})
        if work_dir != target_dir:
            work_dir.rename(target_dir)
        reporter.emit(f"Done: passive upgrade written to {target_dir} in {perf_counter() - build_started:.2f}s")
    except Exception as exc:
        _write_upgrade_state(work_dir, {"status": "failed", "updated_at": bwm_shared.now_iso(), "error": str(exc)})
        if resume:
            reporter.emit(f"Upgrade interrupted; preserved partial work in {work_dir} for resume.")
        else:
            shutil.rmtree(work_dir, ignore_errors=True)
        raise

    release_artifacts: dict[str, Path] | None = None
    if release_root is not None:
        release_artifacts = bwm_shared.write_release_archive(
            target_dir,
            release_root=release_root,
            dataset_name=DATASET_NAME,
            dataset_version=TARGET_DATASET_VERSION,
        )
    return UpgradeOutputs(
        dataset_dir=target_dir,
        passive_sessions_path=target_dir / "metadata" / "passive_sessions.parquet",
        passive_events_path=target_dir / "metadata" / "passive_events.parquet",
        passive_response_features_path=target_dir / "features" / "passive_response_features.parquet",
        schema_path=target_dir / "schema.yaml",
        provenance_path=target_dir / "provenance.yaml",
        build_report_path=target_dir / "build_report.yaml",
        summary_path=target_dir / "SUMMARY.md",
        manifest_path=target_dir / "manifest.json",
        archive_path=release_artifacts["archive_path"] if release_artifacts is not None else None,
        archive_checksum_path=release_artifacts["checksum_path"] if release_artifacts is not None else None,
    )


def _resolve_passive_upgrade_dir(parent: Path, *, target_dir: Path, resume: bool) -> tuple[Path, bool]:
    if target_dir.exists() and resume:
        return target_dir, True
    if resume:
        candidates = sorted(
            [path for path in parent.glob(f".upgrade-{DATASET_NAME}-passive-{TARGET_DATASET_VERSION}-*") if path.is_dir()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0], True
    return Path(mkdtemp(prefix=f".upgrade-{DATASET_NAME}-passive-{TARGET_DATASET_VERSION}-", dir=parent)), False


def _write_upgrade_state(work_dir: Path, state: dict[str, Any]) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "build_state.yaml").write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")


def _copy_tree_hardlink_preferred(src: Path, dst: Path) -> None:
    def _copy_file(link_src: str, link_dst: str) -> str:
        try:
            os.link(link_src, link_dst)
        except OSError:
            shutil.copy2(link_src, link_dst)
        return link_dst

    shutil.copytree(src, dst, copy_function=_copy_file)


def _empty_passive_sessions_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "eid",
            "session_dir",
            "alf_dir",
            "raw_passive_data_present",
            "passive_periods_present",
            "passive_rfm_times_present",
            "passive_gabor_table_present",
            "passive_stims_table_present",
            "n_passive_files",
        ]
    )


def _empty_passive_events_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "eid",
            "passive_event_id",
            "passive_event_name",
            "event_time",
            "event_end_time",
            "event_source",
            "stimulus_type",
            "position",
            "contrast",
            "phase",
        ]
    )


def _empty_passive_response_features_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "pid",
            "cluster_id",
            "passive_event_name",
            "window_spec",
            "n_events",
            "baseline_fr",
            "peak_fr",
            "peak_latency_ms",
            "modulation_index",
        ]
    )


def _build_passive_session_availability(
    *,
    sessions_df: pd.DataFrame,
    cache_root: Path,
    reporter: bwm_ephys.BuildProgressReporter | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    total = int(len(sessions_df))
    started_at = perf_counter()
    for index, row in enumerate(sessions_df.itertuples(index=False), start=1):
        alf_dir = bwm_session_assets.resolve_session_alf_dir(
            cache_root,
            lab=str(row.lab),
            subject=str(row.subject),
            date=str(row.date),
            session_number=int(row.session_number),
        )
        session_dir = alf_dir.parent if alf_dir is not None else None
        files = _passive_files(session_dir)
        rows.append(
            {
                "eid": str(row.eid),
                "session_dir": str(session_dir) if session_dir is not None else "",
                "alf_dir": str(alf_dir) if alf_dir is not None else "",
                "raw_passive_data_present": bool(session_dir is not None and (session_dir / "raw_passive_data").exists()),
                "passive_periods_present": files["periods"] is not None,
                "passive_rfm_times_present": files["rfm_times"] is not None,
                "passive_gabor_table_present": files["gabor"] is not None,
                "passive_stims_table_present": files["stims"] is not None,
                "n_passive_files": int(sum(path is not None for path in files.values())),
            }
        )
        if reporter is not None and _should_emit_progress(index, total):
            reporter.emit(
                bwm_ephys._progress_line(
                    "passive-session-availability",
                    index,
                    total,
                    started_at,
                    current=str(row.eid),
                    state=f"files={int(rows[-1]['n_passive_files'])}",
                )
            )
    df = pd.DataFrame(rows) if rows else _empty_passive_sessions_df()
    if not df.empty:
        for col in (
            "raw_passive_data_present",
            "passive_periods_present",
            "passive_rfm_times_present",
            "passive_gabor_table_present",
            "passive_stims_table_present",
        ):
            df[col] = df[col].astype(bool)
        df["n_passive_files"] = df["n_passive_files"].astype(np.int16)
    return df


def _passive_files(session_dir: Path | None) -> dict[str, Path | None]:
    if session_dir is None or not session_dir.exists():
        return {"periods": None, "rfm_times": None, "gabor": None, "stims": None}
    return {
        "periods": _first_recursive_match(session_dir, "_ibl_passivePeriods.intervalsTable.csv"),
        "rfm_times": _first_recursive_match(session_dir, "_ibl_passiveRFM.times.npy"),
        "gabor": _first_recursive_match(session_dir, "_ibl_passiveGabor.table.csv"),
        "stims": _first_recursive_match(session_dir, "_ibl_passiveStims.table.csv"),
    }


def _first_recursive_match(root: Path, pattern: str) -> Path | None:
    matches = sorted(root.rglob(pattern))
    return matches[0] if matches else None


def _build_passive_events(
    *,
    sessions_df: pd.DataFrame,
    passive_sessions_df: pd.DataFrame,
    cache_root: Path,
    reporter: bwm_ephys.BuildProgressReporter | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    total = int(len(sessions_df))
    started_at = perf_counter()
    for index, session_row in enumerate(sessions_df.itertuples(index=False), start=1):
        availability = passive_sessions_df.loc[passive_sessions_df["eid"].eq(str(session_row.eid))]
        if availability.empty:
            continue
        session_dir_value = str(availability.iloc[0]["session_dir"])
        session_dir = Path(session_dir_value) if session_dir_value else None
        files = _passive_files(session_dir)
        rows.extend(_period_events_for_session(str(session_row.eid), files["periods"]))
        rows.extend(_gabor_events_for_session(str(session_row.eid), files["gabor"]))
        rows.extend(_stims_events_for_session(str(session_row.eid), files["stims"]))
        rows.extend(_rfm_events_for_session(str(session_row.eid), files["rfm_times"]))
        if reporter is not None and _should_emit_progress(index, total):
            reporter.emit(
                bwm_ephys._progress_line(
                    "passive-events",
                    index,
                    total,
                    started_at,
                    current=str(session_row.eid),
                    state=f"rows={len(rows)}",
                )
            )
    events = pd.DataFrame(rows) if rows else _empty_passive_events_df()
    if events.empty:
        return events
    events["passive_event_id"] = np.arange(len(events), dtype=np.int32)
    events["event_time"] = pd.to_numeric(events["event_time"], errors="coerce").astype(np.float32)
    events["event_end_time"] = pd.to_numeric(events["event_end_time"], errors="coerce").astype(np.float32)
    for col in ("position", "contrast", "phase"):
        events[col] = pd.to_numeric(events[col], errors="coerce").astype(np.float32)
    events.sort_values(["eid", "event_time", "passive_event_name", "event_source"], inplace=True, kind="mergesort")
    events["passive_event_id"] = np.arange(len(events), dtype=np.int32)
    return events[
        [
            "eid",
            "passive_event_id",
            "passive_event_name",
            "event_time",
            "event_end_time",
            "event_source",
            "stimulus_type",
            "position",
            "contrast",
            "phase",
        ]
    ].reset_index(drop=True)


def _period_events_for_session(eid: str, path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    df = pd.read_csv(path, index_col=0)
    rows: list[dict[str, Any]] = []
    for column in df.columns:
        start = pd.to_numeric(pd.Series([df.loc["start", column] if "start" in df.index else np.nan]), errors="coerce").iloc[0]
        stop = pd.to_numeric(pd.Series([df.loc["stop", column] if "stop" in df.index else np.nan]), errors="coerce").iloc[0]
        if not np.isfinite(start):
            continue
        rows.append(
            {
                "eid": eid,
                "passive_event_name": f"passive_period_{column}",
                "event_time": float(start),
                "event_end_time": float(stop) if np.isfinite(stop) else np.nan,
                "event_source": path.name,
                "stimulus_type": "period",
                "position": np.nan,
                "contrast": np.nan,
                "phase": np.nan,
            }
        )
    return rows


def _gabor_events_for_session(eid: str, path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    df = pd.read_csv(path)
    rows: list[dict[str, Any]] = []
    for row in df.itertuples(index=False):
        start = pd.to_numeric(pd.Series([getattr(row, "start", np.nan)]), errors="coerce").iloc[0]
        stop = pd.to_numeric(pd.Series([getattr(row, "stop", np.nan)]), errors="coerce").iloc[0]
        if not np.isfinite(start):
            continue
        rows.append(
            {
                "eid": eid,
                "passive_event_name": "passive_gabor",
                "event_time": float(start),
                "event_end_time": float(stop) if np.isfinite(stop) else np.nan,
                "event_source": path.name,
                "stimulus_type": "gabor",
                "position": getattr(row, "position", np.nan),
                "contrast": getattr(row, "contrast", np.nan),
                "phase": getattr(row, "phase", np.nan),
            }
        )
    return rows


def _stims_events_for_session(eid: str, path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    df = pd.read_csv(path)
    rows: list[dict[str, Any]] = []
    specs = [
        ("passive_valve", "valveOn", "valveOff", "valve"),
        ("passive_tone", "toneOn", "toneOff", "tone"),
        ("passive_noise", "noiseOn", "noiseOff", "noise"),
    ]
    for event_name, start_col, stop_col, stimulus_type in specs:
        if start_col not in df.columns:
            continue
        starts = pd.to_numeric(df[start_col], errors="coerce")
        stops = pd.to_numeric(df[stop_col], errors="coerce") if stop_col in df.columns else pd.Series(np.nan, index=df.index)
        for start, stop in zip(starts, stops, strict=False):
            if not np.isfinite(start):
                continue
            rows.append(
                {
                    "eid": eid,
                    "passive_event_name": event_name,
                    "event_time": float(start),
                    "event_end_time": float(stop) if np.isfinite(stop) else np.nan,
                    "event_source": path.name,
                    "stimulus_type": stimulus_type,
                    "position": np.nan,
                    "contrast": np.nan,
                    "phase": np.nan,
                }
            )
    return rows


def _rfm_events_for_session(eid: str, path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    times = np.asarray(np.load(path), dtype=float)
    rows: list[dict[str, Any]] = []
    for value in times:
        if not np.isfinite(value):
            continue
        rows.append(
            {
                "eid": eid,
                "passive_event_name": "passive_rfm_frame",
                "event_time": float(value),
                "event_end_time": np.nan,
                "event_source": path.name,
                "stimulus_type": "rfm_frame",
                "position": np.nan,
                "contrast": np.nan,
                "phase": np.nan,
            }
        )
    return rows


def _build_passive_response_features(
    *,
    dataset_dir: Path,
    units_df: pd.DataFrame,
    passive_events_df: pd.DataFrame,
    jobs: int,
    reporter: bwm_ephys.BuildProgressReporter,
) -> pd.DataFrame:
    if units_df.empty or passive_events_df.empty:
        return _empty_passive_response_features_df()

    perf, started_at = reporter.stage_start("passive-response-features", "recompute passive response features")
    events_by_eid_name = {
        (str(eid), str(event_name)): frame["event_time"].to_numpy(dtype=float)
        for (eid, event_name), frame in passive_events_df.groupby(["eid", "passive_event_name"], sort=False)
    }
    pid_groups = list(units_df.groupby("pid", sort=False))
    total = int(len(pid_groups))
    checkpoint_dir = dataset_dir / ".passive_response_feature_chunks"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    chunk_template = _empty_passive_response_features_df()
    for index, (pid, unit_group) in enumerate(pid_groups, start=1):
        chunk_path = checkpoint_dir / f"{pid}.parquet"
        if chunk_path.exists():
            if _should_emit_progress(index, total):
                reporter.emit(
                    bwm_ephys._progress_line(
                        "passive-response-features",
                        index,
                        total,
                        started_at=perf,
                        current=str(pid),
                        state="resume:chunk-present",
                    )
                )
            continue
        eid = str(unit_group["eid"].iloc[0]) if "eid" in unit_group.columns and not unit_group.empty else ""
        event_names = [name for (eid_key, name) in events_by_eid_name if eid_key == eid]
        pid_rows: list[dict[str, Any]] = []
        if not event_names:
            chunk_template.to_parquet(chunk_path, engine=bwm_ephys.PARQUET_ENGINE, compression=bwm_ephys.PARQUET_COMPRESSION, index=False)
            if _should_emit_progress(index, total):
                reporter.emit(
                    bwm_ephys._progress_line(
                        "passive-response-features",
                        index,
                        total,
                        started_at=perf,
                        current=str(pid),
                        state="skip:no-events",
                    )
                )
            continue
        shard_path = dataset_dir / "spikes" / str(pid)
        if not shard_path.exists():
            chunk_template.to_parquet(chunk_path, engine=bwm_ephys.PARQUET_ENGINE, compression=bwm_ephys.PARQUET_COMPRESSION, index=False)
            if _should_emit_progress(index, total):
                reporter.emit(
                    bwm_ephys._progress_line(
                        "passive-response-features",
                        index,
                        total,
                        started_at=perf,
                        current=str(pid),
                        state="skip:no-shard",
                    )
                )
            continue
        shard = bwm_ephys.load_spike_shard(shard_path)
        spike_times = np.asarray(shard["spike_times_seconds"], dtype=float)
        dense_clusters = np.asarray(shard["spike_clusters"], dtype=int)
        cluster_ids = np.asarray(shard["cluster_ids"], dtype=int)
        raw_cluster_ids = cluster_ids[dense_clusters]
        unit_ids = unit_group["cluster_id"].astype(int).to_numpy()
        if unit_ids.size == 0:
            continue
        for event_name in sorted(set(event_names)):
            event_times = events_by_eid_name[(eid, event_name)]
            event_times = event_times[np.isfinite(event_times)]
            if event_times.size == 0:
                continue
            peths, _ = calculate_peths(
                spike_times,
                raw_cluster_ids,
                unit_ids,
                event_times,
                pre_time=PASSIVE_RESPONSE_PRE_TIME_S,
                post_time=PASSIVE_RESPONSE_POST_TIME_S,
                bin_size=PASSIVE_RESPONSE_BIN_SIZE_S,
                smoothing=PASSIVE_RESPONSE_SMOOTHING_S,
                return_fr=True,
            )
            means = np.asarray(peths.means, dtype=float)
            time_axis = np.asarray(peths.tscale, dtype=float)
            for unit_id, firing_rate in zip(unit_ids, means, strict=False):
                pid_rows.append(
                    {
                        "pid": str(pid),
                        "cluster_id": int(unit_id),
                        "passive_event_name": str(event_name),
                        "window_spec": PASSIVE_RESPONSE_WINDOW_SPEC,
                        "n_events": int(event_times.size),
                        **_summarize_peth_row(firing_rate=firing_rate, time_axis=time_axis),
                    }
                )
        pid_df = pd.DataFrame(pid_rows) if pid_rows else chunk_template.copy()
        if not pid_df.empty:
            pid_df["cluster_id"] = pid_df["cluster_id"].astype(np.int32)
            pid_df["n_events"] = pid_df["n_events"].astype(np.int32)
            for col in ("baseline_fr", "peak_fr", "peak_latency_ms", "modulation_index"):
                pid_df[col] = pid_df[col].astype(np.float32)
            pid_df.sort_values(["pid", "cluster_id", "passive_event_name"], inplace=True, kind="mergesort")
        pid_df.to_parquet(chunk_path, engine=bwm_ephys.PARQUET_ENGINE, compression=bwm_ephys.PARQUET_COMPRESSION, index=False)
        if _should_emit_progress(index, total):
            reporter.emit(
                bwm_ephys._progress_line(
                    "passive-response-features",
                    index,
                    total,
                    started_at=perf,
                    current=str(pid),
                    state=f"chunk_rows={len(pid_df)}",
                )
            )
    chunk_paths = sorted(checkpoint_dir.glob("*.parquet"))
    frames = [pd.read_parquet(path) for path in chunk_paths]
    nonempty_frames = [frame for frame in frames if not frame.empty]
    df = pd.concat(nonempty_frames, ignore_index=True) if nonempty_frames else _empty_passive_response_features_df()
    if not df.empty:
        df["cluster_id"] = df["cluster_id"].astype(np.int32)
        df["n_events"] = df["n_events"].astype(np.int32)
        for col in ("baseline_fr", "peak_fr", "peak_latency_ms", "modulation_index"):
            df[col] = df[col].astype(np.float32)
        df.sort_values(["pid", "cluster_id", "passive_event_name"], inplace=True, kind="mergesort")
    reporter.stage_done(
        "passive-response-features",
        perf,
        started_at,
        rows=int(len(df)),
        events=int(passive_events_df["passive_event_name"].nunique()) if not passive_events_df.empty else 0,
        insertions=total,
    )
    return df


def _should_emit_progress(index: int, total: int) -> bool:
    if total <= 0:
        return True
    if index in (1, total):
        return True
    if total <= 20:
        return True
    return index % max(1, total // 20) == 0


def _summarize_peth_row(*, firing_rate: np.ndarray, time_axis: np.ndarray) -> dict[str, float]:
    baseline_mask = (time_axis >= -PASSIVE_RESPONSE_PRE_TIME_S) & (time_axis < 0.0)
    peak_mask = (time_axis >= PASSIVE_RESPONSE_PEAK_WINDOW_S[0]) & (time_axis <= PASSIVE_RESPONSE_PEAK_WINDOW_S[1])
    if baseline_mask.sum() == 0 or peak_mask.sum() == 0:
        return {"baseline_fr": np.nan, "peak_fr": np.nan, "peak_latency_ms": np.nan, "modulation_index": np.nan}
    baseline_fr = float(np.nanmean(firing_rate[baseline_mask]))
    peak_values = np.asarray(firing_rate[peak_mask], dtype=float)
    peak_times = np.asarray(time_axis[peak_mask], dtype=float)
    if peak_values.size == 0 or np.isnan(peak_values).all():
        return {"baseline_fr": baseline_fr, "peak_fr": np.nan, "peak_latency_ms": np.nan, "modulation_index": np.nan}
    peak_index = int(np.nanargmax(peak_values))
    peak_fr = float(peak_values[peak_index])
    peak_latency_ms = float(peak_times[peak_index] * 1000.0)
    denom = peak_fr + baseline_fr
    modulation_index = float((peak_fr - baseline_fr) / denom) if np.isfinite(denom) and abs(denom) > 1e-12 else np.nan
    return {
        "baseline_fr": baseline_fr,
        "peak_fr": peak_fr,
        "peak_latency_ms": peak_latency_ms,
        "modulation_index": modulation_index,
    }


def _refresh_sidecars(
    *,
    dataset_dir: Path,
    passive_sessions_df: pd.DataFrame,
    passive_events_df: pd.DataFrame,
    passive_response_features_df: pd.DataFrame,
    cache_root: Path,
) -> None:
    schema_path = dataset_dir / "schema.yaml"
    provenance_path = dataset_dir / "provenance.yaml"
    build_report_path = dataset_dir / "build_report.yaml"
    summary_path = dataset_dir / "SUMMARY.md"
    manifest_path = dataset_dir / "manifest.json"

    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    schema["dataset_version"] = TARGET_DATASET_VERSION
    tables = schema.setdefault("tables", {})
    tables["passive_sessions"] = {"path": "metadata/passive_sessions.parquet", "primary_key": ["eid"]}
    tables["passive_events"] = {"path": "metadata/passive_events.parquet", "primary_key": ["eid", "passive_event_id"]}
    tables["passive_response_features"] = {
        "path": "features/passive_response_features.parquet",
        "primary_key": ["pid", "cluster_id", "passive_event_name", "window_spec"],
    }
    schema_path.write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")

    provenance = yaml.safe_load(provenance_path.read_text(encoding="utf-8"))
    provenance["dataset_version"] = TARGET_DATASET_VERSION
    provenance["created_at"] = bwm_shared.now_iso()
    source = provenance.setdefault("source", {})
    source["upgraded_from_dataset_version"] = SOURCE_DATASET_VERSION
    source["passive_cache_root"] = str(cache_root)
    source["passive_source_files"] = [
        "_ibl_passivePeriods.intervalsTable.csv",
        "_ibl_passiveRFM.times.npy",
        "_ibl_passiveGabor.table.csv",
        "_ibl_passiveStims.table.csv",
    ]
    source["passive_response_window_spec"] = PASSIVE_RESPONSE_WINDOW_SPEC
    storage = provenance.setdefault("storage", {})
    passive_storage = storage.setdefault("passive", {})
    passive_storage["event_tables"] = ["passive_sessions", "passive_events", "passive_response_features"]
    provenance_path.write_text(yaml.safe_dump(provenance, sort_keys=False), encoding="utf-8")

    build_report = yaml.safe_load(build_report_path.read_text(encoding="utf-8"))
    build_report["dataset_version"] = TARGET_DATASET_VERSION
    row_counts = build_report.setdefault("row_counts", {})
    row_counts["passive_sessions"] = int(len(passive_sessions_df))
    row_counts["passive_events"] = int(len(passive_events_df))
    row_counts["passive_response_features"] = int(len(passive_response_features_df))
    passive_present_sessions = int(passive_sessions_df[[
        "passive_periods_present",
        "passive_rfm_times_present",
        "passive_gabor_table_present",
        "passive_stims_table_present",
    ]].any(axis=1).sum()) if not passive_sessions_df.empty else 0
    build_report["passive"] = {
        "source_dataset_version": SOURCE_DATASET_VERSION,
        "window_spec": PASSIVE_RESPONSE_WINDOW_SPEC,
        "sessions_with_any_passive_assets": passive_present_sessions,
        "sessions_without_passive_assets": int(len(passive_sessions_df) - passive_present_sessions),
        "passive_events_by_name": {
            str(name): int(count)
            for name, count in passive_events_df["passive_event_name"].value_counts().sort_index().items()
        } if not passive_events_df.empty else {},
        "passive_response_features_by_event": {
            str(name): int(count)
            for name, count in passive_response_features_df["passive_event_name"].value_counts().sort_index().items()
        } if not passive_response_features_df.empty else {},
    }
    build_report_path.write_text(yaml.safe_dump(build_report, sort_keys=False), encoding="utf-8")

    old_summary = summary_path.read_text(encoding="utf-8")
    passive_event_counts = (
        passive_events_df["passive_event_name"].value_counts().sort_index()
        if not passive_events_df.empty else pd.Series(dtype=np.int64)
    )
    lines = [old_summary.rstrip(), "", "## Passive extension (1.1.0)", ""]
    lines.extend(
        [
            f"- Passive session availability rows: {len(passive_sessions_df):,}",
            f"- Sessions with any passive assets in local cache: {passive_present_sessions:,}",
            f"- Passive event rows: {len(passive_events_df):,}",
            f"- Passive response feature rows: {len(passive_response_features_df):,}",
            f"- Passive response window spec: `{PASSIVE_RESPONSE_WINDOW_SPEC}`",
        ]
    )
    if passive_event_counts.empty:
        lines.append("- Passive event breakdown: none found in the current local cache.")
    else:
        lines.append("- Passive event breakdown:")
        for name, count in passive_event_counts.items():
            lines.append(f"  - `{name}`: {int(count):,}")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = bwm_shared.build_manifest(
        dataset_name=DATASET_NAME,
        dataset_version=TARGET_DATASET_VERSION,
        dataset_dir=dataset_dir,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
