#!/bin/bash

set -eu

ssh brazen -- "cp fear.tgz /mnt/kubedata/fear && pushd /mnt/kubedata/fear && tar zxvf fear.tgz"
