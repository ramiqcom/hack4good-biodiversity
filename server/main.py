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
soil_classes = json.loads(
    '{"1": "Heavily raised terrain", "2": "Terp", "3": "Heavily leveled", "4": "Heavily processed terrain", "5": "Heavily excavated terrain", "6": "Quarry", "7": "Water", "8": "Swamp", "9": "Built-up area", "10": "Dike", "11": "Mine dump", "12": "Upland", "13": "Land raised with household waste", "14": "Thick peat soils", "15": "Peat soils", "16": "Podzol soils", "17": "Non-calcareous sandy soils", "18": "Brick soils", "19": "Marine clay soils", "20": "Loam soils", "21": "River clay soils", "22": "Defined associations", "23": "Boggy soils", "24": "Very old marine deposits", "25": "Old river clay soils", "26": "Very old fluvial deposits", "27": "Unmatured mineral soils", "28": "Calcareous sandy soils", "29": "Boulder clay soils", "30": "Limestone weathering soils"}'
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
            "https://storage.googleapis.com/gee-ramiqcom-s4g-bucket/hack4good_biodiversity/biodiversity_score_v1.tif"
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

        # Calculate the score
        average_score = float(np.nanmean(image))

        # Land cover
        lc = rio.open(
            "https://storage.googleapis.com/gee-ramiqcom-s4g-bucket/hack4good_biodiversity/lc_category_nl_raster.tif"
        )
        window_lc = windows.from_bounds(*bounds, transform=lc.transform)
        lc_raster = lc.read(
            1,
            window=window_lc,
            out_dtype="float32",
            boundless=True,
            fill_value=lc.nodata,
        )
        lc_raster[(lc_raster == lc.nodata) | mask] = np.nan
        lc_list = np.unique(lc_raster, return_counts=True)
        lc_class = lc_list[0]
        lc_areas = (lc_list[1] / 10) ** 2
        lc_areas_list = []
        for x in range(len(lc_class)):
            class_id = int(lc_class[x])
            lc_areas_list.append(
                {
                    "class_id": class_id,
                    "area": round(float(lc_areas[x]), 2),
                    "label": lc_classes[str(class_id)],
                }
            )

        # Land cover
        soil = rio.open(
            "https://storage.googleapis.com/gee-ramiqcom-s4g-bucket/hack4good_biodiversity/soil_nl_category_raster.tif"
        )
        window_soil = windows.from_bounds(*bounds, transform=soil.transform)
        soil_raster = soil.read(
            1,
            window=window_soil,
            out_dtype="float32",
            boundless=True,
            fill_value=soil.nodata,
        )
        soil_raster[(soil_raster == soil.nodata) | mask] = np.nan
        soil_list = np.unique(soil_raster, return_counts=True)
        soil_class = soil_list[0]
        soil_areas = (soil_list[1] / 10) ** 2
        soil_areas_list = []
        for x in range(len(soil_class)):
            class_id = int(soil_class[x])
            soil_areas_list.append(
                {
                    "class_id": class_id,
                    "area": round(float(soil_areas[x]), 2),
                    "label": soil_classes[str(class_id)],
                }
            )

        return {
            "score": round(average_score, 2),
            "credits": round(average_score * area / 1e6, 2),
            "geometry": geom_json,
            "area": area,
            "land_cover": lc_areas_list,
            "soil": soil_areas_list,
        }
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail=e)
