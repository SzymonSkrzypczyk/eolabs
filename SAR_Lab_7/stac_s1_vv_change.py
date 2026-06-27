#!/usr/bin/env python3
"""
Calculate and display Sentinel-1 VV backscatter change (Pre- vs Post-event) 
using STAC catalogs for the 2017-06-24 Xinmo Landslide.
"""

import warnings
import requests
import numpy as np
import matplotlib.pyplot as plt

import pystac_client
import rioxarray

warnings.filterwarnings("ignore")

LANDSLIDE_LON, LANDSLIDE_LAT = 103.655, 32.068
RADIUS = 0.03 # Degrees (approx 3km)
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
        print(f"No Sentinel-1 items found for {date_range}.")
        return None, None
    
    # We take the first item. For a rigorous analysis, matching relative orbit is required.
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
        
    return da_clipped, direction

def main():
    # The Xinmo landslide occurred on 2017-06-24
    pre_date = "2017-06-01/2017-06-23"
    post_date = "2017-06-24/2017-07-15" 
    
    # Get pre-event image
    da_pre, orbit_dir = get_s1_image(pre_date)
    if da_pre is None:
        return
        
    # Get post-event image, strictly enforcing the exact same orbit direction 
    # (Ascending vs Descending) to ensure radar geometry matches!
    da_post, _ = get_s1_image(post_date, orbit_direction=orbit_dir)
    if da_post is None:
        print("Could not find a matching post-event image with the same orbit direction.")
        return
        
    # Ensure they have the exact same grid and shape before subtracting
    da_post = da_post.rio.reproject_match(da_pre)
    
    # Convert linear power (RTC values) to Decibels (dB)
    # Using 1e-6 to avoid log10(0)
    pre_db = 10 * np.log10(np.clip(da_pre.values, 1e-6, None))
    post_db = 10 * np.log10(np.clip(da_post.values, 1e-6, None))
    
    # Calculate difference (Post - Pre)
    # Negative values mean a drop in backscatter (e.g., smoother surface, landslide debris, collapsed buildings)
    # Positive values mean an increase in backscatter (e.g., rougher surface, new structures)
    diff_db = post_db - pre_db
    
    # Calculate bounds for plotting
    bounds = da_pre.rio.bounds()
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]
    
    # Plotting
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Normalize dB scales for Pre/Post
    vmin, vmax = np.percentile(pre_db[~np.isnan(pre_db)], [5, 95])
    
    im0 = axes[0].imshow(pre_db, cmap="gray", extent=extent, origin="upper", vmin=vmin, vmax=vmax)
    axes[0].set_title(f"Pre-Event VV ({orbit_dir})")
    fig.colorbar(im0, ax=axes[0], label="dB", shrink=0.7)
    
    im1 = axes[1].imshow(post_db, cmap="gray", extent=extent, origin="upper", vmin=vmin, vmax=vmax)
    axes[1].set_title(f"Post-Event VV ({orbit_dir})")
    fig.colorbar(im1, ax=axes[1], label="dB", shrink=0.7)
    
    # Normalize Difference scale centered at 0
    diff_max = np.nanpercentile(np.abs(diff_db), 95)
    im2 = axes[2].imshow(diff_db, cmap="RdBu", extent=extent, origin="upper", vmin=-diff_max, vmax=diff_max)
    axes[2].set_title("VV Difference (Post - Pre)")
    fig.colorbar(im2, ax=axes[2], label="Δ dB", shrink=0.7)
    
    for ax in axes:
        ax.scatter(LANDSLIDE_LON, LANDSLIDE_LAT, marker="*", s=150, color="yellow", edgecolor="black", label="Event Site")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.legend(loc="upper right")
        
    plt.suptitle("Sentinel-1 VV Backscatter Change Detection (2017-06-24 Xinmo Landslide)", fontsize=16)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
