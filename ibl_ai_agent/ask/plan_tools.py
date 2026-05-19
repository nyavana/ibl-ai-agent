from __future__ import annotations

from pathlib import Path
import textwrap

import yaml

from .constants import PLAN_PAYLOAD_TEMPLATE_PATH
from .domain import AskPlanPayload
from .validation import extract_regions, load_region_maps, validate_analysis_code, validate_plan_payload
from ibl_ai_agent.errors import ExecutionContractError


def _question_targets_latency(question: str) -> bool:
    q = question.lower()
    return "latency" in q and ("visual" in q or "stim" in q)


def _regions_from_question(question: str) -> list[str]:
    canonical, aliases = load_region_maps()
    return extract_regions(question, aliases, canonical)


def _latency_payload(question: str) -> dict[str, object]:
    target_regions = _regions_from_question(question)
    target_regions_expr = repr(target_regions)
    analysis_code = textwrap.dedent(
        f"""
        import json
        from pathlib import Path

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        from brainbox.io.one import SessionLoader, SpikeSortingLoader
        from brainbox.singlecell import calculate_peths
        from iblatlas.regions import BrainRegions

        TARGET_REGIONS = {target_regions_expr}
        EVENT_CANDIDATES = ["stimOn_times", "stimOnTrigger_times"]
        MAX_EVENTS_PER_SESSION = 200
        MAX_UNITS_PER_SESSION = 250


        def _event_times_from_trials(trials):
            if trials is None:
                return np.array([], dtype=float), ""
            for col in EVENT_CANDIDATES:
                if col in trials.columns:
                    vals = pd.to_numeric(trials[col], errors="coerce").to_numpy(dtype=float)
                    vals = vals[np.isfinite(vals)]
                    if vals.size:
                        vals = np.sort(vals)
                        return vals[:MAX_EVENTS_PER_SESSION], col
            return np.array([], dtype=float), ""


        def _first_crossing_latency_ms(spike_times, spike_clusters, cluster_id, event_times):
            if event_times.size < 20:
                return np.nan
            clu_mask = spike_clusters == int(cluster_id)
            if int(np.sum(clu_mask)) == 0:
                return np.nan
            try:
                peths, _ = calculate_peths(
                    spike_times[clu_mask],
                    spike_clusters[clu_mask],
                    np.array([int(cluster_id)], dtype=int),
                    event_times,
                    pre_time=0.2,
                    post_time=0.3,
                    bin_size=0.005,
                    smoothing=0.02,
                    return_fr=True,
                )
            except Exception:
                return np.nan

            fr = np.asarray(peths.means[0], dtype=float)
            t = np.asarray(peths.tscale, dtype=float)
            if fr.size == 0 or t.size == 0:
                return np.nan

            base = (t >= -0.2) & (t < 0.0)
            resp = (t >= 0.0) & (t <= 0.2)
            if int(np.sum(base)) < 5 or int(np.sum(resp)) < 3:
                return np.nan

            baseline_mean = float(np.nanmean(fr[base]))
            baseline_std = float(np.nanstd(fr[base]))
            threshold = baseline_mean + 3.0 * max(baseline_std, 1e-6)

            above = np.where(resp & (fr >= threshold))[0]
            if above.size == 0:
                return np.nan
            above_set = set(int(i) for i in above.tolist())
            consecutive = [i for i in above if int(i + 1) in above_set]
            if not consecutive:
                return np.nan
            return float(t[int(min(consecutive))] * 1000.0)


        br = BrainRegions()
        target_regions = list(TARGET_REGIONS)
        if not target_regions and isinstance(globals().get("QUESTION_FILTERS"), dict):
            target_regions = list(globals().get("QUESTION_FILTERS", {{}}).get("regions", []))

        eids_local = list(globals().get("eids", []))
        latency_rows = []
        errors = []
        event_column_used = ""
        used_one = globals().get("one")

        probe_names = ["probe00", "probe01", "probe02", "probe03"]
        for eid in eids_local:
            try:
                ss = SessionLoader(one=used_one, eid=eid)
                ss.load_trials()
                trials = ss.trials if isinstance(ss.trials, pd.DataFrame) else pd.DataFrame()
                event_times, event_col = _event_times_from_trials(trials)
                if event_col and not event_column_used:
                    event_column_used = event_col
                if event_times.size == 0:
                    errors.append(f"no_visual_events {{eid}}")
                    continue
            except Exception as exc:
                errors.append(f"trials {{eid}}: {{exc}}")
                continue

            units_seen = 0
            for pname in probe_names:
                if units_seen >= MAX_UNITS_PER_SESSION:
                    break
                try:
                    sl = SpikeSortingLoader(eid=eid, pname=pname, one=used_one)
                    spikes, clusters, channels = sl.load_spike_sorting()
                    clusters = sl.merge_clusters(spikes, clusters, channels)
                except Exception:
                    continue

                if "times" not in spikes or "clusters" not in spikes:
                    continue
                cluster_ids = np.asarray(clusters.get("cluster_id", []), dtype=int)
                if cluster_ids.size == 0:
                    continue

                labels = np.asarray(clusters.get("label", np.zeros(cluster_ids.size)), dtype=float)
                firing_rate = np.asarray(
                    clusters.get("firing_rate", np.full(cluster_ids.size, np.nan)),
                    dtype=float,
                )
                if "acronym" in clusters:
                    acr = np.asarray(clusters["acronym"], dtype=object)
                elif "channels" in clusters and "acronym" in channels:
                    chan_idx = np.asarray(clusters["channels"]).astype(int)
                    acr = np.asarray(channels["acronym"], dtype=object)[chan_idx]
                else:
                    acr = np.asarray(["root"] * cluster_ids.size, dtype=object)
                beryl = br.acronym2acronym(acr, mapping="Beryl")

                st = np.asarray(spikes["times"], dtype=float)
                sc = np.asarray(spikes["clusters"], dtype=int)
                for i, cid in enumerate(cluster_ids):
                    if units_seen >= MAX_UNITS_PER_SESSION:
                        break
                    if labels.size and float(labels[i]) <= 0:
                        continue
                    region = str(beryl[i])
                    if target_regions and region not in target_regions:
                        continue

                    lat_ms = _first_crossing_latency_ms(st, sc, int(cid), event_times)
                    latency_rows.append(
                        {{
                            "eid": str(eid),
                            "probe": pname,
                            "cluster_id": int(cid),
                            "region": region,
                            "firing_rate_hz": float(firing_rate[i]) if np.isfinite(firing_rate[i]) else np.nan,
                            "latency_ms": float(lat_ms) if np.isfinite(lat_ms) else np.nan,
                        }}
                    )
                    units_seen += 1

        latency_df = pd.DataFrame(latency_rows)
        if target_regions and not latency_df.empty:
            latency_df = latency_df[latency_df["region"].isin(target_regions)].copy()

        latency_by_region = {{}}
        fr_by_region = {{}}
        if not latency_df.empty:
            latency_by_region = (
                latency_df.groupby("region", as_index=True)["latency_ms"]
                .median()
                .dropna()
                .sort_values()
                .to_dict()
            )
            fr_by_region = (
                latency_df.groupby("region", as_index=True)["firing_rate_hz"]
                .median()
                .dropna()
                .sort_index()
                .to_dict()
            )

        shortest_region = min(latency_by_region, key=latency_by_region.get) if latency_by_region else "unknown"
        pairwise = {{}}
        ordered = [r for r in target_regions if r in fr_by_region] or sorted(fr_by_region.keys())
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                a, b = ordered[i], ordered[j]
                pairwise[f"{{a}}-{{b}}"] = float(fr_by_region[a] - fr_by_region[b])

        fig, axes = plt.subplots(1, 2, figsize=(11, 4), dpi=120)
        if latency_by_region:
            x = list(latency_by_region.keys())
            y = [latency_by_region[k] for k in x]
            axes[0].bar(x, y)
            axes[0].set_title("Median visual response latency")
            axes[0].set_ylabel("Latency (ms)")
        else:
            axes[0].text(0.5, 0.5, "No latency estimates available", ha="center", va="center")
            axes[0].set_axis_off()

        if fr_by_region:
            x2 = list(fr_by_region.keys())
            y2 = [fr_by_region[k] for k in x2]
            axes[1].bar(x2, y2)
            axes[1].set_title("Median firing rate")
            axes[1].set_ylabel("Firing rate (Hz)")
        else:
            axes[1].text(0.5, 0.5, "No firing-rate estimates available", ha="center", va="center")
            axes[1].set_axis_off()

        fig.tight_layout()
        Path(FIGURE_PATH).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(FIGURE_PATH)

        latency_by_region = {{k: float(v) for k, v in latency_by_region.items()}}
        fr_by_region = {{k: float(v) for k, v in fr_by_region.items()}}
        answer = (
            f"Shortest median visual response latency: {{shortest_region}}. "
            f"Median firing rates (Hz): {{fr_by_region}}."
        )
        analysis_result = {{
            "answer": answer,
            "shortest_latency_region": shortest_region,
            "latency_ms_by_region": latency_by_region,
            "median_firing_rate_hz_by_region": fr_by_region,
            "median_fr_pairwise_deltas_hz": pairwise,
            "methods": {{
                "latency_operator": "brainbox.singlecell.calculate_peths threshold crossing",
                "event_column_used": event_column_used or "unknown",
                "latency_rule": "first 2 consecutive bins above baseline_mean + 3*baseline_std",
                "pre_time_s": 0.2,
                "post_time_s": 0.3,
                "bin_size_s": 0.005,
                "smoothing_s": 0.02,
                "target_regions": target_regions,
            }},
            "evidence": {{
                "n_eids": int(len(eids_local)),
                "n_units_analyzed": int(len(latency_df)),
                "errors_preview": [str(x) for x in errors[:10]],
            }},
            "caveats": [
                "Latency is computed from event-aligned PETHs, not a precomputed cluster field.",
                "Latency estimates depend on trial/event availability and threshold parameters.",
            ],
        }}

        result_path = Path(RESULT_JSON_PATH)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        with result_path.open("w", encoding="utf-8") as f:
            json.dump(analysis_result, f, indent=2)
        """
    ).strip()

    return {
        "plan_steps": [
            f"Question focus: {question.strip()}",
            "Compute per-unit visual response latency from spikes aligned to stimulus onset events.",
            "Aggregate latency and firing-rate medians across requested regions and compare pairwise differences.",
            "Write figure + analysis_result payload with method metadata and caveats.",
        ],
        "required_outputs_json": {
            "answer": "string",
            "shortest_latency_region": "string",
            "latency_ms_by_region": "object",
            "median_firing_rate_hz_by_region": "object",
            "median_fr_pairwise_deltas_hz": "object",
            "methods": "object",
            "evidence": "object",
            "caveats": "array",
        },
        "analysis_code": analysis_code,
    }


