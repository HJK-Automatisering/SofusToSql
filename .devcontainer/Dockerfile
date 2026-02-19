FROM mcr.microsoft.com/devcontainers/python:2-3.14-bookworm

COPY install-msodbc.sh /tmp/install-msodbc.sh

RUN chmod +x /tmp/install-msodbc.sh \
    && /tmp/install-msodbc.sh \
    && rm /tmp/install-msodbc.sh