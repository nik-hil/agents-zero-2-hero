FROM python:3.14-slim

# Create non-root user
RUN useradd -m agent

WORKDIR /app

# Copy app
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN apt update && apt install -y ripgrep

# Create workspace
RUN mkdir -p /app/workspace && \
    chown -R agent:agent /app

USER agent

ENV PYTHONUNBUFFERED=1

# Default to running the coding agent directly
CMD ["sleep", "3600"]  