def load_plan_template_payload(*, question: str | None = None) -> dict[str, object]:
    if question and question.strip() and _question_targets_latency(question):
        return _latency_payload(question)

    if not PLAN_PAYLOAD_TEMPLATE_PATH.exists():
        raise ExecutionContractError(f"Template missing: {PLAN_PAYLOAD_TEMPLATE_PATH}")
    raw_template = yaml.safe_load(PLAN_PAYLOAD_TEMPLATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw_template, dict):
        raise ExecutionContractError(f"Invalid template payload at {PLAN_PAYLOAD_TEMPLATE_PATH}")
    payload = {
        "plan_steps": list(raw_template.get("plan_steps", [])),
        "required_outputs_json": dict(raw_template.get("required_outputs_json", {})),
        "analysis_code": str(raw_template.get("analysis_code", "")),
    }
    if question and question.strip():
        payload["plan_steps"] = [f"Question focus: {question.strip()}", *payload["plan_steps"]]
    return payload


def load_and_validate_plan_file(plan_file: Path) -> AskPlanPayload:
    raw = yaml.safe_load(plan_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ExecutionContractError("plan_file must contain a YAML/JSON object.")
    payload = validate_plan_payload(raw)
    errors = validate_analysis_code(payload.analysis_code)
    if errors:
        raise ExecutionContractError("invalid plan payload: " + "; ".join(errors))
    return payload
