FROM python:3.11-slim

WORKDIR /job

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/job
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./

# Install CPU-specific torch and torchvision to avoid large downloads and network errors
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

CMD ["python", "main.py"]
