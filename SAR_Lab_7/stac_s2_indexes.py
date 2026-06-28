#!/usr/bin/env python3
"""
Calculate and display various spectral indices for Sentinel-2 (Pre- vs Post-event) 
using STAC catalogs for the 2017-06-24 Xinmo Landslide.

Indices computed:
- NDVI (Normalized Difference Vegetation Index)
- NDWI (Normalized Difference Water Index)
- NBR (Normalized Burn Ratio)
"""

import warnings
import requests
import numpy as np
import matplotlib.pyplot as plt

import pystac_client
import rioxarray
import xarray as xr

warnings.filterwarnings("ignore")

LANDSLIDE_LON, LANDSLIDE_LAT = 103.655, 32.068
RADIUS = 0.03
AOI = [
    LANDSLIDE_LON - RADIUS,
    LANDSLIDE_LAT - RADIUS,
    LANDSLIDE_LON + RADIUS,
    LANDSLIDE_LAT + RADIUS
]

def get_s2_bands(date_range: str, bands: list):
    print(f"Searching Earth Search for Sentinel-2 L2A ({date_range})...")
    catalog = pystac_client.Client.open("https://earth-search.aws.element84.com/v1")
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=AOI,
        datetime=date_range
    )
    items = list(search.items())
    if not items:
        print(f"No Sentinel-2 items found for {date_range}.")
        return None
    
    # Sort by cloud cover and take the clearest one
    items = sorted(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
    item = items[0]
    print(f"Found S2 item: {item.id} (Cloud cover: {item.properties.get('eo:cloud_cover', 'N/A')}%)")
    
    das = {}
    first_da = None
    
    for b in bands:
        da = rioxarray.open_rasterio(item.assets[b].href)
        da_clipped = da.rio.clip_box(*AOI, crs="EPSG:4326")
        
        if first_da is None:
            da_clipped = da_clipped.rio.reproject("EPSG:4326")
            first_da = da_clipped
        else:
            da_clipped = da_clipped.rio.reproject_match(first_da)
            
        if "band" in da_clipped.dims:
            da_clipped = da_clipped.squeeze("band").drop_vars("band")
            
        # Convert to float and scale (Sentinel-2 L2A scale factor is 10000)
        da_clipped = da_clipped.astype("float32") / 10000.0
        das[b] = da_clipped
        
    return das, first_da.rio.bounds()

def calc_normalized_index(band1: xr.DataArray, band2: xr.DataArray) -> np.ndarray:
    """Calculates (band1 - band2) / (band1 + band2)"""
    b1 = band1.values
    b2 = band2.values
    
    num = b1 - b2
    den = b1 + b2
    
    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        index = np.where(den != 0, num / den, np.nan)
        
    return index

def main():
    # The Xinmo landslide occurred on 2017-06-24
    s2_pre_date = "2017-01-01/2017-06-23"
    s2_post_date = "2017-06-24/2017-08-15"
    
    required_bands = ["green", "red", "nir", "swir22"]
    
    pre_result = get_s2_bands(s2_pre_date, required_bands)
    post_result = get_s2_bands(s2_post_date, required_bands)
    
    if pre_result is None or post_result is None:
        print("Could not retrieve both pre and post event imagery.")
        return
        
    das_pre, bounds_pre = pre_result
    das_post, bounds_post = post_result
    
    # Calculate Indices
    # NDVI: (NIR - Red) / (NIR + Red)
    ndvi_pre = calc_normalized_index(das_pre["nir"], das_pre["red"])
    ndvi_post = calc_normalized_index(das_post["nir"], das_post["red"])
    
    # NDWI: (Green - NIR) / (Green + NIR)
    ndwi_pre = calc_normalized_index(das_pre["green"], das_pre["nir"])
    ndwi_post = calc_normalized_index(das_post["green"], das_post["nir"])
    
    # NBR: (NIR - SWIR22) / (NIR + SWIR22)
    nbr_pre = calc_normalized_index(das_pre["nir"], das_pre["swir22"])
    nbr_post = calc_normalized_index(das_post["nir"], das_post["swir22"])
    
    indices = [
        ("NDVI\n(Vegetation)", ndvi_pre, ndvi_post, "RdYlGn", -0.5, 0.9),
        ("NDWI\n(Water/Moisture)", ndwi_pre, ndwi_post, "BrBG", -0.8, 0.4),
        ("NBR\n(Burn/Barren)", nbr_pre, nbr_post, "PiYG", -0.5, 0.8)
    ]
    
    extent = [bounds_pre[0], bounds_pre[2], bounds_pre[1], bounds_pre[3]]
    
    # Plotting
    for name, pre_data, post_data, cmap, vmin, vmax in indices:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Pre
        im_pre = axes[0].imshow(pre_data, cmap=cmap, extent=extent, origin="upper", vmin=vmin, vmax=vmax)
        axes[0].set_title(f"Pre-Event {name}")
        fig.colorbar(im_pre, ax=axes[0], fraction=0.046, pad=0.04)
        
        # Post
        im_post = axes[1].imshow(post_data, cmap=cmap, extent=extent, origin="upper", vmin=vmin, vmax=vmax)
        axes[1].set_title(f"Post-Event {name}")
        fig.colorbar(im_post, ax=axes[1], fraction=0.046, pad=0.04)
        
        for ax in axes:
            ax.scatter(LANDSLIDE_LON, LANDSLIDE_LAT, marker="*", s=150, color="yellow", edgecolor="black", label="Xinmo Site")
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.legend()
                
        index_name = name.split('\n')[0]
        fig.suptitle(f"Sentinel-2 {index_name} Index: Pre- vs Post-Landslide", fontsize=16)
        fig.tight_layout()
        
    plt.show()

if __name__ == "__main__":
    main()
