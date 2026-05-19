from __future__ import annotations

from pathlib import Path

import numpy as np
from iblatlas.atlas import AllenAtlas
from iblatlas.plots import prepare_lr_data
from iblatlas.regions import BrainRegions


def main() -> None:
    out_dir = Path("reports/atlas_smoke")
    out_dir.mkdir(parents=True, exist_ok=True)

    br = BrainRegions()
    _ = AllenAtlas(res_um=25)

    mop_id = int(br.acronym2id("MOp")[0])
    anc = br.id2acronym(br.ancestors(mop_id).id).tolist()
    desc = br.id2acronym(br.descendants(mop_id).id).tolist()

    ac_lh = np.array(["MOp", "VISp"])
    val_lh = np.array([1.0, 0.6])
    ac_rh = np.array(["MOp", "VISp"])
    val_rh = np.array([0.8, 0.4])
    ac_plot, val_plot = prepare_lr_data(ac_lh, val_lh, ac_rh, val_rh)

    summary = {
        "n_regions": int(br.id.size),
        "mop_id": mop_id,
        "mop_ancestors": anc,
        "mop_descendants": desc,
        "plot_labels_count": int(ac_plot.size),
        "plot_values_count": int(val_plot.size),
    }
    (out_dir / "region_nav_smoke.txt").write_text(f"{summary}\n")
    print(f"wrote {out_dir / 'region_nav_smoke.txt'}")


if __name__ == "__main__":
    main()
