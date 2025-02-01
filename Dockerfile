FROM python:3.10-bookworm

WORKDIR /usr/src/app

COPY server .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["fastapi", "run", "main.py"]
