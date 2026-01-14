#!/bin/bash

# codex resume 019bb86e-0378-7413-a3ca-61a379da77f8

tart run dev \
  --dir "app:$(pwd)/app:tag=com.apple.virtio-fs.automount" \
  --dir "data:$(pwd)/data:ro,tag=com.apple.virtio-fs.automount" \
  --dir "codex:~/.codex:ro,tag=com.apple.virtio-fs.automount" \
  --no-graphics &
