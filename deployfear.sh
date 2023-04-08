#!/bin/bash

mv ${HOME}/fear.tgz /mnt/kubedata/fear
pushd /mnt/kubedata/fear
tar zxvf fear.tgz
popd