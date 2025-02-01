import json

import geopandas as gpd
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


@app.get("/")
def read_root():
    return "This is GreenCabin Main Server"


@app.get("/biodiversity")
def biodiversity():
    return {"score": 5, "credits": 150}


class Item(BaseModel):
    geometry: dict


@app.post("/biodiversity")
def biodiversity_post(item: Item):
    geom_string = item.geometry
    geom_json = json.dumps(geom_string)
    geom = gpd.read_file(geom_json)
    print(geom)
    # value = calculation.calculate_raster(geom)
    return {"score": 5, "credits": 150, "geometry": geom_json}
