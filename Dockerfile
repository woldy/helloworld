# Agenthon 2026 Track 1 — submission #1 (deterministic, no model; models: [])
FROM python:3.13-slim

LABEL qfbench2.interface_version="2.0" \
      org.opencontainers.image.title="woldywei-agenthon-t1-sub1" \
      org.opencontainers.image.description="Agenthon 2026 Track 1 deterministic agent (submission #1: BS-Greeks closed form + instruction-derived floor)" \
      org.opencontainers.image.licenses="Apache-2.0"

# Build-time dependency install (evaluation network is restricted; everything
# the agent needs ships in the image). Wheels pre-downloaded for cp313 on the
# host (container build network has no egress) and installed fully offline.
COPY wheels-cp313/ /tmp/wheels/
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels \
      numpy pandas pyarrow \
 && rm -rf /tmp/wheels

WORKDIR /app
COPY agent/ /app/agent/
COPY solve /usr/local/bin/solve
RUN chmod 0755 /usr/local/bin/solve
# No USER directive on purpose: the harness and conformance.sh mount host-owned
# output dirs without --user, so the image must write regardless of mount
# ownership; the organizer's Development runtime enforces its own non-root user.
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
# No ENTRYPOINT on purpose: the verb must resolve from PATH.
