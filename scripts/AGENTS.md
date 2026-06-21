# Scripts AGENTS.md

## Overview

Shell scripts for starting and stopping the Docker container.

## Files

- `start.sh` — Builds the Docker image and runs the container on port 8000
- `stop.sh` — Stops the running container by name

## Usage

```
./scripts/start.sh   # build & start
./scripts/stop.sh    # stop
```

## Platform support

These POSIX shell scripts work on macOS, Linux, and Windows (WSL/Git Bash).
