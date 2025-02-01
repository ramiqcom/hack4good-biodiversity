import json

import geopandas as gpd
import numpy as np
import rasterio as rio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rasterio import windows
from rasterio.features import rasterize

app = FastAPI()


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
            lc_areas_dict[int(lc_class[x])] = round(float(lc_areas[x]), 2)

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
