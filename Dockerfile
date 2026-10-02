FROM condaforge/miniforge3:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    PIP_CONSTRAINT=/code/docker/pip-constraints.txt \
    PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu
WORKDIR /code

# Use the project Conda environment and a CPU PyTorch wheel for inference.
COPY ./trankit /code/trankit
COPY ./requirements.txt ./environment.yml /code/
COPY ./docker/pip-constraints.txt /code/docker/pip-constraints.txt
RUN conda env create -f /code/environment.yml && conda clean --all --yes
ENV PATH=/opt/conda/envs/trankit-fnbr/bin:$PATH

COPY ./trankit_fnbr /code/trankit_fnbr
COPY ./main.py /code/main.py

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:80/health/ready', timeout=5).close()"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "1"]
