#!/bin/sh

ZOOKEEPER_TARGET_PUB_KEY=$(dodas_cache --wait-for true zookeeper TARGET_PUB_KEY || echo "None")
LOCAL_PUB_KEY=$(cat /opt/dodas/keys/id_rsa.pub)

if [ "$LOCAL_PUB_KEY" == "$ZOOKEEPER_TARGET_PUB_KEY" ];
then
    exit 0 ;
else
    exit 1 ;
fi