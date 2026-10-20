#!/bin/bash
# =============================================================================
# Upload QCOW2 Image to Existing KubeVirt Cluster
# =============================================================================
# Quick upload script for when you already have KubeVirt running
#
# Usage:
#   ./upload-to-kubevirt.sh [namespace]
# =============================================================================

set -euo pipefail

NAMESPACE="${1:-rhel-vms}"
QCOW2_IMAGE="${QCOW2_IMAGE:-./output/rhel8.8-fixed.qcow2}"
PVC_NAME="${PVC_NAME:-rhel8-disk}"
PVC_SIZE="${PVC_SIZE:-20Gi}"

echo "📤 Uploading QCOW2 image to KubeVirt..."
echo "   Image: $QCOW2_IMAGE"
echo "   Namespace: $NAMESPACE"
echo "   PVC: $PVC_NAME"
echo ""

# Fail early if the image is missing
if [ ! -f "$QCOW2_IMAGE" ]; then
    echo "❌ Image not found: $QCOW2_IMAGE (set QCOW2_IMAGE to override)" >&2
    exit 1
fi

# Ensure namespace exists
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Check if virtctl is available
if ! command -v virtctl &> /dev/null; then
    echo "❌ virtctl not found!"
    echo ""
    echo "Install virtctl:"
    echo "  VERSION=v1.2.0"
    echo "  wget https://github.com/kubevirt/kubevirt/releases/download/\${VERSION}/virtctl-\${VERSION}-linux-amd64"
    echo "  chmod +x virtctl-\${VERSION}-linux-amd64"
    echo "  sudo mv virtctl-\${VERSION}-linux-amd64 /usr/local/bin/virtctl"
    exit 1
fi

# Resolve the CDI upload proxy URL (UPLOADPROXY_URL overrides the lookup).
# Done outside the virtctl argument list so a failed lookup is not masked.
if [ -z "${UPLOADPROXY_URL:-}" ]; then
    PROXY_IP="$(kubectl get service -n cdi cdi-uploadproxy -o jsonpath='{.spec.clusterIP}')" || PROXY_IP=""
    if [ -z "$PROXY_IP" ]; then
        echo "❌ Could not determine the cdi-uploadproxy ClusterIP." >&2
        echo "   Set UPLOADPROXY_URL (e.g. https://host:443) and retry." >&2
        exit 1
    fi
    UPLOADPROXY_URL="https://${PROXY_IP}:443"
fi

# Upload the image
echo "⏳ Uploading image (this may take several minutes)..."
virtctl image-upload pvc "$PVC_NAME" \
    --namespace="$NAMESPACE" \
    --image-path="$QCOW2_IMAGE" \
    --size="$PVC_SIZE" \
    --insecure \
    --force-bind \
    --uploadproxy-url="$UPLOADPROXY_URL"

echo ""
echo "✅ Upload complete!"
echo ""
echo "Deploy the VM:"
echo "  kubectl apply -f kubevirt-rhel8.8-deployment.yaml"
