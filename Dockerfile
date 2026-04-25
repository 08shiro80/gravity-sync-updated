FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       rsync openssh-client inotify-tools sudo \
    && rm -rf /var/lib/apt/lists/*

COPY gravity-sync /usr/local/bin/gravity-sync
RUN chmod +x /usr/local/bin/gravity-sync

RUN mkdir -p /etc/gravity-sync

VOLUME ["/etc/gravity-sync"]

CMD ["gravity-sync", "version"]
