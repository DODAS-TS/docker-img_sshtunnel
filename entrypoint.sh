#!/usr/bin/env sh

mkdir -p /opt/dodas/keys
echo "==> Copy keys [TARGET_PRIV_KEY, TARGET_PUB_KEY]"
dodas_cache --wait-for true zookeeper TARGET_PRIV_KEY > /opt/dodas/keys/id_rsa
dodas_cache --wait-for true zookeeper TARGET_PUB_KEY > /opt/dodas/keys/id_rsa.pub
chmod go-rw /opt/dodas/keys/id_rsa
chmod go-w /opt/dodas/keys/id_rsa.pub
echo "==> Check tunnel endpoints"
if [ "$TUNNEL_FROM" == "UNDEFINED" ] || [ -z "$TUNNEL_FROM" ];
then
    export TUNNEL_FROM="$TARGET_SSH_PORT"
fi
if [ "$TUNNEL_TO" == "UNDEFINED" ] || [ -z "$TUNNEL_TO" ];
then
    export TUNNEL_TO="$TARGET_SSH_PORT"
fi
export TARGET_HOST=`dodas_get_target_ip $(dodas_cache --wait-for true zookeeper TARGET_HOST)`
echo "==> Start sshd tunnel: [$TUNNEL_FROM:$TARGET_HOST:$TUNNEL_TO]"
exec ssh -N -g -L $TUNNEL_FROM:$TARGET_HOST:$TUNNEL_TO -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no admin@$TARGET_HOST -p $TARGET_SSH_PORT -i /opt/dodas/keys/id_rsa
