#!/usr/bin/env python3
"""Run the Sentinel-2 optical analysis (Phases 6 and 7) exporting to a local GeoTIFF using STAC."""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import pystac_client
import rioxarray
import xarray as xr

# Suppress rioxarray CRS and other warnings
warnings.filterwarnings("ignore")

LAB_DIR = Path(__file__).resolve().parent
# Changed output dir from earth_engine to stac
OUTPUT_DIR = LAB_DIR / "output" / "stac"
RASTER_FILE = OUTPUT_DIR / "sentinel2_optical_analysis.tif"
AOI = [103.62, 32.04, 103.68, 32.09]

def get_sentinel2_scene(catalog: pystac_client.Client, date_range: str) -> xr.Dataset:
    print(f"Searching STAC for {date_range}...")
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=AOI,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": 20}}
    )
    items = list(search.items())
    if not items:
        # Fallback without cloud cover filter
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=AOI,
            datetime=date_range
        )
        items = list(search.items())
        if not items:
            raise RuntimeError(f"No Sentinel-2 items found for {date_range} in the AOI.")
    
    # Take the scene with the lowest cloud cover
    items = sorted(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
    item = items[0]
    print(f"Selected item: {item.id} (Cloud cover: {item.properties.get('eo:cloud_cover', 'N/A')}%)")
    
    # Asset mapping (STAC names to original GEE band names)
    asset_keys = {
        "blue": "B2",
        "green": "B3",
        "red": "B4",
        "nir": "B8",
        "swir16": "B11"
    }
    
    das = {}
    reference_da = None
    
    for asset, band_name in asset_keys.items():
        url = item.assets[asset].href
        # We need to scale the data by dividing by 10000 for L2A reflectance (standard STAC/GEE)
        # GEE COPERNICUS/S2 L1C is already scaled or user code didn't scale it, 
        # but indices like NDVI/BSI work well with either.
        # We will use raw values as they cancel out in the formulas, 
        # but scaling helps avoid potential overflow in BSI addition.
        da = rioxarray.open_rasterio(url)
        # Clip to AOI (we provide the CRS of the AOI)
        da_clipped = da.rio.clip_box(*AOI, crs="EPSG:4326")
        
        # Remove the band dimension if it is a single band
        if "band" in da_clipped.dims:
            da_clipped = da_clipped.squeeze("band").drop_vars("band")
            
        das[band_name] = da_clipped.astype("float32")
        
        # Keep the 10m band (e.g., Red) as the reference for reprojection
        if asset == "red":
            reference_da = das[band_name]

    # Resample all bands to match the reference grid (necessary for SWIR16 which is 20m)
    for band_name, da in das.items():
        if da.shape != reference_da.shape:
            das[band_name] = da.rio.reproject_match(reference_da)
            
    # Combine into a single Dataset
    ds = xr.Dataset(das)
    return ds

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Connecting to Earth Search STAC API...")
    catalog = pystac_client.Client.open("https://earth-search.aws.element84.com/v1")

    print("\nProcessing baseline scene...")
    ds_base = get_sentinel2_scene(catalog, "2017-02-19/2017-02-21")
    
    print("\nProcessing aftermath scene...")
    ds_after = get_sentinel2_scene(catalog, "2017-08-13/2017-08-15")

    print("\nComputing indices...")
    # NDVI = (B8 - B4) / (B8 + B4)
    ndvi_base = (ds_base["B8"] - ds_base["B4"]) / (ds_base["B8"] + ds_base["B4"])
    ndvi_after = (ds_after["B8"] - ds_after["B4"]) / (ds_after["B8"] + ds_after["B4"])
    ndvi_delta = ndvi_after - ndvi_base

    # BSI = ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))
    bsi_base = ((ds_base["B11"] + ds_base["B4"]) - (ds_base["B8"] + ds_base["B2"])) / ((ds_base["B11"] + ds_base["B4"]) + (ds_base["B8"] + ds_base["B2"]))
    bsi_after = ((ds_after["B11"] + ds_after["B4"]) - (ds_after["B8"] + ds_after["B2"])) / ((ds_after["B11"] + ds_after["B4"]) + (ds_after["B8"] + ds_after["B2"]))
    bsi_delta = bsi_after - bsi_base

    print("Merging bands...")
    # Create the output dataset with the specified band order
    ds_out = xr.Dataset({
        "tc_base_r": ds_base["B4"],
        "tc_base_g": ds_base["B3"],
        "tc_base_b": ds_base["B2"],
        "tc_after_r": ds_after["B4"],
        "tc_after_g": ds_after["B3"],
        "tc_after_b": ds_after["B2"],
        "ndvi_base": ndvi_base,
        "ndvi_after": ndvi_after,
        "ndvi_delta": ndvi_delta,
        "bsi_base": bsi_base,
        "bsi_after": bsi_after,
        "bsi_delta": bsi_delta,
    })

    # Cast to float32
    ds_out = ds_out.astype("float32")

    print(f"Exporting to {RASTER_FILE.relative_to(LAB_DIR)}...")
    # Convert Dataset to DataArray for rioxarray
    da_out = ds_out.to_array(dim="band")
    
    # Add band names as description for the GeoTIFF
    da_out.attrs["long_name"] = list(ds_out.data_vars.keys())

    da_out.rio.to_raster(RASTER_FILE)

    if not RASTER_FILE.exists():
        raise SystemExit("STAC export did not create the expected GeoTIFF.")

    print("\nSentinel-2 optical analysis export completed.")
    print(f"Saved raster: {RASTER_FILE.relative_to(LAB_DIR)}")

if __name__ == "__main__":
    main()
