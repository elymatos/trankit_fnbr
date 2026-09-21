FROM python:3.9-slim

WORKDIR /code

COPY ./trankit /code/trankit
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./trankit_fnbr /code/trankit_fnbr
COPY ./main.py /code/main.py

CMD ["fastapi", "run", "main.py", "--port", "80"]
