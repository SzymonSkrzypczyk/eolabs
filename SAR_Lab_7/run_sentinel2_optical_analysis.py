#!/usr/bin/env python3
"""Run the Sentinel-2 optical analysis (Phases 6 and 7) exporting to a local GeoTIFF."""

from __future__ import annotations

import os
from pathlib import Path

import ee
import geemap

LAB_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = LAB_DIR / "output" / "earth_engine"
RASTER_FILE = OUTPUT_DIR / "sentinel2_optical_analysis.tif"
AOI = [103.62, 32.04, 103.68, 32.09]

def main() -> None:
    project_id = os.environ.get("EARTH_ENGINE_PROJECT", "").strip()
    if not project_id:
        raise SystemExit(
            "EARTH_ENGINE_PROJECT is not set. Configure it privately in this run configuration."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        ee.Initialize(project=project_id)
    except Exception as exc:
        ee.Authenticate()
        ee.Initialize(project=project_id)
        raise SystemExit(
            f"Earth Engine initialization failed with {type(exc).__name__}."
        ) from None
    

    target_region = ee.Geometry.Rectangle(AOI)
    
    s2_collection = (
        ee.ImageCollection("COPERNICUS/S2")
        .filterBounds(target_region)
    )

    baseline_scene = ee.Image(s2_collection.filterDate("2017-02-19", "2017-02-21").first())
    aftermath_scene = ee.Image(s2_collection.filterDate("2017-08-13", "2017-08-15").first())

    # NDVI = (B8 - B4) / (B8 + B4)
    ndvi_base = baseline_scene.normalizedDifference(["B8", "B4"]).rename("ndvi_base")
    ndvi_after = aftermath_scene.normalizedDifference(["B8", "B4"]).rename("ndvi_after")
    ndvi_delta = ndvi_after.subtract(ndvi_base).rename("ndvi_delta")

    # BSI = ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))
    bsi_expr = "((b('B11') + b('B4')) - (b('B8') + b('B2'))) / ((b('B11') + b('B4')) + (b('B8') + b('B2')))"
    bsi_base = baseline_scene.expression(bsi_expr).rename("bsi_base")
    bsi_after = aftermath_scene.expression(bsi_expr).rename("bsi_after")
    bsi_delta = bsi_after.subtract(bsi_base).rename("bsi_delta")

    # True color
    tc_base = baseline_scene.select(["B4", "B3", "B2"]).rename(["tc_base_r", "tc_base_g", "tc_base_b"])
    tc_after = aftermath_scene.select(["B4", "B3", "B2"]).rename(["tc_after_r", "tc_after_g", "tc_after_b"])

    merged_output = (
        tc_base
        .addBands(tc_after)
        .addBands(ndvi_base)
        .addBands(ndvi_after)
        .addBands(ndvi_delta)
        .addBands(bsi_base)
        .addBands(bsi_after)
        .addBands(bsi_delta)
        .clip(target_region)
        .toFloat()
    )

    geemap.ee_export_image(
        merged_output,
        filename=str(RASTER_FILE),
        scale=10,
        region=target_region,
        file_per_band=False,
    )
    
    if not RASTER_FILE.exists():
        raise SystemExit("Earth Engine export did not create the expected GeoTIFF.")

    print("Sentinel-2 optical analysis export completed.")
    print(f"Saved raster: {RASTER_FILE.relative_to(LAB_DIR)}")

if __name__ == "__main__":
    main()
