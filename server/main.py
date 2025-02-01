from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return "This is GreenCabin Main Server"


@app.get("/biodiversity")
def biodiversity():
    return {"score": 5, "credits": 150}
