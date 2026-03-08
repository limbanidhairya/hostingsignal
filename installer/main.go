// HostingSignal Panel — Compiled Installer Binary
// Provides interactive installation with OS detection, dependency checks,
// web server choice, progress display, and license activation.
//
// Build: go build -o installer main.go
// Usage: ./installer

package main

import (
	"bufio"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"time"
)

const (
	version       = "1.0.0"
	installDir    = "/usr/local/hostingsignal"
	mirrorURL     = "https://mirror.hostingsignal.com"
	licenseURL    = "https://license.hostingsignal.com"
	installScript = "install.sh"
	banner        = `
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ██╗  ██╗ ██████╗ ███████╗████████╗██╗███╗   ██╗ ██████╗  ║
║     ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝██║████╗  ██║██╔════╝  ║
║     ███████║██║   ██║███████╗   ██║   ██║██╔██╗ ██║██║  ███╗ ║
║     ██╔══██║██║   ██║╚════██║   ██║   ██║██║╚██╗██║██║   ██║ ║
║     ██║  ██║╚██████╔╝███████║   ██║   ██║██║ ╚████║╚██████╔╝ ║
║     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═══╝ ╚═════╝  ║
║              ███████╗██╗ ██████╗ ███╗   ██╗ █████╗ ██╗        ║
║              ██╔════╝██║██╔════╝ ████╗  ██║██╔══██╗██║        ║
║              ███████╗██║██║  ███╗██╔██╗ ██║███████║██║        ║
║              ╚════██║██║██║   ██║██║╚██╗██║██╔══██║██║        ║
║              ███████║██║╚██████╔╝██║ ╚████║██║  ██║███████╗   ║
║              ╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝   ║
║                                                               ║
║              Hosting Control Panel Installer                  ║
║                       v%s                              ║
╚═══════════════════════════════════════════════════════════════╝
`
)

type OSInfo struct {
	Name    string
	Version string
	ID      string
	Arch    string
}

func main() {
	if os.Getuid() != 0 {
		fmt.Println("❌ This installer must be run as root")
		fmt.Println("   Usage: sudo ./installer")
		os.Exit(1)
	}

	fmt.Printf(banner, version)
	fmt.Println()

	// Step 1: Detect OS
	osInfo := detectOS()
	if osInfo == nil {
		fmt.Println("❌ Unsupported operating system")
		fmt.Println("   Supported: Ubuntu 22+, Ubuntu 24+, Debian 12, AlmaLinux 9")
		os.Exit(1)
	}
	printStep(1, "OS Detection", fmt.Sprintf("%s %s (%s)", osInfo.Name, osInfo.Version, osInfo.Arch))

	// Step 2: Check prerequisites
	printStep(2, "Prerequisites Check", "Checking system requirements...")
	checkPrerequisites()

	// Step 3: Web server choice
	webServer := promptWebServer()
	printStep(3, "Web Server", fmt.Sprintf("Selected: %s", webServer))

	// Step 4: License key
	licenseKey := promptLicenseKey()
	printStep(4, "License", "License key received")

	// Step 5: Confirmation
	fmt.Println()
	fmt.Println("╔═══════════════════════════════════════╗")
	fmt.Println("║       Installation Summary            ║")
	fmt.Println("╠═══════════════════════════════════════╣")
	fmt.Printf("║  OS:         %-24s ║\n", osInfo.Name+" "+osInfo.Version)
	fmt.Printf("║  Web Server: %-24s ║\n", webServer)
	fmt.Printf("║  Install to: %-24s ║\n", installDir)
	fmt.Println("╚═══════════════════════════════════════╝")
	fmt.Println()

	if !promptConfirm("Proceed with installation?") {
		fmt.Println("Installation cancelled.")
		os.Exit(0)
	}

	// Step 6: Download and run install script
	printStep(5, "Download", "Downloading installation package...")
	scriptPath, err := downloadInstallScript()
	if err != nil {
		fmt.Printf("❌ Download failed: %v\n", err)
		os.Exit(1)
	}

	// Step 7: Run installation
	printStep(6, "Installing", "Running installation (this may take several minutes)...")
	err = runInstall(scriptPath, webServer, licenseKey, osInfo)
	if err != nil {
		fmt.Printf("❌ Installation failed: %v\n", err)
		os.Exit(1)
	}

	// Step 8: Complete
	fmt.Println()
	fmt.Println("╔═══════════════════════════════════════════════════╗")
	fmt.Println("║           ✅ Installation Complete!               ║")
	fmt.Println("╠═══════════════════════════════════════════════════╣")
	fmt.Println("║                                                   ║")
	fmt.Println("║  Panel URL:    https://<server-ip>:3000           ║")
	fmt.Println("║  API URL:      https://<server-ip>:8000           ║")
	fmt.Println("║                                                   ║")
	fmt.Println("║  Complete setup at: https://<server-ip>:3000/setup║")
	fmt.Println("║                                                   ║")
	fmt.Println("║  CLI:  hsctl status                               ║")
	fmt.Println("║  Logs: hsctl logs                                 ║")
	fmt.Println("║                                                   ║")
	fmt.Println("╚═══════════════════════════════════════════════════╝")
}

