FROM alpine:latest

RUN apk add --no-cache openssh \
  && sed -i s/#PermitRootLogin.*/PermitRootLogin\ yes/ /etc/ssh/sshd_config \
  && ssh-keygen -A \
  && echo "root:root" | chpasswd

EXPOSE 22