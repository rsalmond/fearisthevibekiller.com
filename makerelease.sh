#!/bin/bash

tar czf fear.tgz -C ./release .
scp fear.tgz brazen:~/
