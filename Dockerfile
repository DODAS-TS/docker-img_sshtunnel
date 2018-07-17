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
RUN mkdir -p /opt/dodas
COPY cache.py /opt/dodas/
RUN ln -s /opt/dodas/cache.py /usr/local/sbin/dodas_cache

EXPOSE 22

ENV TUNNEL_FROM="UNDEFINED"
ENV TUNNEL_TO="UNDEFINED"
ENV TARGET_SSH_PORT=31042

CMD ["/usr/sbin/sshd", "-D"]
