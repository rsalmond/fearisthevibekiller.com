#!/usr/bin/env bash
set -euo pipefail

VM_NAME="dev"
BASE_IMAGE="debian"
USER="admin"

APP_DIR="$(pwd)/app"
SECURE_DIR="$(cd ../fitvk.secure && pwd)"

echo "XXX $SECURE_DIR"

echo "==> Rebuilding VM: $VM_NAME"

# 1. destroy if exists
if tart list | awk '{print $1}' | grep -qx "$VM_NAME"; then
  echo "==> Deleting existing VM"
  tart stop "$VM_NAME" >/dev/null 2>&1 || true
  tart delete "$VM_NAME"
fi

# 2. clone fresh
echo "==> Cloning base image"
tart clone "$BASE_IMAGE" "$VM_NAME"

# 3. boot in background with shares
echo "==> Booting VM"
tart run "$VM_NAME" \
  --no-graphics \
  --dir "app:$APP_DIR:tag=com.apple.virtio-fs.automount" \
  --dir "secure:$SECURE_DIR:tag=com.apple.virtio-fs.automount" &

VM_PID=$!

cleanup() {
  tart stop "$VM_NAME" >/dev/null 2>&1 || true
  kill "$VM_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# 4. wait for IP
echo "==> Waiting for VM IP"
for _ in {1..60}; do
  IP="$(tart ip "$VM_NAME" 2>/dev/null || true)"
  [[ -n "${IP:-}" ]] && break
  sleep 1
done

if [[ -z "${IP:-}" ]]; then
  echo "VM never got an IP"
  exit 1
fi

echo "==> VM IP: $IP"

SSH_OPTS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
)

echo "==> Waiting for SSH"
for _ in {1..60}; do
  if nc -z "$IP" 22 2>/dev/null; then
    break
  fi
  sleep 1
done

echo "==> Uploading Codex state"
tar -C "$HOME" -czf - .codex \
| ssh "${SSH_OPTS[@]}" "$USER@$IP" 'tar -C /home/admin -xzf - && sudo chown -R admin:admin /home/admin/.codex'

# 5. provision (ONE payload)
ssh "${SSH_OPTS[@]}" "$USER@$IP" 'bash -s' <<'EOF'
set -euo pipefail

# packages
sudo apt-get update
sudo apt-get install -y vim iptables iproute2 containerd runc git

# codex
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm i -g @openai/codex

# generate default containerd config
sudo mkdir -p /etc/containerd
sudo containerd config default | sudo tee /etc/containerd/config.toml

# REQUIRED for Kubernetes / modern tooling (even if you never use k8s)
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' \
  /etc/containerd/config.toml

# nerdctl
NERDCTL_VERSION=1.7.6
curl -fsSL \
  https://github.com/containerd/nerdctl/releases/download/v${NERDCTL_VERSION}/nerdctl-full-${NERDCTL_VERSION}-linux-arm64.tar.gz \
| sudo tar -C /usr/local -xz

sudo systemctl enable --now containerd
sudo systemctl enable --now buildkit

# virtiofs automount helper
sudo tee /usr/local/libexec/tart-mount-shares >/dev/null <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

TAG="com.apple.virtio-fs.automount"
ROOT="/mnt/shared"

mkdir -p "$ROOT"
mountpoint -q "$ROOT" || mount -t virtiofs "$TAG" "$ROOT" || exit 0


mkdir -p /app /secure
mountpoint -q /app  || mount --bind "$ROOT/app" /app
mountpoint -q /secure  || mount --bind "$ROOT/secure" /secure

SCRIPT

sudo chmod +x /usr/local/libexec/tart-mount-shares

# systemd unit
sudo tee /etc/systemd/system/tart-shares.service >/dev/null <<'UNIT'
[Unit]
Description=Tart virtiofs shared folders
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/tart-mount-shares
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable tart-shares.service

sudo poweroff
EOF

wait "$VM_PID" || true
trap - EXIT

echo "==> Done. VM '$VM_NAME' ready."
