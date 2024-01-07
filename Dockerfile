# Stage 1: Build image
FROM python:3.10-slim AS build

# Install dependencies needed for building (e.g., git)
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# Create and activate a virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install dependencies into the virtual environment
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Final image
FROM python:3.10-slim

WORKDIR /usr/src/app

ENV PATH="/venv/bin:$PATH"

# Copy only the virtual environment from the build stage
COPY --from=build /venv /venv

COPY . .

CMD [ "python", "./main.py" ]
