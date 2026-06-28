# SAR lab 7

By Szymon Skrzypczyk

## Project initialization

I've begun by creating an environment for the lab, I've used miniconda to follow the installation for `mintpy` and other packages, then I used the provided `download_licsar_pre_event.py` to download the required 
files, I've stuck to default **cutoff** timestamp. Then I proceeded to generate a matching `mintpy/` directory using the `licsar_to_mintpy_h5.py` script, I've selected `103.62 32.04 103.68 32.09` as my bounding box for the AOI
as I've found this bbox to include the main area affected by the landslide in 2017, which will be later shown during Sentinel 2 analysis :)

## Mintpy processing

Firstly, I've focused on the provided commands, but since I've run into slight problems with mintpy I switched to code utilization of mintpy. As the base of my analysis I've selected the files inside `mintpy/` directory such as 
`velocity.h5` or/and `timeseries.h5`.

### DEM model

I've generated a DEM model of the area to show its mountainous characteristic, as it can be seen on 2D and 3D representations of the area.

![3D model](figures\study_area_3d_dem.png)

![2D model](figures\study_area_dem.png)


It can be clearly seen that the elevation changes drastically throughout the AOI. A location with lower elevation has been used as a reference point in the next part.

### LOS velocity

I've initially tried several refernce points, but have ended up using the one extracted from `velocity.h5`. It's located in the lower right corner of the AOI. The central point of the AOI is in the landslide area. I've proceeded to generate LOS velocity and temporal coherence charts
as it can be seen on the figure below. The reference point has small LOS velocity change and high temporal coherence, therefore I think it's a good candidate, since it's a rather stable point.

![los](figures\mintpy_velocity_temporal_coherence.png)

Looking at the overall maps, the temporal coherence is pretty mixed, which makes sense for steep, mountainous terrain. There's a clear diagonal band of good coherence (green and yellow) where the radar data is reliable, while the dark purple areas show a lot of noise, likely from vegetation. 
Within the good data zones, the LOS velocity map shows significant surface movement. You can see a prominent red band across the middle and upper right, meaning the ground was moving toward the satellite at up to 15 mm/year. The landslide is located right inside this active deformation zone. Since my chosen reference point is in a highly coherent, stable area with almost zero movement, it gives us a really solid baseline to analyze the actual displacements that caused the event.

![comparison](figures\event_spanning_coherence.png)

Looking at the dates (May 26 to June 7), this map actually shows the pre-event conditions a few weeks before the landslide. The coherence has already dropped across the whole area, showing up as mostly dark purple on the heatmap. This huge loss of signal could mean the slope was already rapidly deforming and accelerating right before it failed. The boxplot confirms the poor data quality: the landslide area has a median coherence of only 0.3, and my reference point is even lower at 0.18.

![ts_los](figures\mintpy_landslide_timeseries.png)

After a huge shift in 2015, the displacement doesn't keep climbing. Instead, it gradually drops and ranges mostly between 25 mm and 40 mm throughout 2016 and early 2017. Right before the landslide date, the displacement is just bouncing around the 25–30 mm mark. This tells me that the slope actually went through its most drastic, sudden movement a couple of years before the collapse, rather than just steadily accelerating right up until it failed.

Mintpy has generated a bunch of different figures that complement the analysis, such as the figure below, showing LOS velocity for different time ranges: 

![mintpy_velocity](mintpy\pic\velocity.png)

I believe that it's consisent with previous chart that showed one massive increase in the values, which here is also visible for a single chart, while the other charts stayed relatively similar.

## Sentinel 1 Pre- and Post-Event

![s1](test_stac2.png)

While it's really hard to spot the landslide just by looking at the raw pre- and post-event radar images (there are small changes though) because of the intense mountain shadows, the difference map on the right makes the impact super clear. By subtracting the "before" image from the "after" image, the map reveals a distinct dark red streak starting at the event site and sliding down into the valley. This red color means the radar signal dropped significantly after the collapse. 
This makes sense because the landslide stripped away all the rough trees and topsoil, leaving behind a smoother surface or a changed slope angle that bounced the radar waves away from the satellite instead of back to it. You can also see a few blue patches near the bottom where the signal actually increased, which is probably where all the parts of the landslide finally piled up. It's also worth noting the increase in post-event VV returned for the area of reference point.

## Sentinel 2 Pre- and Post-Event

![s2](s2_diff.png)

Unlike the radar maps where the damage was hard to spot, these true-color Sentinel-2 images make the landslide impossible to miss. In the pre-event picture on the left, the mountainside and valley look completely undisturbed. But looking at the post-event image on the right, there is a massive, light-grey scar of bare rock and dirt cutting right down the mountain. You can clearly see how the huge pile of debris spread out across the valley floor directly over the Xinmo site, 
completely burying the area and drastically altering the landscape.

## Sentile 2 Pre- and Post-Event indices

### NDVI

![ndvi](ndvi.png)

The charts show a massive change in the index values right over the Xinmo site. Before the event, the area around the star had positive index readings, shown by the light green colors. After the landslide, a huge peach and orange scar appears directly over the site and up the mountain, indicating that the index values plummeted to zero or slightly below. This drastic drop in the index perfectly outlines the exact path and shape of the landslide's destruction.

### NDWI

![ndwi](ndwi.png)

The NDWI charts show a drastic change directly over the landslide area. Before the event, the region around the Xinmo site had negative index readings, appearing as light brown and tan on the map. However, in the post-event map, the values for that specific area suddenly shifted much closer to 0 and slightly positive, creating a distinct light blue scar. Because the index readings for the destroyed zone changed so sharply compared to the untouched surrounding terrain, this sudden shift perfectly outlines the exact shape and runout path of the landslide.

### NBR

![nbr](nbr.png)

The NBR charts show a strong contrast that perfectly highlights the landslide area. Before the event, the index readings around the Xinmo site were relatively mixed, appearing as faint pinks and light greens with values hovering near zero. In the post-event map, the surrounding terrain shifted to high positive values, shown in dark green. However, the exact path of the landslide dropped to slightly negative readings, creating a massive, distinct light pink scar where the values sit right around 0.0 to -0.1. Because the index values for this specific zone are so drastically different from the rest of the map, this sharp drop perfectly outlines the exact shape and runout path of the event.