import json

import geopandas as gpd
import numpy as np
import rasterio as rio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rasterio import windows
from rasterio.features import rasterize

app = FastAPI()

lc_classes = json.loads(
    '{"10": "Railway site", "11": "Main road", "12": "Airport", "20": "Residential area", "21": "Retail and catering", "22": "Public facility", "23": "Socio-cultural facility", "24": "Industrial estate", "30": "Landfill", "31": "Wreck storage site", "32": "Cemetery", "33": "Mineral extraction site", "34": "Construction site", "35": "Semi-paved other terrain", "40": "Park and public garden", "41": "Sports field", "42": "Allotment garden", "43": "Day recreation area", "44": "Recreational accommodation area", "50": "Greenhouse horticulture", "51": "Other agricultural terrain", "60": "Forest", "61": "Open dry natural terrain", "62": "Open wet natural terrain", "70": "IJsselmeer & Markermeer", "71": "Closed sea arm", "72": "Rhine & Meuse", "73": "Randmeer", "74": "Reservoir", "75": "Water with recreational function", "76": "Water with mineral extraction function", "77": "Fluid and/or silt field", "78": "Other inland water", "80": "Wadden Sea, Eems & Dollard", "81": "Oosterschelde", "82": "Westerschelde", "83": "North Sea"}'
)


@app.get("/")
def read_root():
    return "This is GreenCabin Main Server"


@app.get("/biodiversity")
def biodiversity():
    return {"score": 5, "credits": 150}


class Data(BaseModel):
    geometry: dict


class Item(BaseModel):
    data: Data


@app.post("/biodiversity")
def biodiversity_post(item: Item):
    try:
        # Load the geometry
        geom_string = item.data.geometry
        geom_json = json.dumps(geom_string)
        geom = gpd.read_file(geom_json)

        # Calculate area of the geometry
        area = geom.union_all().area

        # Open the raster
        raster = rio.open(
            "https://storage.googleapis.com/gee-ramiqcom-s4g-bucket/hack4good_biodiversity/lc_nl_raster.tif"
        )
        transform = raster.transform
        bounds = geom.total_bounds
        window = windows.from_bounds(*bounds, transform=transform)
        image = raster.read(
            1,
            window=window,
            out_dtype="float32",
            boundless=True,
            fill_value=raster.nodata,
        )
        image[image == raster.nodata] = np.nan

        # Create raster from geometry
        raster_geom = rasterize(
            [(geo, 1) for geo in geom.geometry],
            out_shape=image.shape,
            nodata=0,
            fill=1,
            dtype="uint8",
            transform=windows.transform(window, transform),
        )
        mask = raster_geom == 0

        # Mask image with raster geom
        image[mask] = np.nan

        # Land cover
        lc = rio.open(
            "https://storage.googleapis.com/gee-ramiqcom-s4g-bucket/hack4good_biodiversity/lc_category_nl_raster.tif"
        )
        lc_raster = lc.read(
            1,
            window=window,
            out_dtype="float32",
            boundless=True,
            fill_value=lc.nodata,
        )
        lc_raster[(lc_raster == lc.nodata) | mask] = np.nan
        lc_list = np.unique(lc_raster, return_counts=True)
        lc_class = lc_list[0]
        lc_areas = (lc_list[1] / 10) ** 2
        lc_areas_dict = {}
        for x in range(len(lc_class)):
            lc_areas_dict[lc_classes[str(int(lc_class[x]))]] = round(
                float(lc_areas[x]), 2
            )

        # Calculate the score
        average_score = float(np.nanmean(image))

        return {
            "score": round(average_score, 2),
            "credits": round(average_score * area / 1e6, 2),
            "geometry": geom_json,
            "area": area,
            "land_cover": lc_areas_dict,
        }
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail=e)
