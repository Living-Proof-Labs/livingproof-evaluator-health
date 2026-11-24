# SPDX-License-Identifier: Apache-2.0
FROM ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 AS uv
FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS development
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /uvx /usr/local/bin/
ADD --checksum=sha256:680859dbb4d881a9c72d4d9a8f510825450849af8567deacd7302c01124416fb https://github.com/go-task/task/releases/download/v3.54.0/task_linux_amd64.tar.gz /tmp/task-amd64.tar.gz
ADD --checksum=sha256:d7189d439d4a6058e39e1b2acd7c8b27acd4856691b408f23b242e4294e1df5b https://github.com/go-task/task/releases/download/v3.54.0/task_linux_arm64.tar.gz /tmp/task-arm64.tar.gz
ARG TARGETARCH
RUN tar -xzf /tmp/task-${TARGETARCH}.tar.gz -C /usr/local/bin task && rm /tmp/task-*.tar.gz
ENV UV_PYTHON_DOWNLOADS=never UV_CACHE_DIR=/tmp/uv-cache
WORKDIR /workspace
