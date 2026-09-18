FROM python:3.9


WORKDIR /code







COPY ./trankit /code/trankit
#RUN git clone https://github.com/nlp-uoregon/trankit.git
RUN pip install -e /code/trankit

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#COPY ./main.py /code/


CMD ["fastapi", "run", "main.py", "--port", "80"]

#COPY ./app /code/app


#CMD ["fastapi", "run", "app/main.py", "--port", "80"]
