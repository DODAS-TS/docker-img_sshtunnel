FROM alpine:latest

# OpenSSH Server
RUN apk add --no-cache openssh \
    && sed -i s/#PermitRootLogin.*/PermitRootLogin\ yes/ /etc/ssh/sshd_config \
    && ssh-keygen -A \
    && echo "root:root" | chpasswd

# Python env for cache script
RUN apk add --no-cache python3 py3-requests py3-paramiko py3-psutil \
    && python3 -m ensurepip \
    && pip3 install --upgrade pip setuptools \
    && pip3 install j2cli kazoo

# Cache script
RUN mkdir -p /opt/dodas/cache \
    && mkdir -p /opt/dodas/health_checks
COPY cache.py /opt/dodas/cache/
COPY entrypoint.sh /opt/dodas/cache/
COPY check_ssh_server.py /opt/dodas/health_checks/
COPY check_ssh_tunnel.sh /opt/dodas/health_checks/
RUN ln -sf /opt/dodas/cache/cache.py /usr/local/bin/dodas_cache \
    && ln -sf /opt/dodas/cache/entrypoint.sh /usr/local/bin/dodas_cache_entrypoint \
    && ln -sf /opt/dodas/health_checks/check_ssh_server.py /usr/local/bin/dodas_check_ssh_server \
    && ln -sf /opt/dodas/health_checks/check_ssh_tunnel.sh /usr/local/bin/dodas_check_ssh_tunnel

EXPOSE 22

ENV TUNNEL_FROM="UNDEFINED"
ENV TUNNEL_TO="UNDEFINED"
ENV TARGET_SSH_PORT=31042

CMD ["/usr/local/bin/dodas_cache_entrypoint"]
