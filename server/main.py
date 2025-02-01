import json

import geopandas as gpd
import numpy as np
import rasterio as rio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rasterio import windows

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
            window=window,
            out_dtype="float32",
            boundless=True,
            fill_value=raster.nodata,
        )
        image[image == raster.nodata] = np.nan

        # Calculate the score
        average_score = float(np.nanmean(image))

        return {
            "score": round(average_score, 2),
            "credits": round(average_score * area / 1e6, 2),
            "geometry": geom_json,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=e)
