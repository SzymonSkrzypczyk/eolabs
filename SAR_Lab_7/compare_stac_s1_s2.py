#!/usr/bin/env python3
"""
Compare and display Sentinel-1 (SAR) and Sentinel-2 (Optical) images 
from STAC catalogs for the Xinmo Landslide Area of Interest.
"""

import warnings
import requests
import numpy as np
import matplotlib.pyplot as plt

import pystac_client
import rioxarray

warnings.filterwarnings("ignore")

LANDSLIDE_LON, LANDSLIDE_LAT = 103.655, 32.068
RADIUS = 0.03
AOI = [
    LANDSLIDE_LON - RADIUS,
    LANDSLIDE_LAT - RADIUS,
    LANDSLIDE_LON + RADIUS,
    LANDSLIDE_LAT + RADIUS
]
def get_planetary_computer_sas_token(collection: str) -> str:
    """Fetch anonymous SAS token for Microsoft Planetary Computer."""
    url = f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{collection}"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json().get("token", "")
    except Exception as e:
        print(f"Warning: Failed to fetch SAS token: {e}")
    return ""

def get_s1_image(date_range: str, orbit_direction: str = None):
    print(f"Searching Planetary Computer for Sentinel-1 RTC ({date_range})...")
    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    
    query = {}
    if orbit_direction:
        query["sat:orbit_state"] = {"eq": orbit_direction}
        
    search = catalog.search(
        collections=["sentinel-1-rtc"],
        bbox=AOI,
        datetime=date_range,
        query=query if query else None
    )
    items = list(search.items())
    if not items:
        print("No Sentinel-1 items found.")
        return None
    
    item = items[0]
    direction = item.properties.get("sat:orbit_state", "Unknown")
    print(f"Found S1 item: {item.id} (Orbit: {direction})")
    
    sas_token = get_planetary_computer_sas_token("sentinel-1-rtc")
    url = item.assets["vv"].href
    if sas_token:
        url += "?" + sas_token
        
    da = rioxarray.open_rasterio(url)
    da_clipped = da.rio.clip_box(*AOI, crs="EPSG:4326")
    da_clipped = da_clipped.rio.reproject("EPSG:4326")
    
    if "band" in da_clipped.dims:
        da_clipped = da_clipped.squeeze("band").drop_vars("band")
        
    return da_clipped, da_clipped.rio.bounds(), direction

