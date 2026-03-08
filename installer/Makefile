# HostingSignal Panel Installer — Build Makefile

BINARY_NAME = installer
VERSION = 1.0.0
BUILD_DIR = build
LDFLAGS = -ldflags "-s -w -X main.version=$(VERSION)"

.PHONY: all clean linux-amd64 linux-arm64

all: linux-amd64 linux-arm64

linux-amd64:
	@echo "Building for Linux amd64..."
	@mkdir -p $(BUILD_DIR)
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME)-linux-amd64 main.go
	@echo "✅ $(BUILD_DIR)/$(BINARY_NAME)-linux-amd64"

linux-arm64:
	@echo "Building for Linux arm64..."
	@mkdir -p $(BUILD_DIR)
	GOOS=linux GOARCH=arm64 go build $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME)-linux-arm64 main.go
	@echo "✅ $(BUILD_DIR)/$(BINARY_NAME)-linux-arm64"

clean:
	rm -rf $(BUILD_DIR)

checksums:
	@cd $(BUILD_DIR) && sha256sum * > checksums.txt
	@echo "✅ Checksums generated"
