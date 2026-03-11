# ============================================================================
# Thakran OS — Master Build System
# ============================================================================
# Usage:
#   make all          - Build everything
#   make kernel       - Build the custom kernel
#   make ai-engine    - Build the AI core engine
#   make desktop      - Build the desktop shell
#   make iso          - Generate bootable ISO
#   make dev-setup    - Set up development environment
#   make clean        - Clean all build artifacts
# ============================================================================

.PHONY: all kernel ai-engine desktop iso dev-setup clean help

# Version
VERSION := $(shell cat VERSION)

# Directories
BUILD_DIR     := build
KERNEL_DIR    := kernel
AI_DIR        := ai
DESKTOP_DIR   := desktop
APPS_DIR      := apps
INSTALLER_DIR := installer
SYSTEM_DIR    := system

# Kernel config
KERNEL_VERSION := 6.12
KERNEL_ARCH    := x86_64
KERNEL_CONFIG  := $(KERNEL_DIR)/config/$(KERNEL_ARCH).config

# Colors for output
COLOR_RESET  := \033[0m
COLOR_GREEN  := \033[32m
COLOR_BLUE   := \033[34m
COLOR_YELLOW := \033[33m
COLOR_CYAN   := \033[36m

# Default target
all: kernel ai-engine desktop apps iso
	@echo "$(COLOR_GREEN)✓ Thakran OS $(VERSION) — Build Complete$(COLOR_RESET)"

# ─── Development Setup ─────────────────────────────────────────────────────
dev-setup:
	@echo "$(COLOR_CYAN)⚙ Setting up Thakran OS development environment...$(COLOR_RESET)"
	@bash scripts/dev-setup.sh
	@echo "$(COLOR_GREEN)✓ Development environment ready$(COLOR_RESET)"

# ─── Kernel ────────────────────────────────────────────────────────────────
kernel:
	@echo "$(COLOR_BLUE)🐧 Building Thakran OS Kernel $(KERNEL_VERSION)...$(COLOR_RESET)"
	@mkdir -p $(BUILD_DIR)/kernel
	@bash $(KERNEL_DIR)/build.sh $(KERNEL_CONFIG) $(BUILD_DIR)/kernel
	@echo "$(COLOR_GREEN)✓ Kernel build complete$(COLOR_RESET)"

# ─── AI Core Engine ───────────────────────────────────────────────────────
ai-engine:
	@echo "$(COLOR_YELLOW)🧠 Building AI Core Engine (thakran-aid)...$(COLOR_RESET)"
	@mkdir -p $(BUILD_DIR)/ai
	@cp -r $(AI_DIR)/* $(BUILD_DIR)/ai/
	@echo "$(COLOR_GREEN)✓ AI engine build complete$(COLOR_RESET)"

# ─── Desktop Shell ────────────────────────────────────────────────────────
desktop:
	@echo "$(COLOR_CYAN)🖥️  Building Thakran Desktop Shell...$(COLOR_RESET)"
	@mkdir -p $(BUILD_DIR)/desktop
	@cp -r $(DESKTOP_DIR)/* $(BUILD_DIR)/desktop/
	@echo "$(COLOR_GREEN)✓ Desktop shell build complete$(COLOR_RESET)"

# ─── Core Apps ─────────────────────────────────────────────────────────────
apps:
	@echo "$(COLOR_BLUE)📦 Building Core Applications...$(COLOR_RESET)"
	@mkdir -p $(BUILD_DIR)/apps
	@cp -r $(APPS_DIR)/* $(BUILD_DIR)/apps/
	@echo "$(COLOR_GREEN)✓ Apps build complete$(COLOR_RESET)"

# ─── ISO Generation ───────────────────────────────────────────────────────
iso: kernel ai-engine desktop apps
	@echo "$(COLOR_YELLOW)💿 Generating Thakran OS ISO image...$(COLOR_RESET)"
	@mkdir -p $(BUILD_DIR)/iso
	@bash $(INSTALLER_DIR)/iso-builder/build-iso.sh $(BUILD_DIR) $(VERSION)
	@echo "$(COLOR_GREEN)✓ ISO generated: $(BUILD_DIR)/thakran-os-$(VERSION).iso$(COLOR_RESET)"

# ─── Clean ─────────────────────────────────────────────────────────────────
clean:
	@echo "$(COLOR_YELLOW)🧹 Cleaning build artifacts...$(COLOR_RESET)"
	@rm -rf $(BUILD_DIR)
	@echo "$(COLOR_GREEN)✓ Clean complete$(COLOR_RESET)"

# ─── Help ──────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "$(COLOR_CYAN)Thakran OS Build System$(COLOR_RESET)"
	@echo "$(COLOR_CYAN)======================$(COLOR_RESET)"
	@echo ""
	@echo "  make all          Build everything"
	@echo "  make kernel       Build the custom kernel"
	@echo "  make ai-engine    Build the AI core engine"
	@echo "  make desktop      Build the desktop shell"
	@echo "  make apps         Build core applications"
	@echo "  make iso          Generate bootable ISO"
	@echo "  make dev-setup    Set up dev environment"
	@echo "  make clean        Clean build artifacts"
	@echo "  make help         Show this help"
	@echo ""