def get_s2_image(date_range: str):
    print(f"Searching Earth Search for Sentinel-2 L2A ({date_range})...")
    catalog = pystac_client.Client.open("https://earth-search.aws.element84.com/v1")
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=AOI,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": 20}}
    )
    items = list(search.items())
    if not items:
        print("No Sentinel-2 items found.")
        return None
    
    items = sorted(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
    item = items[0]
    print(f"Found S2 item: {item.id} (Cloud cover: {item.properties.get('eo:cloud_cover', 'N/A')}%)")
    
    bands = ["red", "green", "blue"]
    das = []
    
    for b in bands:
        da = rioxarray.open_rasterio(item.assets[b].href)
        da_clipped = da.rio.clip_box(*AOI, crs="EPSG:4326")
        
        if len(das) == 0:
            da_clipped = da_clipped.rio.reproject("EPSG:4326")
        else:
            da_clipped = da_clipped.rio.reproject_match(das[0])
            
        if "band" in da_clipped.dims:
            da_clipped = da_clipped.squeeze("band").drop_vars("band")
            
        da_clipped = da_clipped.astype("float32") / 10000.0
        das.append(da_clipped)
    
    rgb = np.stack([das[0], das[1], das[2]], axis=-1)
    
    # Brighten the RGB image slightly for better visualization
    rgb = np.clip(rgb * 2.5, 0, 1)
    return rgb, das[0].rio.bounds()

def main():
    # The Xinmo landslide occurred on 2017-06-24
    s1_pre_date = "2017-06-01/2017-06-23"
    s1_post_date = "2017-06-24/2017-07-15" 
    s2_pre_date = "2017-01-01/2017-06-23"
    s2_post_date = "2017-06-24/2017-08-15"
    
    s1_pre_result = get_s1_image(s1_pre_date)
    s1_post_result = None
    if s1_pre_result:
        _, _, orbit_dir = s1_pre_result
        s1_post_result = get_s1_image(s1_post_date, orbit_direction=orbit_dir)
        
    s2_pre_result = get_s2_image(s2_pre_date)
    s2_post_result = get_s2_image(s2_post_date)
    
    fig_s1, axes_s1 = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot S1 Pre
    if s1_pre_result is not None:
        da_s1, s1_bounds, _ = s1_pre_result
        s1_vals = da_s1.values
        s1_db = 10 * np.log10(np.clip(s1_vals, 1e-6, None))
        vmin, vmax = np.percentile(s1_db[~np.isnan(s1_db)], [5, 95])
        s1_extent = [s1_bounds[0], s1_bounds[2], s1_bounds[1], s1_bounds[3]]
        im00 = axes_s1[0].imshow(s1_db, cmap="gray", extent=s1_extent, origin="upper", vmin=vmin, vmax=vmax) 
        axes_s1[0].set_title("Pre-Landslide Sentinel-1 VV (SAR)")
        fig_s1.colorbar(im00, ax=axes_s1[0], label="Approx dB", shrink=0.8)

    # Plot S1 Post
    if s1_post_result is not None:
        da_s1, s1_bounds, _ = s1_post_result
        s1_vals = da_s1.values
        s1_db = 10 * np.log10(np.clip(s1_vals, 1e-6, None))
        vmin, vmax = np.percentile(s1_db[~np.isnan(s1_db)], [5, 95])
        s1_extent = [s1_bounds[0], s1_bounds[2], s1_bounds[1], s1_bounds[3]]
        im01 = axes_s1[1].imshow(s1_db, cmap="gray", extent=s1_extent, origin="upper", vmin=vmin, vmax=vmax) 
        axes_s1[1].set_title("Post-Landslide Sentinel-1 VV (SAR)")
        fig_s1.colorbar(im01, ax=axes_s1[1], label="Approx dB", shrink=0.8)
        
    for ax in axes_s1:
        ax.scatter(LANDSLIDE_LON, LANDSLIDE_LAT, marker="*", s=150, color="red", edgecolor="black", label="Xinmo Site")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.legend()
        
    fig_s1.suptitle("Sentinel-1 Imagery: Pre- vs Post-Landslide (2017-06-24)", fontsize=16)
    fig_s1.tight_layout()

    fig_s2, axes_s2 = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot S2 Pre
    if s2_pre_result is not None:
        rgb_s2, s2_bounds = s2_pre_result
        s2_extent = [s2_bounds[0], s2_bounds[2], s2_bounds[1], s2_bounds[3]]
        axes_s2[0].imshow(rgb_s2, extent=s2_extent, origin="upper")
        axes_s2[0].set_title("Pre-Landslide Sentinel-2 True Color")
        
    # Plot S2 Post
    if s2_post_result is not None:
        rgb_s2, s2_bounds = s2_post_result
        s2_extent = [s2_bounds[0], s2_bounds[2], s2_bounds[1], s2_bounds[3]]
        axes_s2[1].imshow(rgb_s2, extent=s2_extent, origin="upper")
        axes_s2[1].set_title("Post-Landslide Sentinel-2 True Color")
    
    for ax in axes_s2:
        ax.scatter(LANDSLIDE_LON, LANDSLIDE_LAT, marker="*", s=150, color="red", edgecolor="black", label="Xinmo Site")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.legend()
        
    fig_s2.suptitle("Sentinel-2 Imagery: Pre- vs Post-Landslide (2017-06-24)", fontsize=16)
    fig_s2.tight_layout()
    
    plt.show()

if __name__ == "__main__":
    main()