func detectOS() *OSInfo {
	info := &OSInfo{Arch: runtime.GOARCH}

	data, err := os.ReadFile("/etc/os-release")
	if err != nil {
		return nil
	}

	lines := strings.Split(string(data), "\n")
	for _, line := range lines {
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := parts[0]
		val := strings.Trim(parts[1], "\"")

		switch key {
		case "NAME":
			info.Name = val
		case "VERSION_ID":
			info.Version = val
		case "ID":
			info.ID = val
		}
	}

	// Validate supported OS
	switch info.ID {
	case "ubuntu":
		if info.Version >= "22" {
			return info
		}
	case "debian":
		if info.Version >= "12" {
			return info
		}
	case "almalinux", "rocky":
		if info.Version >= "9" {
			return info
		}
	}

	return nil
}

func checkPrerequisites() {
	checks := []struct {
		name    string
		check   func() bool
	}{
		{"CPU cores >= 1", func() bool { return runtime.NumCPU() >= 1 }},
		{"Architecture supported", func() bool { return runtime.GOARCH == "amd64" || runtime.GOARCH == "arm64" }},
		{"curl available", func() bool { return commandExists("curl") }},
		{"systemctl available", func() bool { return commandExists("systemctl") }},
	}

	for _, c := range checks {
		if c.check() {
			fmt.Printf("   ✅ %s\n", c.name)
		} else {
			fmt.Printf("   ❌ %s\n", c.name)
		}
	}
}

func commandExists(cmd string) bool {
	_, err := exec.LookPath(cmd)
	return err == nil
}

func promptWebServer() string {
	fmt.Println()
	fmt.Println("┌─────────────────────────────────────┐")
	fmt.Println("│  Select Web Server Engine:           │")
	fmt.Println("│                                      │")
	fmt.Println("│  1) OpenLiteSpeed (recommended)      │")
	fmt.Println("│  2) Apache                           │")
	fmt.Println("└─────────────────────────────────────┘")
	fmt.Print("  Enter choice [1/2]: ")

	reader := bufio.NewReader(os.Stdin)
	input, _ := reader.ReadString('\n')
	input = strings.TrimSpace(input)

	switch input {
	case "2":
		return "apache"
	default:
		return "openlitespeed"
	}
}

func promptLicenseKey() string {
	fmt.Println()
	fmt.Print("  Enter license key (HS-XXXX-XXXX-XXXX-XXXX): ")
	reader := bufio.NewReader(os.Stdin)
	input, _ := reader.ReadString('\n')
	return strings.TrimSpace(input)
}

func promptConfirm(prompt string) bool {
	fmt.Printf("  %s [y/N]: ", prompt)
	reader := bufio.NewReader(os.Stdin)
	input, _ := reader.ReadString('\n')
	input = strings.ToLower(strings.TrimSpace(input))
	return input == "y" || input == "yes"
}

func printStep(num int, title, detail string) {
	fmt.Printf("\n  [%d/6] %s\n", num, title)
	fmt.Printf("        %s\n", detail)
}

func downloadInstallScript() (string, error) {
	url := fmt.Sprintf("%s/%s", mirrorURL, installScript)
	tmpPath := "/tmp/hostingsignal-install.sh"

	resp, err := http.Get(url)
	if err != nil {
		// Fallback: use bundled install script
		fmt.Println("        ⚠ Mirror unavailable, using embedded installer")
		return "/usr/local/hostingsignal/installer/install.sh", nil
	}
	defer resp.Body.Close()

	out, err := os.Create(tmpPath)
	if err != nil {
		return "", err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return "", err
	}

	os.Chmod(tmpPath, 0755)
	fmt.Println("        ✅ Download complete")
	return tmpPath, nil
}

func runInstall(scriptPath, webServer, licenseKey string, osInfo *OSInfo) error {
	env := os.Environ()
	env = append(env,
		fmt.Sprintf("HS_WEB_SERVER=%s", webServer),
		fmt.Sprintf("HS_LICENSE_KEY=%s", licenseKey),
		fmt.Sprintf("HS_OS_ID=%s", osInfo.ID),
		fmt.Sprintf("HS_OS_VERSION=%s", osInfo.Version),
		"HS_NON_INTERACTIVE=1",
	)

	cmd := exec.Command("bash", scriptPath)
	cmd.Env = env
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	startTime := time.Now()
	err := cmd.Run()
	elapsed := time.Since(startTime)

	if err != nil {
		return fmt.Errorf("install script exited with error: %w", err)
	}

	fmt.Printf("        ✅ Installation completed in %s\n", elapsed.Round(time.Second))
	return nil
}
