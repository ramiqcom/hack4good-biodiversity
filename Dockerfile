FROM python:3.10-bookworm

WORKDIR /usr/src/app

COPY server .

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8080"]
