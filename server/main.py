import json

import geopandas as gpd
import rasterio as rio
from fastapi import FastAPI
from pydantic import BaseModel

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
    geom_string = item.data.geometry
    geom_json = json.dumps(geom_string)
    geom = gpd.read_file(geom_json)
    print(geom)
    raster = rio.open(
        "https://storage.googleapis.com/gee-ramiqcom-s4g-bucket/hack4good_biodiversity/lc_nl_raster.tif"
    )
    print(raster)
    return {"score": 5, "credits": 150, "geometry": geom_json}
