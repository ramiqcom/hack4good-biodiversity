FROM python:3.10-bookworm

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY server ./server

CMD ["fastapi", "run", "server/main.py"]
