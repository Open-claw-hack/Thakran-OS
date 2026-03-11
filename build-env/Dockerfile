FROM ubuntu:24.04

# ============================================================================
# Thakran OS — Cross-Compilation Build Environment
# ============================================================================
# A hermetic Docker container to build the bootable ISO image.
# Optimized with layer caching — packages are only downloaded once.
# ============================================================================

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# 1. Install core build tools + ISO generation tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    bc \
    bison \
    flex \
    libelf-dev \
    libssl-dev \
    make \
    wget \
    curl \
    git \
    python3 \
    python3-pip \
    rsync \
    kmod \
    cpio \
    xz-utils \
    zstd \
    dosfstools \
    mtools \
    parted \
    squashfs-tools \
    xorriso \
    grub-pc-bin \
    grub-efi-amd64-bin \
    grub-efi-ia32-bin \
    grub-common \
    grub2-common \
    isolinux \
    syslinux-common \
    symlinks \
    fakeroot \
    debootstrap \
    pkg-config \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup workspace
RUN mkdir -p /workspace/build /workspace/out
WORKDIR /workspace

# The ISO build requires root for chroot/mount operations.
# No need to switch to a non-root user.

CMD ["/bin/bash"]
