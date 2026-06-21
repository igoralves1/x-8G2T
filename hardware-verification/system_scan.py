#!/usr/bin/env python3
"""
COMPREHENSIVE SYSTEM SCAN - AI WORKLOAD READINESS
Full hardware and software verification for AI/ML development

================================================================================
WHAT THIS SCRIPT TESTS
================================================================================
Step | What it Tests              | Why it Matters
-----|----------------------------|-----------------------------------------------
  1  | System Overview            | Identifies OS, hostname, boot time
  2  | CPU Information            | Checks cores, frequency, cache, virtualization
  3  | BIOS/Firmware              | Verifies firmware version and compatibility
  4  | Memory (RAM)               | Checks capacity, speed, type, usage
  5  | Storage (SSD/NVMe)         | Checks drives, capacity, health, performance
  6  | Network                    | Verifies connectivity, IPs, speed, DNS
  7  | PyTorch installation       | Ensures the AI framework is installed
  8  | CUDA availability          | Confirms GPU drivers work with PyTorch
  9  | GPU detection              | Identifies your GPU and its specs
 10  | Basic GPU computation      | Verifies the GPU can do math correctly
 11  | GPU Performance            | Benchmarks your GPU's speed
 12  | GPU Memory allocation      | Tests VRAM allocation and limits
 13  | NVIDIA Driver info         | Shows NVIDIA driver details (nvidia-smi)
 14  | AI/ML Software & Venv      | Checks installed frameworks and virtual environment
 15  | CPU Stress Test            | Tests CPU performance under load
 16  | GPU Stress Test            | Tests GPU performance under load
 17  | Storage Speed Test         | Measures read/write speeds
 18  | Network Speed Test         | Measures download/upload speeds
 19  | Power Supply Test          | Tests power delivery to GPU
 20  | System Summary             | Provides overall readiness assessment
================================================================================
"""

import sys
import subprocess
import importlib
import os
import platform
import json
import urllib.request
import time
import socket
import datetime
import re

# =============================================================================
# GLOBAL VARIABLES
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Detect OS at the very beginning - this guides all platform-specific steps
OS_TYPE = platform.system()
IS_WINDOWS = OS_TYPE == "Windows"
IS_LINUX = OS_TYPE == "Linux"
IS_MACOS = OS_TYPE == "Darwin"
IS_JETSON = IS_LINUX and os.path.exists('/etc/nv_tegra_release')  # Jetson Nano detection

# Scan timing variables - captured at script start
SCAN_START_TIME = datetime.datetime.now()
SCAN_START_TIMESTAMP = SCAN_START_TIME.isoformat()
SCAN_START_STR = SCAN_START_TIME.strftime('%Y-%m-%d %H:%M:%S')

# Global dictionary to store all report data
REPORT_DATA = {
    "scan_start_time": SCAN_START_TIMESTAMP,
    "scan_end_time": None,
    "scan_duration_seconds": None,
    "os_info": {
        "type": OS_TYPE,
        "is_windows": IS_WINDOWS,
        "is_linux": IS_LINUX,
        "is_macos": IS_MACOS,
        "is_jetson": IS_JETSON
    },
    "system": {},
    "cpu": {},
    "bios": {},
    "motherboard": {},
    "memory": {},
    "storage": {},
    "network": {},
    "pytorch": {},
    "gpu": {},
    "performance": {},
    "software": {},
    "stress_tests": {},
    "power_supply": {},
    "summary": {},
    "virtual_environment_setup": {
        "created": False,
        "tool_used": None,
        "env_name": None,
        "packages_installed": False
    },
    "recommendations": []
}

# =============================================================================
# LIBRARY CHECK AND INSTALLATION
# =============================================================================

REQUIRED_LIBRARIES = {
    'psutil': 'psutil',
    'wmi': 'wmi',  # Windows only
    'GPUtil': 'GPUtil',
    'cpuinfo': 'py-cpuinfo',
    'speedtest': 'speedtest-cli'
}

def check_and_install_libraries():
    """Check if required libraries are installed, prompt user to install if missing"""
    
    print("="*70)
    print("📦 LIBRARY DEPENDENCY CHECK")
    print("="*70)
    print("\nRequired libraries for this script:")
    print("-" * 50)
    
    # Determine which libraries are needed based on OS
    needed_libs = {}
    for lib, package in REQUIRED_LIBRARIES.items():
        if lib == 'wmi' and not IS_WINDOWS:
            continue  # Skip wmi on non-Windows
        needed_libs[lib] = package
    
    # Check each library
    missing_libs = []
    installed_libs = []
    
    for lib, package in needed_libs.items():
        try:
            importlib.import_module(lib)
            installed_libs.append((lib, package))
            print(f"  ✅ {lib} (package: {package}) - Installed")
        except ImportError:
            missing_libs.append((lib, package))
            print(f"  ❌ {lib} (package: {package}) - MISSING")
    
    # Check for optional PyTorch
    try:
        importlib.import_module('torch')
        print(f"  ✅ torch (package: torch) - Installed")
    except ImportError:
        print(f"  ⚠️  torch (package: torch) - NOT INSTALLED (optional for GPU tests)")
    
    print("\n" + "-" * 50)
    
    if missing_libs:
        print(f"\n⚠️  {len(missing_libs)} library(s) need to be installed:")
        for lib, package in missing_libs:
            print(f"    - {lib} (pip install {package})")
        
        print("\n" + "="*70)
        print("📥 INSTALLATION REQUIRED")
        print("="*70)
        print("\nDo you want to install the missing libraries?")
        print("  [1] Yes, install all missing libraries")
        print("  [2] Yes, but let me review each one")
        print("  [3] No, exit script")
        print("  [4] Install with specific Python version (e.g., python -m pip)")
        
        while True:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == '1':
                # Install all missing libraries
                print("\n📥 Installing missing libraries...")
                for lib, package in missing_libs:
                    print(f"  Installing {package}...")
                    try:
                        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                        print(f"  ✅ {package} installed successfully")
                    except subprocess.CalledProcessError:
                        print(f"  ❌ Failed to install {package}")
                        print(f"     Please install manually: pip install {package}")
                
                print("\n🔄 Libraries installed! Reloading modules...")
                for lib, _ in missing_libs:
                    try:
                        importlib.import_module(lib)
                    except ImportError:
                        pass
                break
                
            elif choice == '2':
                print("\n📥 Installing libraries one by one...")
                for lib, package in missing_libs:
                    response = input(f"\n  Install {package}? (y/n): ").strip().lower()
                    if response == 'y':
                        try:
                            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                            print(f"  ✅ {package} installed successfully")
                        except subprocess.CalledProcessError:
                            print(f"  ❌ Failed to install {package}")
                    else:
                        print(f"  ⏭️  Skipping {package}")
                break
                
            elif choice == '3':
                print("\n❌ Exiting script. Please install the required libraries and run again.")
                print("   To install all: pip install psutil wmi GPUtil py-cpuinfo speedtest-cli")
                sys.exit(0)
                
            elif choice == '4':
                pip_cmd = input("\n  Enter pip command (e.g., python -m pip or pip3): ").strip()
                if pip_cmd:
                    for lib, package in missing_libs:
                        print(f"  Installing {package} with {pip_cmd}...")
                        try:
                            subprocess.check_call([pip_cmd, 'install', package], shell=True)
                            print(f"  ✅ {package} installed successfully")
                        except subprocess.CalledProcessError:
                            print(f"  ❌ Failed to install {package}")
                break
            else:
                print("  Invalid choice. Please enter 1, 2, 3, or 4.")
        
        # Check if PyTorch should be installed
        try:
            importlib.import_module('torch')
        except ImportError:
            print("\n" + "="*70)
            print("📥 OPTIONAL: PYTORCH INSTALLATION")
            print("="*70)
            print("\nPyTorch is recommended for GPU testing.")
            print("\nDo you want to install PyTorch with CUDA support?")
            print("  [y] Yes, install PyTorch with CUDA")
            print("  [n] No, skip PyTorch installation")
            
            response = input("\nChoice (y/n): ").strip().lower()
            if response == 'y':
                print("\n📥 Installing PyTorch with CUDA support...")
                print("  This may take a few minutes...")
                try:
                    subprocess.check_call([
                        sys.executable, '-m', 'pip', 'install',
                        'torch', 'torchvision', 'torchaudio',
                        '--index-url', 'https://download.pytorch.org/whl/cu121'
                    ])
                    print("  ✅ PyTorch installed successfully")
                except subprocess.CalledProcessError:
                    print("  ❌ Failed to install PyTorch")
                    print("     Try manual installation:")
                    print("     pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
    
    else:
        print("\n✅ All required libraries are installed!")
        
        try:
            importlib.import_module('torch')
            print("  ✅ PyTorch is also installed")
        except ImportError:
            print("  ⚠️  PyTorch is not installed (optional for GPU tests)")
            response = input("\n  Install PyTorch with CUDA support? (y/n): ").strip().lower()
            if response == 'y':
                print("  Installing PyTorch...")
                try:
                    subprocess.check_call([
                        sys.executable, '-m', 'pip', 'install',
                        'torch', 'torchvision', 'torchaudio',
                        '--index-url', 'https://download.pytorch.org/whl/cu121'
                    ])
                    print("  ✅ PyTorch installed successfully")
                except subprocess.CalledProcessError:
                    print("  ❌ Failed to install PyTorch")
    
    print("\n" + "="*70)
    print("✅ Library check complete!")
    print("="*70)
    return True

# =============================================================================
# NVIDIA-SMI CHECK - FULL OUTPUT
# =============================================================================

def check_nvidia_smi():
    """Check if nvidia-smi is available and show FULL GPU status"""
    print("="*70)
    print("🔧 NVIDIA-SMI CHECK")
    print("="*70)
    
    try:
        # Check if nvidia-smi is available
        result = subprocess.run(['nvidia-smi', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ nvidia-smi is available\n")
            
            # Get FULL nvidia-smi output - NO TRUNCATION
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if result.returncode == 0:
                print("  FULL nvidia-smi output:")
                print("=" * 80)
                print(result.stdout)  # Full output - no truncation
                print("=" * 80)
                
                # Also show query for specific GPU details
                print("\n  Detailed GPU Query:")
                print("-" * 60)
                
                # Get GPU count
                result_count = subprocess.run(['nvidia-smi', '--query-gpu=count', '--format=csv,noheader'], 
                                              capture_output=True, text=True)
                if result_count.returncode == 0 and result_count.stdout.strip():
                    print(f"  GPU Count: {result_count.stdout.strip()}")
                
                # Get GPU details
                result_details = subprocess.run([
                    'nvidia-smi', 
                    '--query-gpu=index,name,driver_version,memory.total,temperature.gpu,power.limit,utilization.gpu,power.draw,pstate,clocks.sm,clocks.mem',
                    '--format=csv,noheader'
                ], capture_output=True, text=True)
                
                if result_details.returncode == 0 and result_details.stdout.strip():
                    print("\n  GPU Details:")
                    lines = result_details.stdout.strip().split('\n')
                    for line in lines:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 11:
                            print(f"    Index: {parts[0]}")
                            print(f"    Name: {parts[1]}")
                            print(f"    Driver Version: {parts[2]}")
                            print(f"    Memory Total: {parts[3]}")
                            print(f"    Temperature: {parts[4]}")
                            print(f"    Power Limit: {parts[5]}")
                            print(f"    GPU Utilization: {parts[6]}")
                            print(f"    Power Draw: {parts[7]}")
                            print(f"    Performance State: {parts[8]}")
                            print(f"    SM Clock: {parts[9]}")
                            print(f"    Memory Clock: {parts[10]}")
                            print("-" * 40)
                
                # Get GPU processes
                result_proc = subprocess.run(
                    ['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader'],
                    capture_output=True, text=True
                )
                if result_proc.returncode == 0 and result_proc.stdout.strip():
                    print("\n  GPU Processes:")
                    print("-" * 40)
                    for line in result_proc.stdout.strip().split('\n'):
                        if line.strip():
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) >= 3:
                                pid = parts[0]
                                proc_name = parts[1]
                                mem = parts[2]
                                if proc_name == '[Insufficient Permissions]':
                                    print(f"    PID: {pid}")
                                    print(f"    Process: ⚠️  Insufficient permissions to view process name")
                                    print(f"    Used Memory: {mem}")
                                    print("    💡 Run terminal as Administrator to see process names")
                                    if IS_WINDOWS:
                                        print("    💡 On Windows: Right-click terminal -> Run as administrator")
                                else:
                                    print(f"    PID: {pid}")
                                    print(f"    Process: {proc_name}")
                                    print(f"    Used Memory: {mem}")
                                print("-" * 30)
                else:
                    print("\n  No GPU processes running")
                
                return True
            else:
                print("  ⚠️  nvidia-smi returned an error")
                return False
        else:
            print("  ❌ nvidia-smi not found!")
            print("     NVIDIA drivers may not be installed or not in PATH")
            return False
    except FileNotFoundError:
        print("  ❌ nvidia-smi not found!")
        print("     NVIDIA drivers may not be installed or not in PATH")
        return False
    except Exception as e:
        print(f"  ⚠️  Error checking nvidia-smi: {e}")
        return False

# =============================================================================
# IMPORT LIBRARIES AFTER CHECK
# =============================================================================

# Run library check before importing anything else
if __name__ == "__main__":
    # Check and install libraries
    check_and_install_libraries()
    
    # Check nvidia-smi with FULL output
    check_nvidia_smi()
    
    # Now import all libraries
    import psutil
    import time
    import socket
    import datetime
    import re
    
    # Try importing optional libraries
    try:
        import GPUtil
        HAS_GPUTIL = True
    except ImportError:
        HAS_GPUTIL = False
    
    try:
        import cpuinfo
        HAS_CPUINFO = True
    except ImportError:
        HAS_CPUINFO = False
    
    try:
        import wmi
        HAS_WMI = True
    except ImportError:
        HAS_WMI = False
    
    try:
        import speedtest
        HAS_SPEEDTEST = True
    except ImportError:
        HAS_SPEEDTEST = False
    
    try:
        import torch
        HAS_TORCH = True
    except ImportError:
        HAS_TORCH = False

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def run_command(cmd):
    """Run a system command and return output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None

def run_command_no_shell(cmd):
    """Run a system command without shell and return output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None

def get_size(bytes, suffix="B"):
    """Convert bytes to human readable format"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f} {unit}{suffix}"
        bytes /= factor
    return f"{bytes:.2f} {suffix}"

def print_section(title):
    """Print a section header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)

def print_subsection(title):
    """Print a subsection header"""
    print(f"\n{title}")
    print("-" * 50)

def print_table_header():
    """Print the test plan table"""
    print("\n" + "="*70)
    print(" COMPREHENSIVE SYSTEM SCAN - TEST PLAN")
    print("="*70)
    print(" Step | What it Tests              | Why it Matters")
    print("------|----------------------------|-----------------------------------------------")
    print("  1   | System Overview            | Identifies OS, hostname, boot time")
    print("  2   | CPU Information            | Checks cores, frequency, cache, virtualization")
    print("  3   | BIOS/Firmware              | Verifies firmware version and compatibility")
    print("  4   | Memory (RAM)               | Checks capacity, speed, type, usage")
    print("  5   | Storage (SSD/NVMe)         | Checks drives, capacity, health, performance")
    print("  6   | Network                    | Verifies connectivity, IPs, speed, DNS")
    print("  7   | PyTorch installation       | Ensures the AI framework is installed")
    print("  8   | CUDA availability          | Confirms GPU drivers work with PyTorch")
    print("  9   | GPU detection              | Identifies your GPU and its specs")
    print(" 10   | Basic GPU computation      | Verifies the GPU can do math correctly")
    print(" 11   | GPU Performance            | Benchmarks your GPU's speed")
    print(" 12   | GPU Memory allocation      | Tests VRAM allocation and limits")
    print(" 13   | NVIDIA Driver info         | Shows NVIDIA driver details (nvidia-smi)")
    print(" 14   | AI/ML Software & Venv      | Checks installed frameworks and virtual environment")
    print(" 15   | CPU Stress Test            | Tests CPU performance under load")
    print(" 16   | GPU Stress Test            | Tests GPU performance under load")
    print(" 17   | Storage Speed Test         | Measures read/write speeds")
    print(" 18   | Network Speed Test         | Measures download/upload speeds")
    print(" 19   | Power Supply Test          | Tests power delivery to GPU")
    print(" 20   | System Summary             | Provides overall readiness assessment")
    print("="*70)

def print_notes(step_num, notes):
    """Print notes for a step"""
    print(f"\n  📝 NOTES:")
    print("  " + "-" * 60)
    for line in notes.split('\n'):
        print(f"    {line}")
    print("  " + "-" * 60)

def save_json_report():
    """Save the collected report data to a JSON file in the script directory"""
    try:
        # Update end time and duration
        end_time = datetime.datetime.now()
        REPORT_DATA["scan_end_time"] = end_time.isoformat()
        REPORT_DATA["scan_duration_seconds"] = (end_time - SCAN_START_TIME).total_seconds()
        
        # Save to file in the script directory
        filename = os.path.join(SCRIPT_DIR, "system_scan_report.json")
        with open(filename, 'w') as f:
            json.dump(REPORT_DATA, f, indent=2, default=str)
        
        # Print timing summary
        print(f"\n⏱️  Scan Timing:")
        print(f"   Started: {SCAN_START_STR}")
        print(f"   Ended:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Duration: {REPORT_DATA['scan_duration_seconds']:.2f} seconds")
        
        print(f"\n📄 JSON report saved to: {filename}")
        print(f"   File size: {get_size(os.path.getsize(filename))}")
        return filename
    except Exception as e:
        print(f"\n⚠️  Failed to save JSON report: {e}")
        return None

def detect_jetson():
    """Detect if running on NVIDIA Jetson Nano"""
    return IS_LINUX and os.path.exists('/etc/nv_tegra_release')

def is_rpi():
    """Detect if running on Raspberry Pi"""
    if IS_LINUX:
        try:
            with open('/proc/cpuinfo', 'r') as f:
                return 'Raspberry Pi' in f.read()
        except:
            pass
    return False

# =============================================================================
# PLATFORM-SPECIFIC HARDWARE DETECTION
# =============================================================================

def get_platform_specific_info():
    """Get platform-specific hardware information (BIOS, motherboard, network)"""
    
    if IS_WINDOWS:
        return get_windows_hardware_info()
    elif IS_LINUX:
        return get_linux_hardware_info()
    elif IS_MACOS:
        return get_macos_hardware_info()
    else:
        return {"error": f"Unsupported OS: {OS_TYPE}"}

def filter_sensitive_data(data, sensitive_keys):
    """Filter sensitive data from dictionaries"""
    if isinstance(data, dict):
        filtered = {}
        for key, value in data.items():
            if key in sensitive_keys:
                filtered[key] = "[FILTERED]"
            else:
                filtered[key] = filter_sensitive_data(value, sensitive_keys)
        return filtered
    elif isinstance(data, list):
        return [filter_sensitive_data(item, sensitive_keys) for item in data]
    else:
        return data

def get_windows_hardware_info():
    """Get Windows-specific hardware information"""
    info = {
        "bios": {},
        "motherboard": {},
        "network_adapters": [],
        "wifi_interfaces": []
    }
    
    try:
        import wmi
        c = wmi.WMI()
        
        # BIOS Information
        for bios in c.Win32_BIOS():
            info["bios"] = {
                "name": bios.Name if hasattr(bios, 'Name') else None,
                "version": bios.SMBIOSBIOSVersion if hasattr(bios, 'SMBIOSBIOSVersion') else None,
                "manufacturer": bios.Manufacturer if hasattr(bios, 'Manufacturer') else None,
                "release_date": str(bios.ReleaseDate) if hasattr(bios, 'ReleaseDate') else None,
                "smbios_version": f"{bios.SMBIOSMajorVersion}.{bios.SMBIOSMinorVersion}" if hasattr(bios, 'SMBIOSMajorVersion') else None,
                "serial_number": "[FILTERED]" if hasattr(bios, 'SerialNumber') else None
            }
            break
        
        # Motherboard Information
        for board in c.Win32_BaseBoard():
            info["motherboard"] = {
                "manufacturer": board.Manufacturer if hasattr(board, 'Manufacturer') else None,
                "product": board.Product if hasattr(board, 'Product') else None,
                "version": board.Version if hasattr(board, 'Version') else None,
                "serial_number": "[FILTERED]" if hasattr(board, 'SerialNumber') else None,
                "tag": board.Tag if hasattr(board, 'Tag') else None
            }
            break
        
        # Network Adapters
        for adapter in c.Win32_NetworkAdapter():
            if adapter.Name and adapter.InterfaceDescription:
                info["network_adapters"].append({
                    "name": adapter.Name if hasattr(adapter, 'Name') else None,
                    "description": adapter.InterfaceDescription if hasattr(adapter, 'InterfaceDescription') else None,
                    "status": adapter.Status if hasattr(adapter, 'Status') else None,
                    "mac_address": adapter.MACAddress if hasattr(adapter, 'MACAddress') else None,
                    "speed": adapter.Speed if hasattr(adapter, 'Speed') else None
                })
        
    except Exception as e:
        info["error"] = f"Failed to get Windows hardware info: {e}"
    
    # Get Wi-Fi info using netsh
    try:
        wifi_output = run_command("netsh wlan show interfaces")
        if wifi_output:
            wifi_info = {}
            for line in wifi_output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    wifi_info[key.strip()] = value.strip()
            if wifi_info:
                info["wifi_interfaces"].append(wifi_info)
    except:
        pass
    
    # Get Wi-Fi adapters using Get-NetAdapter
    try:
        netadapter_output = run_command("powershell -Command \"Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, NetworkInterfaceType\"")
        if netadapter_output:
            for line in netadapter_output.split('\n'):
                if line.strip() and not line.startswith('Name'):
                    parts = line.split()
                    if parts:
                        info["network_adapters"].append({
                            "name": parts[0] if parts else None,
                            "status": "Up" if "Up" in line else "Down"
                        })
    except:
        pass
    
    return info

def get_linux_hardware_info():
    """Get Linux-specific hardware information"""
    info = {
        "bios": {},
        "motherboard": {},
        "network_adapters": [],
        "wifi_interfaces": []
    }
    
    try:
        # BIOS Information
        bios_output = run_command("sudo dmidecode -t bios 2>/dev/null")
        if bios_output:
            bios_data = {}
            for line in bios_output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    bios_data[key.strip()] = value.strip()
            info["bios"] = {
                "vendor": bios_data.get('Vendor'),
                "version": bios_data.get('Version'),
                "release_date": bios_data.get('Release Date'),
                "serial_number": "[FILTERED]"
            }
    except:
        pass
    
    try:
        # Motherboard Information
        board_output = run_command("sudo dmidecode -t baseboard 2>/dev/null")
        if board_output:
            board_data = {}
            for line in board_output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    board_data[key.strip()] = value.strip()
            info["motherboard"] = {
                "manufacturer": board_data.get('Manufacturer'),
                "product": board_data.get('Product Name'),
                "version": board_data.get('Version'),
                "serial_number": "[FILTERED]"
            }
    except:
        pass
    
    try:
        # Network interfaces
        net_output = run_command("ip link show")
        if net_output:
            for line in net_output.split('\n'):
                if ':' in line and not '@' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        info["network_adapters"].append({
                            "name": parts[1].strip(),
                            "status": "Up" if "UP" in line else "Down"
                        })
    except:
        pass
    
    try:
        # Wi-Fi info
        wifi_output = run_command("iwconfig 2>/dev/null")
        if wifi_output:
            wifi_info = {}
            for line in wifi_output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    wifi_info[key.strip()] = value.strip()
            if wifi_info:
                info["wifi_interfaces"].append(wifi_info)
    except:
        pass
    
    return info

def get_macos_hardware_info():
    """Get macOS-specific hardware information"""
    info = {
        "bios": {},
        "motherboard": {},
        "network_adapters": [],
        "wifi_interfaces": []
    }
    
    try:
        # System Information
        sysinfo = run_command("system_profiler SPHardwareDataType")
        if sysinfo:
            hardware_data = {}
            for line in sysinfo.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    hardware_data[key.strip()] = value.strip()
            info["bios"] = {
                "version": hardware_data.get('Boot ROM Version'),
                "serial_number": "[FILTERED]"
            }
    except:
        pass
    
    try:
        # Network interfaces
        net_output = run_command("ifconfig")
        if net_output:
            interface_names = []
            for line in net_output.split('\n'):
                if line and not line.startswith(' '):
                    interface_names.append(line.split(':')[0])
            for name in interface_names:
                info["network_adapters"].append({
                    "name": name,
                    "status": "Available"
                })
    except:
        pass
    
    try:
        # Wi-Fi info
        wifi_output = run_command("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I 2>/dev/null")
        if wifi_output:
            wifi_info = {}
            for line in wifi_output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    wifi_info[key.strip()] = value.strip()
            if wifi_info:
                info["wifi_interfaces"].append(wifi_info)
    except:
        pass
    
    return info

# =============================================================================
# STEP 1: SYSTEM OVERVIEW
# =============================================================================

def get_system_info():
    """Step 1: Get basic system information"""
    print_section("STEP 1: SYSTEM OVERVIEW")
    print("-" * 50)
    
    notes = f"""
    This shows your system basics: OS, machine type, hostname, boot time, and Python version.
    
    OS Detected: {OS_TYPE}
    Windows: {IS_WINDOWS}
    Linux: {IS_LINUX}
    macOS: {IS_MACOS}
    Jetson: {IS_JETSON}
    
    This helps identify your environment and ensure compatibility with AI tools.
    """
    print_notes(1, notes)
    
    system_info = {
        "os": OS_TYPE,
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": socket.gethostname(),
        "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S'),
        "python_version": sys.version,
        "script_run": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "is_windows": IS_WINDOWS,
        "is_linux": IS_LINUX,
        "is_macos": IS_MACOS,
        "is_jetson": IS_JETSON
    }
    REPORT_DATA["system"] = system_info
    
    print(f"  System: {OS_TYPE} {platform.release()} ({platform.version})")
    print(f"  Machine: {platform.machine()}")
    print(f"  Processor: {platform.processor()}")
    print(f"  Hostname: {socket.gethostname()}")
    print(f"  Boot Time: {datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python Version: {sys.version}")
    print(f"  Script Run: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Jetson Detected: {IS_JETSON}")

# =============================================================================
# STEP 2: CPU INFORMATION
# =============================================================================

def get_cpu_info():
    """Step 2: Get detailed CPU information"""
    print_section("STEP 2: CPU INFORMATION")
    print("-" * 50)
    
    notes = """
    CPU checks: physical cores, logical cores, frequency, usage, virtualization.
    For AI workloads: 8+ physical cores and 3.5+ GHz frequency is ideal for data preprocessing.
    """
    print_notes(2, notes)
    
    physical_cores = psutil.cpu_count(logical=False)
    logical_cores = psutil.cpu_count(logical=True)
    
    cpu_data = {
        "physical_cores": physical_cores,
        "logical_cores": logical_cores,
        "max_frequency": None,
        "current_frequency": None,
        "min_frequency": None,
        "cpu_usage": psutil.cpu_percent(interval=1),
        "model": "Unknown",
        "architecture": "Unknown",
        "virtualization": "Unknown",
        "running_in_vm": False,
        "load_average": None
    }
    
    freq = psutil.cpu_freq()
    if freq:
        cpu_data["max_frequency"] = freq.max
        cpu_data["current_frequency"] = freq.current
        cpu_data["min_frequency"] = freq.min
        print(f"  Max Frequency: {freq.max:.2f} MHz")
        print(f"  Current Frequency: {freq.current:.2f} MHz")
        print(f"  Min Frequency: {freq.min:.2f} MHz")
    
    print(f"  Physical Cores: {physical_cores}")
    print(f"  Logical Cores: {logical_cores}")
    print(f"  CPU Usage: {psutil.cpu_percent(interval=1)}%")
    
    if hasattr(psutil, 'getloadavg'):
        load = psutil.getloadavg()
        cpu_data["load_average"] = {"1min": load[0], "5min": load[1], "15min": load[2]}
        print(f"  Load Average (1, 5, 15 min): {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}")
    
    if HAS_CPUINFO:
        try:
            info = cpuinfo.get_cpu_info()
            cpu_data["model"] = info.get('brand_raw', 'Unknown')
            cpu_data["architecture"] = info.get('arch', 'Unknown')
            cpu_data["bits"] = info.get('bits', 'Unknown')
            cpu_data["cache_size"] = info.get('l2_cache_size', 'Unknown')
            cpu_data["flags"] = len(info.get('flags', []))
            print(f"  CPU Model: {info.get('brand_raw', 'Unknown')}")
            print(f"  Architecture: {info.get('arch', 'Unknown')}")
            print(f"  Bits: {info.get('bits', 'Unknown')}")
            print(f"  Cache Size: {info.get('l2_cache_size', 'Unknown')}")
            print(f"  CPU Flags: {len(info.get('flags', []))} features enabled")
        except:
            pass
    
    if IS_WINDOWS and HAS_WMI:
        try:
            c = wmi.WMI()
            for cpu in c.Win32_Processor():
                cpu_data["processor_id"] = cpu.ProcessorId
                cpu_data["max_clock_speed"] = cpu.MaxClockSpeed
                cpu_data["current_clock_speed"] = cpu.CurrentClockSpeed
                cpu_data["socket"] = cpu.SocketDesignation
                cpu_data["virtualization"] = cpu.VirtualizationFirmwareEnabled
                print(f"  Processor ID: {cpu.ProcessorId}")
                print(f"  Max Clock Speed: {cpu.MaxClockSpeed} MHz")
                print(f"  Current Clock Speed: {cpu.CurrentClockSpeed} MHz")
                print(f"  Socket Designation: {cpu.SocketDesignation}")
                print(f"  Virtualization: {cpu.VirtualizationFirmwareEnabled}")
                break
        except:
            pass
    
    if IS_WINDOWS:
        virt = run_command("systeminfo | findstr /I 'virtualization'")
        if virt:
            cpu_data["virtualization_cmd"] = virt
            print(f"  Virtualization: {virt}")
    
    is_vm = False
    try:
        if IS_WINDOWS:
            is_vm = "Virtual" in run_command("wmic computersystem get model") or "VMware" in run_command("wmic computersystem get model")
        elif IS_LINUX:
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    if 'hypervisor' in f.read():
                        is_vm = True
    except:
        pass
    cpu_data["running_in_vm"] = is_vm
    print(f"  Running in VM: {is_vm}")
    
    REPORT_DATA["cpu"] = cpu_data

# =============================================================================
# STEP 3: BIOS / FIRMWARE INFORMATION
# =============================================================================

def get_bios_info():
    """Step 3: Get BIOS/Firmware information"""
    print_section("STEP 3: BIOS / FIRMWARE INFORMATION")
    print("-" * 50)
    
    notes = """
    BIOS checks: manufacturer, version, date, SMBIOS version.
    Newer BIOS versions can improve PCIe performance (GPU communication) and power management.
    """
    print_notes(3, notes)
    
    bios_data = {}
    
    if IS_WINDOWS and HAS_WMI:
        try:
            c = wmi.WMI()
            for bios in c.Win32_BIOS():
                bios_data["manufacturer"] = bios.Manufacturer
                bios_data["name"] = bios.Name
                bios_data["version"] = bios.SMBIOSBIOSVersion
                bios_data["date"] = str(bios.ReleaseDate) if bios.ReleaseDate else None
                bios_data["smbios_major"] = bios.SMBIOSMajorVersion
                bios_data["smbios_minor"] = bios.SMBIOSMinorVersion
                print(f"  Manufacturer: {bios.Manufacturer}")
                print(f"  Name: {bios.Name}")
                print(f"  Version: {bios.SMBIOSBIOSVersion}")
                if bios.ReleaseDate:
                    print(f"  Date: {bios.ReleaseDate}")
                print(f"  SMBIOS Version: {bios.SMBIOSMajorVersion}.{bios.SMBIOSMinorVersion}")
                break
        except:
            pass
    
    if IS_WINDOWS:
        bios_info = run_command("systeminfo | findstr /I 'BIOS'")
        if bios_info:
            bios_data["systeminfo"] = bios_info
            for line in bios_info.split('\n'):
                print(f"  {line.strip()}")
    
    elif IS_LINUX:
        bios_info = run_command("sudo dmidecode -t bios 2>/dev/null | grep -E 'Vendor|Version|Release Date'")
        if bios_info:
            bios_data["dmidecode"] = bios_info
            for line in bios_info.split('\n'):
                print(f"  {line.strip()}")
    
    elif IS_MACOS:
        bios_info = run_command("system_profiler SPHardwareDataType | grep -E 'Boot ROM Version|SMC Version'")
        if bios_info:
            bios_data["system_profiler"] = bios_info
            for line in bios_info.split('\n'):
                print(f"  {line.strip()}")
    
    REPORT_DATA["bios"] = bios_data

# =============================================================================
# STEP 4: MEMORY (RAM) INFORMATION
# =============================================================================

def get_memory_info():
    """Step 4: Get detailed memory information"""
    print_section("STEP 4: MEMORY (RAM) INFORMATION")
    print("-" * 50)
    
    notes = """
    RAM checks: total capacity, available, speed, usage.
    For AI workloads: 16GB+ for hobbyist, 32GB+ for professional, 64GB+ for large language models.
    """
    print_notes(4, notes)
    
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    memory_data = {
        "total_ram": mem.total,
        "available_ram": mem.available,
        "used_ram": mem.used,
        "ram_usage_percent": mem.percent,
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_free": swap.free,
        "swap_usage_percent": swap.percent,
        "modules": []
    }
    
    print(f"  Total RAM: {get_size(mem.total)}")
    print(f"  Available RAM: {get_size(mem.available)}")
    print(f"  Used RAM: {get_size(mem.used)}")
    print(f"  RAM Usage: {mem.percent}%")
    
    if IS_WINDOWS and HAS_WMI:
        try:
            c = wmi.WMI()
            total_speed = 0
            count = 0
            for mem_device in c.Win32_PhysicalMemory():
                module = {
                    "capacity": mem_device.Capacity,
                    "speed": mem_device.Speed,
                    "manufacturer": mem_device.Manufacturer,
                    "part_number": mem_device.PartNumber,
                    "form_factor": mem_device.FormFactor,
                    "device_locator": mem_device.DeviceLocator
                }
                memory_data["modules"].append(module)
                print(f"\n  Memory Module:")
                print(f"    Capacity: {get_size(mem_device.Capacity)}")
                print(f"    Speed: {mem_device.Speed} MHz")
                print(f"    Manufacturer: {mem_device.Manufacturer}")
                print(f"    Part Number: {mem_device.PartNumber}")
                print(f"    Form Factor: {mem_device.FormFactor}")
                print(f"    Device Locator: {mem_device.DeviceLocator}")
                total_speed += int(mem_device.Speed) if mem_device.Speed else 0
                count += 1
            if count > 0:
                memory_data["avg_speed"] = total_speed/count
                print(f"\n  Average Speed: {total_speed/count:.0f} MHz")
        except:
            pass
    
    print(f"\n  Swap Total: {get_size(swap.total)}")
    print(f"  Swap Used: {get_size(swap.used)}")
    print(f"  Swap Free: {get_size(swap.free)}")
    print(f"  Swap Usage: {swap.percent}%")
    
    REPORT_DATA["memory"] = memory_data

# =============================================================================
# STEP 5: STORAGE INFORMATION
# =============================================================================

def get_storage_info():
    """Step 5: Get detailed storage information"""
    print_section("STEP 5: STORAGE INFORMATION")
    print("-" * 50)
    
    notes = """
    Storage checks: partitions, file systems, capacity, usage, I/O statistics.
    For AI workloads: NVMe SSD (2000+ MB/s) is ideal. SATA SSD is acceptable. HDD is NOT recommended.
    """
    print_notes(5, notes)
    
    storage_data = {
        "partitions": [],
        "io_stats": {},
        "physical_disks": []
    }
    
    print_subsection("Disk Partitions")
    partitions = psutil.disk_partitions()
    for partition in partitions:
        partition_info = {
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "fstype": partition.fstype,
            "opts": partition.opts
        }
        
        device_display = partition.device.replace('\\', '\\\\')
        print(f"  Device: {device_display}")
        print(f"    Mount: {partition.mountpoint}")
        print(f"    File System: {partition.fstype}")
        print(f"    Options: {partition.opts}")
        
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            partition_info["total_size"] = usage.total
            partition_info["used"] = usage.used
            partition_info["free"] = usage.free
            partition_info["usage_percent"] = usage.percent
            print(f"    Total Size: {get_size(usage.total)}")
            print(f"    Used: {get_size(usage.used)}")
            print(f"    Free: {get_size(usage.free)}")
            print(f"    Usage: {usage.percent}%")
        except PermissionError:
            print("    (Permission denied)")
        storage_data["partitions"].append(partition_info)
        print()
    
    print_subsection("Disk I/O Statistics")
    io_counters = psutil.disk_io_counters()
    if io_counters:
        storage_data["io_stats"] = {
            "read_count": io_counters.read_count,
            "write_count": io_counters.write_count,
            "read_bytes": io_counters.read_bytes,
            "write_bytes": io_counters.write_bytes,
            "read_time_ms": io_counters.read_time,
            "write_time_ms": io_counters.write_time
        }
        print(f"  Read Count: {io_counters.read_count}")
        print(f"  Write Count: {io_counters.write_count}")
        print(f"  Read Bytes: {get_size(io_counters.read_bytes)}")
        print(f"  Write Bytes: {get_size(io_counters.write_bytes)}")
        print(f"  Read Time: {io_counters.read_time} ms")
        print(f"  Write Time: {io_counters.write_time} ms")
    
    if IS_WINDOWS and HAS_WMI:
        print_subsection("Physical Disk Details")
        try:
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                disk_info = {
                    "model": disk.Model,
                    "interface": disk.InterfaceType,
                    "media_type": disk.MediaType,
                    "size": disk.Size,
                    "partitions": disk.Partitions
                }
                storage_data["physical_disks"].append(disk_info)
                print(f"  Model: {disk.Model}")
                print(f"    Interface: {disk.InterfaceType}")
                print(f"    Media Type: {disk.MediaType}")
                print(f"    Size: {get_size(int(disk.Size)) if disk.Size else 'Unknown'}")
                print(f"    Partitions: {disk.Partitions}")
                print()
        except:
            pass
    
    if IS_LINUX:
        print_subsection("Disk Information")
        disk_info = run_command("lsblk -o NAME,SIZE,MODEL,TYPE 2>/dev/null")
        if disk_info:
            print("  lsblk output:")
            for line in disk_info.split('\n'):
                if line.strip():
                    print(f"    {line}")
    
    REPORT_DATA["storage"] = storage_data

# =============================================================================
# STEP 6: NETWORK INFORMATION
# =============================================================================

def get_network_info():
    """Step 6: Get detailed network information with Wi-Fi details"""
    print_section("STEP 6: NETWORK INFORMATION")
    print("-" * 50)
    
    notes = """
    Network checks: interfaces, IPs, MAC addresses, I/O statistics, connectivity.
    For AI workloads: 50+ Mbps download for models, 10+ Mbps upload for cloud training, low ping (<50ms).
    """
    print_notes(6, notes)
    
    network_data = {
        "interfaces": [],
        "io_stats": {},
        "connectivity": {
            "internet": False,
            "dns_resolution": False,
            "ping_success": False
        },
        "wifi": []
    }
    
    print_subsection("Network Interfaces")
    interfaces = psutil.net_if_addrs()
    for interface_name, interface_addresses in interfaces.items():
        if interface_name.startswith(('lo', 'Loopback')):
            continue
        interface_info = {"name": interface_name, "addresses": []}
        print(f"  {interface_name}:")
        for address in interface_addresses:
            addr_info = {"family": str(address.family), "address": address.address}
            if address.netmask:
                addr_info["netmask"] = address.netmask
            interface_info["addresses"].append(addr_info)
            
            if address.family == socket.AF_INET:
                print(f"    IPv4: {address.address}")
                if address.netmask:
                    print(f"    Netmask: {address.netmask}")
            elif address.family == socket.AF_INET6:
                print(f"    IPv6: {address.address}")
            else:
                print(f"    MAC: {address.address}")
        network_data["interfaces"].append(interface_info)
    
    # Get Wi-Fi information based on OS
    print_subsection("Wi-Fi Information")
    
    if IS_WINDOWS:
        # Get Wi-Fi details using netsh
        try:
            wifi_output = run_command("netsh wlan show interfaces")
            if wifi_output:
                wifi_info = {}
                for line in wifi_output.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        wifi_info[key.strip()] = value.strip()
                if wifi_info:
                    network_data["wifi"].append(wifi_info)
                    print(f"  Wi-Fi Adapter: {wifi_info.get('Name', 'Unknown')}")
                    print(f"  SSID: {wifi_info.get('SSID', 'Not connected')}")
                    print(f"  Band: {wifi_info.get('Band', 'Unknown')}")
                    print(f"  Channel: {wifi_info.get('Channel', 'Unknown')}")
                    print(f"  Signal: {wifi_info.get('Signal', 'Unknown')}")
                    print(f"  Receive Rate: {wifi_info.get('Receive rate (Mbps)', 'Unknown')}")
                    print(f"  Transmit Rate: {wifi_info.get('Transmit rate (Mbps)', 'Unknown')}")
        except:
            pass
        
        # Get network adapters
        try:
            adapter_output = run_command("powershell -Command \"Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, NetworkInterfaceType\"")
            if adapter_output:
                print("\n  Network Adapters:")
                for line in adapter_output.split('\n'):
                    if line.strip() and not line.startswith('Name'):
                        parts = line.split()
                        if len(parts) >= 2:
                            status = "Up" if "Up" in line else "Disconnected"
                            print(f"    {parts[0]} - {status}")
        except:
            pass
    
    elif IS_LINUX:
        # Get Wi-Fi info using iwconfig
        try:
            wifi_output = run_command("iwconfig 2>/dev/null | grep -E 'ESSID|Frequency|Bit Rate|Signal level'")
            if wifi_output:
                wifi_info = {}
                for line in wifi_output.split('\n'):
                    if 'ESSID' in line:
                        wifi_info['SSID'] = line.split('"')[1] if '"' in line else line.split(':')[1].strip()
                    elif 'Frequency' in line:
                        wifi_info['Frequency'] = line.split(':')[1].strip() if ':' in line else None
                    elif 'Bit Rate' in line:
                        wifi_info['Bit Rate'] = line.split(':')[1].strip() if ':' in line else None
                    elif 'Signal level' in line:
                        wifi_info['Signal'] = line.split('=')[1].strip() if '=' in line else None
                if wifi_info:
                    network_data["wifi"].append(wifi_info)
                    print(f"  SSID: {wifi_info.get('SSID', 'Not connected')}")
                    print(f"  Frequency: {wifi_info.get('Frequency', 'Unknown')}")
                    print(f"  Bit Rate: {wifi_info.get('Bit Rate', 'Unknown')}")
                    print(f"  Signal: {wifi_info.get('Signal', 'Unknown')}")
        except:
            pass
    
    elif IS_MACOS:
        # Get Wi-Fi info using airport
        try:
            wifi_output = run_command("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I 2>/dev/null")
            if wifi_output:
                wifi_info = {}
                for line in wifi_output.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        wifi_info[key.strip()] = value.strip()
                if wifi_info:
                    network_data["wifi"].append(wifi_info)
                    print(f"  SSID: {wifi_info.get('SSID', 'Not connected')}")
                    print(f"  Band: {wifi_info.get('op mode', 'Unknown')}")
                    print(f"  Channel: {wifi_info.get('channel', 'Unknown')}")
                    print(f"  Signal: {wifi_info.get('agrCtlRSSI', 'Unknown')}")
        except:
            pass
    
    print_subsection("Network I/O Statistics")
    io_counters = psutil.net_io_counters()
    if io_counters:
        network_data["io_stats"] = {
            "bytes_sent": io_counters.bytes_sent,
            "bytes_recv": io_counters.bytes_recv,
            "packets_sent": io_counters.packets_sent,
            "packets_recv": io_counters.packets_recv,
            "errin": io_counters.errin,
            "errout": io_counters.errout,
            "dropin": io_counters.dropin,
            "dropout": io_counters.dropout
        }
        print(f"  Bytes Sent: {get_size(io_counters.bytes_sent)}")
        print(f"  Bytes Received: {get_size(io_counters.bytes_recv)}")
        print(f"  Packets Sent: {io_counters.packets_sent}")
        print(f"  Packets Received: {io_counters.packets_recv}")
        print(f"  Errors In: {io_counters.errin}")
        print(f"  Errors Out: {io_counters.errout}")
        print(f"  Drops In: {io_counters.dropin}")
        print(f"  Drops Out: {io_counters.dropout}")
    
    print_subsection("Connectivity Test")
    try:
        socket.gethostbyname('8.8.8.8')
        network_data["connectivity"]["internet"] = True
        print("  ✅ Internet connectivity: Available")
        
        dns_test = socket.gethostbyname('google.com')
        network_data["connectivity"]["dns_resolution"] = True
        print(f"  ✅ DNS Resolution: google.com -> {dns_test}")
        
        if IS_WINDOWS:
            ping = run_command("ping -n 1 8.8.8.8")
            if ping:
                network_data["connectivity"]["ping_success"] = True
                print("  ✅ Ping test: Successful")
        else:
            ping = run_command("ping -c 1 8.8.8.8")
            if ping:
                network_data["connectivity"]["ping_success"] = True
                print("  ✅ Ping test: Successful")
    except:
        print("  ❌ Internet connectivity: Not available or DNS issue")
    
    REPORT_DATA["network"] = network_data

# =============================================================================
# STEP 7: PYTORCH INSTALLATION WITH VERSION CHECK
# =============================================================================

def check_pytorch():
    """Step 7: Check if PyTorch is installed and compare with latest version"""
    print_section("STEP 7: PYTORCH INSTALLATION")
    print("-" * 50)
    
    notes = """
    PyTorch checks: installation status, version, latest version from PyPI, CUDA compatibility.
    PyTorch is the main deep learning framework. Newer versions have performance improvements.
    """
    print_notes(7, notes)
    
    pytorch_data = {
        "installed": HAS_TORCH,
        "version": None,
        "latest_version": None,
        "cuda_version": None,
        "cudnn_version": None,
        "cuda_available": False,
        "is_latest": False
    }
    
    if HAS_TORCH:
        installed_version = torch.__version__
        pytorch_data["version"] = installed_version
        print(f"  ✅ PyTorch installed: {installed_version}")
        
        # Check latest version from PyPI
        print("\n  🔍 Checking latest version from PyPI...")
        try:
            url = "https://pypi.org/pypi/torch/json"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_version = data['info']['version']
                pytorch_data["latest_version"] = latest_version
                
                print(f"  Latest PyTorch version: {latest_version}")
                
                if installed_version == latest_version:
                    pytorch_data["is_latest"] = True
                    print("  ✅ You have the latest version!")
                else:
                    print(f"  ⚠️  You are using version {installed_version} (latest is {latest_version})")
                    print("  💡 To update: pip install --upgrade torch")
                    
        except Exception as e:
            print(f"  ⚠️  Could not check latest version: {e}")
            print("  💡 Check manually at: https://pypi.org/project/torch/")
        
        # Check CUDA compatibility
        if torch.cuda.is_available():
            cuda_version = torch.version.cuda
            cudnn_version = torch.backends.cudnn.version()
            pytorch_data["cuda_available"] = True
            pytorch_data["cuda_version"] = cuda_version
            pytorch_data["cudnn_version"] = cudnn_version
            print(f"\n  ✅ CUDA version: {cuda_version}")
            print(f"  ✅ cuDNN version: {cudnn_version}")
            print("  ✅ PyTorch is CUDA-enabled - GPU acceleration available!")
        else:
            print("  ⚠️  PyTorch is installed but CUDA is not available")
            print("  💡 Install CUDA version: pip install torch --index-url https://download.pytorch.org/whl/cu121")
        
        REPORT_DATA["pytorch"] = pytorch_data
        return True
    else:
        print("  ❌ PyTorch NOT installed")
        print("   Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        REPORT_DATA["pytorch"] = pytorch_data
        return False

# =============================================================================
# STEPS 8-10: GPU INFORMATION (Comprehensive)
# =============================================================================

def get_gpu_info():
    """Steps 8-10: Comprehensive GPU information"""
    
    # Step 8: Check CUDA availability
    print_section("STEP 8: CUDA AVAILABILITY")
    print("-" * 50)
    
    notes = """
    CUDA checks: CUDA availability, CUDA version, cuDNN version.
    CUDA enables GPU acceleration for AI (100x faster than CPU). Without CUDA, PyTorch runs on CPU only.
    """
    print_notes(8, notes)
    
    gpu_data = {
        "cuda_available": False,
        "cuda_version": None,
        "cudnn_version": None,
        "gpu_count": 0,
        "gpu_details": [],
        "computation_success": False
    }
    
    if not HAS_TORCH:
        print("  ⚠️  PyTorch not installed - skipping CUDA check")
        REPORT_DATA["gpu"] = gpu_data
        return
    
    print(f"  CUDA Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        gpu_data["cuda_available"] = True
        gpu_data["cuda_version"] = torch.version.cuda
        gpu_data["cudnn_version"] = torch.backends.cudnn.version()
        print(f"  CUDA Version: {torch.version.cuda}")
        print(f"  cuDNN Version: {torch.backends.cudnn.version()}")
        print("  ✅ GPU acceleration is enabled!")
    else:
        print("  ❌ CUDA is NOT available!")
        print("   Possible issues:")
        print("   - NVIDIA drivers not installed")
        print("   - PyTorch version without CUDA support")
        REPORT_DATA["gpu"] = gpu_data
        return
    
    # Step 9: GPU Detection
    print_section("STEP 9: GPU DETECTION")
    print("-" * 50)
    
    notes = """
    GPU detection: GPU name, compute capability, VRAM, CUDA cores, max threads.
    Your GPU's capabilities determine what AI models you can run.
    """
    print_notes(9, notes)
    
    gpu_count = torch.cuda.device_count()
    gpu_data["gpu_count"] = gpu_count
    print(f"  GPU Count: {gpu_count}")
    
    if gpu_count > 0:
        for i in range(gpu_count):
            gpu_detail = {
                "index": i,
                "name": torch.cuda.get_device_name(i)
            }
            props = torch.cuda.get_device_properties(i)
            gpu_detail["compute_capability"] = f"{props.major}.{props.minor}"
            gpu_detail["total_vram"] = props.total_memory / 1e9
            gpu_detail["multi_processors"] = props.multi_processor_count
            gpu_detail["cuda_cores"] = props.multi_processor_count * 128
            gpu_detail["max_threads_per_block"] = props.max_threads_per_block
            gpu_detail["max_threads_per_multi_processor"] = props.max_threads_per_multi_processor
            gpu_detail["shared_memory_per_block"] = props.shared_memory_per_block / 1024
            gpu_detail["total_shared_memory_per_multiprocessor"] = props.shared_memory_per_multiprocessor / 1024
            
            gpu_data["gpu_details"].append(gpu_detail)
            
            print(f"\n  GPU {i}:")
            print(f"    Name: {torch.cuda.get_device_name(i)}")
            print(f"    Compute Capability: {props.major}.{props.minor}")
            print(f"    Total VRAM: {props.total_memory / 1e9:.2f} GB")
            print(f"    Multi-processors: {props.multi_processor_count}")
            print(f"    CUDA Cores: {props.multi_processor_count * 128} (approx)")
            print(f"    Max Threads per Block: {props.max_threads_per_block}")
            print(f"    Max Threads per Multi-processor: {props.max_threads_per_multi_processor}")
            print(f"    Shared Memory per Block: {props.shared_memory_per_block / 1024:.0f} KB")
            print(f"    Total Shared Memory per Multi-processor: {props.shared_memory_per_multiprocessor / 1024:.0f} KB")
    
    # Step 10: Basic GPU Computation Test
    print_section("STEP 10: BASIC GPU COMPUTATION")
    print("-" * 50)
    
    notes = """
    Basic GPU computation test: matrix multiplication (1000x1000) on GPU.
    This verifies GPU memory allocation and basic computation works correctly.
    """
    print_notes(10, notes)
    
    try:
        print("  Creating tensors on GPU...")
        a = torch.randn(1000, 1000).cuda()
        b = torch.randn(1000, 1000).cuda()
        
        print("  Performing matrix multiplication...")
        c = torch.matmul(a, b)
        
        gpu_data["computation_success"] = True
        print("  ✅ Computation successful!")
        print(f"    Result shape: {c.shape}")
        print(f"    Result device: {c.device}")
        print(f"    Memory allocated: {torch.cuda.memory_allocated() / 1e6:.2f} MB")
        print(f"    Memory reserved: {torch.cuda.memory_reserved() / 1e6:.2f} MB")
    except Exception as e:
        print(f"  ❌ Computation failed: {e}")
    
    REPORT_DATA["gpu"] = gpu_data

# =============================================================================
# STEP 11: GPU PERFORMANCE WITH SCALING
# =============================================================================

def gpu_performance_test():
    """Step 11: GPU Performance test with scaling benchmarks up to 10 seconds"""
    print_section("STEP 11: GPU PERFORMANCE")
    print("-" * 50)
    
    notes = """
    GPU Performance benchmark: tests matrix multiplication with increasing sizes.
    This shows what AI models your GPU can handle based on matrix multiplication speed.
    
    Matrix size to capabilities:
    1024x1024: Very small models, fast operations (<1ms)
    2048x2048: Small models, quick (<1ms)
    4096x4096: Medium models, efficient (~3-4ms)
    8192x8192: Large models, good performance (~28ms)
    12288x12288: Very large models, acceptable (~97ms)
    16384x16384: LLM-scale operations, decent (~220ms)
    24576x24576: Massive operations, still works (~788ms)
    
    What these benchmarks mean for AI:
    - Matrix multiplication is the core operation in neural networks
    - Faster matrix multiplications = faster model training
    - Larger matrices = larger models = more complex AI tasks
    """
    print_notes(11, notes)
    
    def benchmark_matmul(size, repeats=10):
        try:
            a = torch.randn(size, size, device='cuda')
            b = torch.randn(size, size, device='cuda')
            
            # Warmup
            for _ in range(3):
                torch.matmul(a, b)
            torch.cuda.synchronize()
            
            start = time.perf_counter()
            for _ in range(repeats):
                torch.matmul(a, b)
            torch.cuda.synchronize()
            elapsed = (time.perf_counter() - start) / repeats * 1000
            
            return elapsed
        except RuntimeError as e:
            if "out of memory" in str(e):
                return "OOM"
            raise e
    
    print("  Matrix Multiplication Benchmark (10 iterations):")
    print("  " + "-" * 60)
    
    # Test sizes up to 24576x24576
    sizes = [1024, 2048, 4096, 8192, 12288, 16384, 24576]
    results = []
    benchmark_data = []
    
    for size in sizes:
        result = benchmark_matmul(size)
        if result == "OOM":
            print(f"    {size}x{size}: ❌ Out of Memory (VRAM limit reached)")
            benchmark_data.append({"size": size, "status": "OOM"})
            break
        elif result > 10000:  # 10 seconds
            print(f"    {size}x{size}: ⏱️  {result/1000:.2f}s (stopping at 10s threshold)")
            benchmark_data.append({"size": size, "status": "timeout", "time_ms": result})
            break
        else:
            print(f"    {size}x{size}: {result:.2f} ms")
            results.append((size, result))
            benchmark_data.append({"size": size, "status": "success", "time_ms": result})
    
    print("  " + "-" * 60)
    
    # Store benchmark data
    REPORT_DATA["performance"]["matrix_benchmark"] = benchmark_data
    
    # Interpret results
    print("\n  📋 WHAT THESE BENCHMARKS MEAN FOR YOUR GPU:")
    print("  " + "-" * 60)
    
    if results:
        max_size, max_time = results[-1]
        REPORT_DATA["performance"]["max_matrix_size"] = max_size
        REPORT_DATA["performance"]["max_matrix_time_ms"] = max_time
        
        print(f"  ✅ Your GPU handled {max_size}x{max_size} matrix in {max_time:.2f}ms")
        print(f"  ✅ This is an excellent result")
        
        print("\n  📊 CAPABILITIES BASED ON MATRIX SIZE:")
        print("  " + "-" * 60)
        
        has_24576 = any(s == 24576 for s, _ in results)
        has_16384 = any(s == 16384 for s, _ in results)
        has_12288 = any(s == 12288 for s, _ in results)
        has_8192 = any(s == 8192 for s, _ in results)
        has_4096 = any(s == 4096 for s, _ in results)
        
        if has_24576:
            print("  🏆 Your GPU can handle operations up to 24576x24576")
            print("  💡 This means you can run:")
            print("     • Large Language Models (Llama-70B) with proper optimization")
            print("     • Complex image generation (Stable Diffusion, DALL-E)")
            print("     • Large-scale neural network training")
            print("     • Multi-modal AI models (vision + language)")
        elif has_16384:
            print("  ✅ Your GPU can handle operations up to 16384x16384")
            print("  💡 This means you can run:")
            print("     • Medium-Large Language Models (Llama-13B, Mistral)")
            print("     • Advanced computer vision models")
            print("     • Most fine-tuning tasks")
        elif has_12288:
            print("  ✅ Your GPU can handle operations up to 12288x12288")
            print("  💡 This means you can run:")
            print("     • Medium Language Models (Llama-7B)")
            print("     • Standard computer vision models")
            print("     • Most AI research tasks")
        elif has_8192:
            print("  ✅ Your GPU can handle operations up to 8192x8192")
            print("  💡 This means you can run:")
            print("     • Small Language Models")
            print("     • Standard AI tasks")
            print("     • Good for learning and prototyping")
        elif has_4096:
            print("  ✅ Your GPU can handle operations up to 4096x4096")
            print("  💡 This means you can run:")
            print("     • Small neural networks")
            print("     • Basic AI tasks")
        
        print("\n  💡 RECOMMENDATIONS FOR YOUR GPU:")
        print("  " + "-" * 60)
        recommendations = [
            "Use mixed precision (FP16/BF16) for 2x faster training",
            "Use gradient accumulation for larger effective batch sizes",
            "Consider using xformers for optimized attention mechanisms"
        ]
        REPORT_DATA["recommendations"].extend(recommendations)
        for rec in recommendations:
            print(f"  • {rec}")

# =============================================================================
# STEP 12: GPU MEMORY ALLOCATION TEST
# =============================================================================

def gpu_memory_test():
    """Step 12: Test GPU memory allocation"""
    print_section("STEP 12: GPU MEMORY ALLOCATION")
    print("-" * 50)
    
    notes = """
    GPU Memory test: tests how much VRAM you can allocate.
    Your VRAM capacity determines what models and batch sizes you can run.
    """
    print_notes(12, notes)
    
    memory_test_data = {
        "total_vram_gb": None,
        "allocations": [],
        "max_allocated_gb": 0
    }
    
    try:
        print("  Testing memory allocation...")
        torch.cuda.empty_cache()
        
        total_mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        memory_test_data["total_vram_gb"] = total_mem_gb
        print(f"  Total VRAM: {total_mem_gb:.2f} GB")
        
        test_sizes_gb = [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 14.0]
        
        print("\n  Testing memory allocations (GB):")
        print("  " + "-" * 40)
        
        last_success = 0
        
        for size_gb in test_sizes_gb:
            if size_gb > total_mem_gb * 0.9:
                print(f"    {size_gb:.1f} GB: ⏭️  Skipping (near total VRAM)")
                break
            
            elements = int(size_gb * 1e9 / 4)
            try:
                test_tensor = torch.randn(elements, device='cuda')
                allocated = torch.cuda.memory_allocated() / 1e9
                memory_test_data["allocations"].append({"size_gb": size_gb, "allocated_gb": allocated, "success": True})
                print(f"    {size_gb:.1f} GB: ✅ Allocated (Total used: {allocated:.2f} GB)")
                del test_tensor
                torch.cuda.empty_cache()
                last_success = size_gb
                time.sleep(0.1)
            except RuntimeError as e:
                if "out of memory" in str(e):
                    memory_test_data["allocations"].append({"size_gb": size_gb, "success": False, "error": "OOM"})
                    print(f"    {size_gb:.1f} GB: ❌ Out of Memory")
                    break
                else:
                    raise e
        
        print("  " + "-" * 40)
        memory_test_data["max_allocated_gb"] = last_success
        print(f"\n  ✅ Maximum allocated: {last_success:.1f} GB")
        
        if last_success >= 12:
            print("  ✅ Excellent! Your GPU can handle large models!")
        elif last_success >= 8:
            print("  ✅ Good! Your GPU can handle most models.")
        elif last_success >= 4:
            print("  ⚠️  Adequate. You may need to use smaller batch sizes.")
        else:
            print("  ⚠️  Limited VRAM. Consider using model quantization.")
            
    except Exception as e:
        print(f"  ⚠️  Memory test error: {e}")
    
    REPORT_DATA["performance"]["memory_test"] = memory_test_data

# =============================================================================
# STEP 13: NVIDIA DRIVER INFO
# =============================================================================

def get_nvidia_info():
    """Step 13: Enhanced NVIDIA driver info"""
    print_section("STEP 13: NVIDIA DRIVER INFO")
    print("-" * 50)
    
    notes = """
    NVIDIA Driver info: driver version, temperature, power draw, utilization.
    If "Could not query" appears, try running the terminal as Administrator.
    On Windows: Right-click terminal -> Run as administrator
    """
    print_notes(13, notes)
    
    nvidia_data = {
        "driver_version": None,
        "cuda_version": None,
        "gpu_name": None,
        "temperature": None,
        "power_draw": None,
        "power_limit": None,
        "gpu_utilization": None,
        "memory_utilization": None,
        "performance_state": None,
        "sm_clock": None,
        "memory_clock": None,
        "query_success": False
    }
    
    query_success = False
    try:
        print("  Querying GPU details with nvidia-smi...")
        
        queries = [
            ('index', 'GPU Index'),
            ('name', 'GPU Name'),
            ('driver_version', 'Driver Version'),
            ('cuda_version', 'CUDA Version'),
            ('memory.total', 'Total Memory'),
            ('memory.used', 'Memory Used'),
            ('memory.free', 'Memory Free'),
            ('temperature.gpu', 'GPU Temperature'),
            ('power.draw', 'Power Draw'),
            ('power.limit', 'Power Limit'),
            ('utilization.gpu', 'GPU Utilization'),
            ('utilization.memory', 'Memory Utilization'),
            ('compute_mode', 'Compute Mode'),
            ('pstate', 'Performance State'),
            ('clocks.sm', 'SM Clock'),
            ('clocks.mem', 'Memory Clock')
        ]
        
        query_string = ','.join([q[0] for q in queries])
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=' + query_string, '--format=csv,noheader'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = [p.strip() for p in result.stdout.strip().split(',')]
            for i, (key, display_name) in enumerate(queries):
                if i < len(parts) and parts[i] and parts[i] != '[Not Supported]':
                    # Map to nvidia_data fields
                    if key == 'name':
                        nvidia_data["gpu_name"] = parts[i]
                    elif key == 'driver_version':
                        nvidia_data["driver_version"] = parts[i]
                    elif key == 'cuda_version':
                        nvidia_data["cuda_version"] = parts[i]
                    elif key == 'temperature.gpu':
                        nvidia_data["temperature"] = parts[i]
                    elif key == 'power.draw':
                        nvidia_data["power_draw"] = parts[i]
                    elif key == 'power.limit':
                        nvidia_data["power_limit"] = parts[i]
                    elif key == 'utilization.gpu':
                        nvidia_data["gpu_utilization"] = parts[i]
                    elif key == 'utilization.memory':
                        nvidia_data["memory_utilization"] = parts[i]
                    elif key == 'pstate':
                        nvidia_data["performance_state"] = parts[i]
                    elif key == 'clocks.sm':
                        nvidia_data["sm_clock"] = parts[i]
                    elif key == 'clocks.mem':
                        nvidia_data["memory_clock"] = parts[i]
                    print(f"  {display_name}: {parts[i]}")
            nvidia_data["query_success"] = True
            query_success = True
        else:
            print("  ⚠️  nvidia-smi query returned no data")
    except subprocess.TimeoutExpired:
        print("  ⚠️  nvidia-smi timed out")
    except Exception as e:
        print(f"  ⚠️  Could not query GPU: {e}")
    
    # Fallback using PyTorch
    if not query_success and HAS_TORCH and torch.cuda.is_available():
        print("\n  Using PyTorch fallback:")
        try:
            props = torch.cuda.get_device_properties(0)
            nvidia_data["gpu_name"] = torch.cuda.get_device_name(0)
            nvidia_data["total_vram_gb"] = props.total_memory / 1e9
            nvidia_data["compute_capability"] = f"{props.major}.{props.minor}"
            nvidia_data["multi_processors"] = props.multi_processor_count
            print(f"  GPU Name: {torch.cuda.get_device_name(0)}")
            print(f"  Total VRAM: {props.total_memory / 1e9:.2f} GB")
            print(f"  Compute Capability: {props.major}.{props.minor}")
            print(f"  Multi-processors: {props.multi_processor_count}")
        except Exception as e:
            print(f"  ⚠️  PyTorch fallback failed: {e}")
    
    # Try nvidia-smi regular output
    try:
        print("\n  nvidia-smi status:")
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.split('\n')
            for line in lines[:8]:
                if line.strip():
                    print(f"    {line}")
    except Exception as e:
        print(f"  ⚠️  Could not get nvidia-smi status: {e}")
    
    REPORT_DATA["gpu"]["nvidia_info"] = nvidia_data

# =============================================================================
# STEP 14: AI/ML SOFTWARE & VIRTUAL ENVIRONMENT
# =============================================================================

def get_software_info():
    """Step 14: Check installed software, versions, and virtual environment"""
    print_section("STEP 14: AI/ML SOFTWARE & VIRTUAL ENVIRONMENT")
    print("-" * 50)
    
    notes = """
    Software & Environment checks: Python environment (venv/conda), AI frameworks installed.
    Virtual environments prevent package conflicts. Always use one for AI projects.
    """
    print_notes(14, notes)
    
    software_data = {
        "virtual_environment": {
            "active": False,
            "type": "None",
            "path": None
        },
        "frameworks": {},
        "installed_count": 0,
        "total_count": 0
    }
    
    # Virtual Environment Check
    print_subsection("Python Environment Check")
    
    in_venv = False
    venv_type = "None"
    
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        in_venv = True
        venv_type = "venv"
    
    if 'CONDA_PREFIX' in os.environ:
        in_venv = True
        venv_type = "Conda"
    
    if hasattr(sys, 'prefix') and 'VIRTUAL_ENV' in os.environ:
        in_venv = True
        venv_type = "virtualenv"
    
    python_path = sys.executable
    python_location = os.path.dirname(python_path)
    
    software_data["virtual_environment"]["active"] = in_venv
    software_data["virtual_environment"]["type"] = venv_type
    software_data["virtual_environment"]["path"] = python_path
    
    print(f"  Python Executable: {python_path}")
    print(f"  Python Location: {python_location}")
    
    if in_venv:
        print(f"  ✅ Virtual Environment: ACTIVE ({venv_type})")
        if 'VIRTUAL_ENV' in os.environ:
            software_data["virtual_environment"]["env_path"] = os.environ['VIRTUAL_ENV']
            print(f"    Virtual Env Path: {os.environ['VIRTUAL_ENV']}")
        if 'CONDA_PREFIX' in os.environ:
            software_data["virtual_environment"]["conda_path"] = os.environ['CONDA_PREFIX']
            print(f"    Conda Env Path: {os.environ['CONDA_PREFIX']}")
    else:
        print("  ⚠️  No virtual environment detected!")
        print("    ℹ️  You are using system Python (global installation)")
        print("    📝 Recommendation: Use a virtual environment for AI/ML projects")
    
    # AI/ML Frameworks Check
    print_subsection("AI/ML Frameworks")
    
    frameworks = {
        'torch': 'PyTorch',
        'tensorflow': 'TensorFlow',
        'jax': 'JAX',
        'transformers': 'Hugging Face Transformers',
        'xformers': 'Xformers',
        'langchain': 'LangChain',
        'accelerate': 'Hugging Face Accelerate',
        'diffusers': 'Diffusers',
        'scipy': 'SciPy',
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'matplotlib': 'Matplotlib',
        'seaborn': 'Seaborn',
        'scikit-learn': 'Scikit-Learn',
        'opencv-python': 'OpenCV'
    }
    
    installed = 0
    installed_list = []
    missing_list = []
    
    for module, name in frameworks.items():
        try:
            mod = importlib.import_module(module.replace('-', '_'))
            version = mod.__version__
            software_data["frameworks"][name] = {"installed": True, "version": version}
            print(f"  ✅ {name}: {version}")
            installed += 1
            installed_list.append(name)
        except ImportError:
            software_data["frameworks"][name] = {"installed": False, "version": None}
            print(f"  ❌ {name}: Not installed")
            missing_list.append(name)
    
    software_data["installed_count"] = installed
    software_data["total_count"] = len(frameworks)
    print(f"\n  Total AI/ML packages installed: {installed}/{len(frameworks)}")
    
    REPORT_DATA["software"] = software_data
    
    return in_venv, installed_list, missing_list

# =============================================================================
# STEP 15: CPU STRESS TEST
# =============================================================================

def cpu_stress_test():
    """Step 15: CPU stress test with diagnosis"""
    print_section("STEP 15: CPU STRESS TEST")
    print("-" * 50)
    
    notes = """
    CPU Stress Test: performs heavy calculations to test CPU performance.
    Fast completion (<8s) = excellent performance. Frequency drop >20% = thermal throttling.
    """
    print_notes(15, notes)
    
    physical_cores = psutil.cpu_count(logical=False)
    logical_cores = psutil.cpu_count(logical=True)
    freq_before = psutil.cpu_freq()
    
    stress_data = {
        "physical_cores": physical_cores,
        "logical_cores": logical_cores,
        "base_frequency": freq_before.max if freq_before else None,
        "duration_seconds": None,
        "threads_used": None,
        "cpu_usage_after": None,
        "frequency_drop_percent": None,
        "issues": [],
        "recommendations": [],
        "status": "PASS"
    }
    
    print(f"  Physical Cores: {physical_cores}")
    print(f"  Logical Cores: {logical_cores}")
    if freq_before:
        print(f"  Base Frequency: {freq_before.max:.2f} MHz")
    
    print("  Running CPU stress test (10 seconds)...")
    start = time.time()
    
    def cpu_work():
        x = 0
        for i in range(20_000_000):
            x += i ** 2
        return x
    
    try:
        from multiprocessing import Pool
        cores_to_use = min(physical_cores, 4) if physical_cores else 1
        with Pool(processes=cores_to_use) as pool:
            pool.map(lambda _: cpu_work(), range(cores_to_use))
        elapsed = time.time() - start
        threads_used = cores_to_use
    except:
        cpu_work()
        elapsed = time.time() - start
        threads_used = 1
    
    cpu_percent = psutil.cpu_percent(interval=1)
    freq_after = psutil.cpu_freq()
    
    stress_data["duration_seconds"] = elapsed
    stress_data["threads_used"] = threads_used
    stress_data["cpu_usage_after"] = cpu_percent
    
    print(f"\n  📊 Results:")
    print(f"    Test Duration: {elapsed:.2f} seconds")
    print(f"    Threads Used: {threads_used}")
    print(f"    CPU Usage: {cpu_percent}%")
    
    freq_drop = 0
    if freq_before and freq_after:
        freq_drop = ((freq_before.max - freq_after.current) / freq_before.max) * 100 if freq_before.max > 0 else 0
        stress_data["frequency_drop_percent"] = freq_drop
        print(f"    Frequency During Test: {freq_after.current:.2f} MHz (Drop: {freq_drop:.1f}%)")
    
    print("\n  📋 DIAGNOSIS:")
    print("  " + "-" * 50)
    
    expected_time = 8.0
    if elapsed > expected_time * 1.5:
        stress_data["issues"].append(f"CPU test took {elapsed:.1f}s (expected ~{expected_time:.1f}s)")
        stress_data["recommendations"].append("Check for thermal throttling using HWMonitor")
        stress_data["recommendations"].append("Ensure adequate cooling and airflow")
        stress_data["status"] = "WARNING"
    
    if freq_before and freq_after:
        if freq_drop > 20:
            stress_data["issues"].append(f"Significant frequency drop: {freq_drop:.1f}%")
            stress_data["recommendations"].append("Monitor CPU temperatures during load")
            stress_data["recommendations"].append("Consider improving CPU cooling")
            stress_data["status"] = "WARNING"
    
    if cpu_percent < 80 and threads_used > 1:
        stress_data["issues"].append(f"Low CPU utilization: {cpu_percent}% with {threads_used} threads")
        stress_data["recommendations"].append("Check system Power Plan (set to High Performance)")
        stress_data["status"] = "WARNING"
    
    if physical_cores and physical_cores < 8:
        stress_data["issues"].append(f"Limited physical cores: {physical_cores} (recommended 8+ for AI)")
        stress_data["recommendations"].append("Consider upgrading CPU for data preprocessing")
        stress_data["status"] = "WARNING"
    
    if stress_data["issues"]:
        print("\n  ⚠️  Issues Found:")
        for issue in stress_data["issues"]:
            print(f"    • {issue}")
        print("\n  📝 Recommendations:")
        for rec in stress_data["recommendations"]:
            print(f"    {rec}")
    else:
        print("  ✅ No issues detected. CPU performance is excellent!")
        stress_data["status"] = "PASS"
    
    REPORT_DATA["stress_tests"]["cpu"] = stress_data

# =============================================================================
# STEP 16: GPU STRESS TEST
# =============================================================================

def gpu_stress_test():
    """Step 16: GPU stress test with detailed explanation"""
    print_section("STEP 16: GPU STRESS TEST")
    print("-" * 50)
    
    notes = """
    GPU Stress Test: 5 iterations of 8192x8192 matrix multiplication.
    0% Utilization is normal - modern GPUs complete operations before monitoring tools sample.
    For better utilization, use larger matrices or increase batch size in training.
    """
    print_notes(16, notes)
    
    stress_data = {
        "iterations": 5,
        "matrix_size": 8192,
        "results": [],
        "max_temperature": None,
        "max_power": None,
        "avg_temperature": None,
        "duration_seconds": None,
        "issues": [],
        "recommendations": [],
        "status": "PASS"
    }
    
    if not HAS_TORCH:
        print("  ⚠️  GPU stress test skipped (PyTorch not installed)")
        return
    
    if not torch.cuda.is_available():
        print("  ⚠️  GPU stress test skipped (CUDA not available)")
        return
    
    gpu_name = torch.cuda.get_device_name(0)
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"  GPU: {gpu_name}")
    print(f"  VRAM: {gpu_mem:.2f} GB")
    
    print("\n  Initial GPU Status:")
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw,clocks.sm,clocks.mem',
             '--format=csv,noheader'],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            stats = [s.strip() for s in result.stdout.strip().split(',')]
            if len(stats) >= 6:
                print(f"    GPU Utilization: {stats[0]}")
                print(f"    Memory Used: {stats[1]}")
                print(f"    Temperature: {stats[2]}")
                print(f"    Power Draw: {stats[3]}")
                print(f"    SM Clock: {stats[4]}")
                print(f"    Memory Clock: {stats[5]}")
    except:
        pass
    
    print("\n  Running GPU stress test with larger matrices...")
    print("  💡 Using 8192x8192 matrices for longer processing time")
    start = time.time()
    
    max_temp = 0
    max_power = 0
    all_temps = []
    
    for i in range(5):
        print(f"  Iteration {i+1}/5...")
        a = torch.randn(8192, 8192, device='cuda')
        b = torch.randn(8192, 8192, device='cuda')
        c = torch.matmul(a, b)
        torch.cuda.synchronize()
        time.sleep(0.5)
        
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=temperature.gpu,power.draw,utilization.gpu,memory.used',
                 '--format=csv,noheader'],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                stats = [s.strip() for s in result.stdout.strip().split(',')]
                if len(stats) >= 4:
                    temp = float(stats[0].replace('°C', '').strip())
                    power = float(stats[1].replace('W', '').strip())
                    util = stats[2]
                    mem = stats[3]
                    all_temps.append(temp)
                    if temp > max_temp:
                        max_temp = temp
                    if power > max_power:
                        max_power = power
                    stress_data["results"].append({
                        "iteration": i+1,
                        "temperature": temp,
                        "power": power,
                        "utilization": util,
                        "memory_used": mem
                    })
                    print(f"    [Monitor] Util: {util}, Mem: {mem}, Temp: {temp}°C, Power: {power}W")
        except:
            pass
    
    elapsed = time.time() - start
    avg_temp = sum(all_temps) / len(all_temps) if all_temps else 0
    
    stress_data["duration_seconds"] = elapsed
    stress_data["max_temperature"] = max_temp
    stress_data["max_power"] = max_power
    stress_data["avg_temperature"] = avg_temp
    
    print(f"\n  ✅ GPU Test Complete in {elapsed:.2f} seconds")
    
    print("\n  📋 DIAGNOSIS:")
    print("  " + "-" * 50)
    
    if max_power < 100:
        stress_data["issues"].append(f"Low power draw: {max_power:.1f}W (expected 300W)")
        stress_data["recommendations"].append("Try increasing matrix size or batch size")
        stress_data["recommendations"].append("Check if GPU is in power-saving mode")
        stress_data["status"] = "WARNING"
    elif max_power > 300:
        print("  ✅ GPU power draw is excellent!")
    
    if max_temp > 85:
        stress_data["issues"].append(f"High GPU temperature: {max_temp:.0f}°C")
        stress_data["recommendations"].append("Improve cooling or reduce workload")
        stress_data["status"] = "WARNING"
    elif max_temp > 70:
        print(f"  ✅ Good GPU temperature: {max_temp:.0f}°C")
    else:
        print(f"  ✅ Excellent GPU temperature: {max_temp:.0f}°C")
    
    if stress_data["issues"]:
        print("\n  ⚠️  Issues Found:")
        for issue in stress_data["issues"]:
            print(f"    • {issue}")
        print("\n  📝 Recommendations:")
        for rec in stress_data["recommendations"]:
            print(f"    {rec}")
    else:
        print("  ✅ No issues detected. GPU performance is excellent!")
    
    print("\n  💡 PERFORMANCE TIPS:")
    print("  " + "-" * 50)
    tips = [
        "Use larger batch sizes for better utilization",
        "Enable mixed precision training (AMP)",
        "Use torch.compile() for PyTorch 2.0+",
        "Set system Power Plan to 'High Performance'"
    ]
    stress_data["recommendations"].extend(tips)
    for tip in tips:
        print(f"  • {tip}")
    
    REPORT_DATA["stress_tests"]["gpu"] = stress_data

# =============================================================================
# STEP 17: STORAGE SPEED TEST
# =============================================================================

def storage_speed_test():
    """Step 17: Storage speed test with diagnosis"""
    print_section("STEP 17: STORAGE SPEED TEST")
    print("-" * 50)
    
    notes = """
    Storage Speed Test: measures read/write speeds.
    NVMe SSD: 2000+ MB/s (excellent), SATA SSD: 400-500 MB/s (good), HDD: 50-150 MB/s (too slow for AI).
    """
    print_notes(17, notes)
    
    storage_test_data = {
        "test_size_mb": 100,
        "write_speed_mb_s": None,
        "read_speed_mb_s": None,
        "drive_type": "Unknown",
        "status": "PASS",
        "issues": [],
        "recommendations": []
    }
    
    try:
        import tempfile
        
        test_size = 100 * 1024 * 1024
        temp_file = tempfile.mktemp()
        
        print(f"  Testing with {get_size(test_size)} file...")
        
        start = time.time()
        with open(temp_file, 'wb') as f:
            f.write(os.urandom(test_size))
        write_time = time.time() - start
        write_speed = test_size / write_time / 1024 / 1024
        
        start = time.time()
        with open(temp_file, 'rb') as f:
            data = f.read()
        read_time = time.time() - start
        read_speed = test_size / read_time / 1024 / 1024
        
        os.remove(temp_file)
        
        storage_test_data["write_speed_mb_s"] = write_speed
        storage_test_data["read_speed_mb_s"] = read_speed
        
        print(f"\n  📊 Results:")
        print(f"    Write Speed: {write_speed:.2f} MB/s")
        print(f"    Read Speed: {read_speed:.2f} MB/s")
        
        print("\n  📋 DIAGNOSIS:")
        print("  " + "-" * 50)
        
        if write_speed > 500:
            storage_test_data["drive_type"] = "NVMe SSD"
            print("  ✅ Excellent performance - NVMe SSD detected")
            if write_speed > 1000:
                print("  ✅ PCIe Gen 3/4 NVMe SSD with excellent speeds")
        elif write_speed > 200:
            storage_test_data["drive_type"] = "SATA SSD"
            print("  ✅ Good performance - SATA SSD detected")
            storage_test_data["issues"].append("SATA SSD detected (slower than NVMe)")
            storage_test_data["recommendations"].append("Consider upgrading to NVMe SSD for faster data loading")
            storage_test_data["status"] = "WARNING"
        elif write_speed > 50:
            storage_test_data["drive_type"] = "HDD"
            storage_test_data["issues"].append("HDD detected - Slow for AI workloads")
            storage_test_data["recommendations"].append("Upgrade to NVMe SSD for significantly better performance")
            storage_test_data["status"] = "WARNING"
        else:
            storage_test_data["drive_type"] = "Very Slow Drive"
            storage_test_data["issues"].append("Very slow storage detected!")
            storage_test_data["recommendations"].append("IMMEDIATELY upgrade to NVMe SSD for AI work")
            storage_test_data["status"] = "FAIL"
            
    except Exception as e:
        print(f"  ⚠️  Storage test error: {e}")
        storage_test_data["status"] = "ERROR"
        storage_test_data["issues"].append(f"Storage test error: {e}")
    
    REPORT_DATA["storage"]["speed_test"] = storage_test_data

# =============================================================================
# STEP 18: NETWORK SPEED TEST
# =============================================================================

def network_speed_test():
    """Step 18: Network speed test with diagnosis"""
    print_section("STEP 18: NETWORK SPEED TEST")
    print("-" * 50)
    
    notes = """
    Network Speed Test: measures download/upload speeds and ping.
    Recommended: 100+ Mbps download, 20+ Mbps upload, <50ms ping for remote work.
    """
    print_notes(18, notes)
    
    network_test_data = {
        "download_mbps": None,
        "upload_mbps": None,
        "ping_ms": None,
        "status": "PASS",
        "issues": [],
        "recommendations": []
    }
    
    if HAS_SPEEDTEST:
        try:
            print("  Running speed test (may take 30-60 seconds)...")
            st = speedtest.Speedtest()
            st.get_best_server()
            
            download = st.download() / 1_000_000
            upload = st.upload() / 1_000_000
            ping = st.results.ping
            
            network_test_data["download_mbps"] = download
            network_test_data["upload_mbps"] = upload
            network_test_data["ping_ms"] = ping
            
            print(f"\n  📊 Results:")
            print(f"    Download Speed: {download:.2f} Mbps")
            print(f"    Upload Speed: {upload:.2f} Mbps")
            print(f"    Ping: {ping:.2f} ms")
            
            print("\n  📋 DIAGNOSIS:")
            print("  " + "-" * 50)
            
            if download > 100:
                print("  ✅ Excellent download speed")
            elif download > 50:
                network_test_data["issues"].append(f"Moderate download speed: {download:.1f} Mbps")
                network_test_data["recommendations"].append("Large models may take time to download")
                network_test_data["status"] = "WARNING"
                print("  ⚠️  Adequate download speed")
                print("  💡 Large models may take time to download")
            else:
                network_test_data["issues"].append(f"Slow download speed: {download:.1f} Mbps")
                network_test_data["recommendations"].append("Consider downloading models at work/school")
                network_test_data["status"] = "WARNING"
                print("  ❌ Slow download speed")
                print("  💡 Consider downloading models at work/school")
            
            if upload > 20:
                print("  ✅ Excellent upload speed")
            else:
                network_test_data["issues"].append(f"Upload speed may be slow: {upload:.1f} Mbps")
                network_test_data["recommendations"].append("Uploading models may take time")
                network_test_data["status"] = "WARNING"
                print("  ⚠️  Upload speed may be slow for sharing models")
                
        except Exception as e:
            print(f"  ⚠️  Speed test error: {e}")
            network_test_data["status"] = "ERROR"
            network_test_data["issues"].append(f"Speed test error: {e}")
    else:
        print("  ⚠️  Speedtest not installed (pip install speedtest-cli)")
        network_test_data["status"] = "SKIPPED"
    
    REPORT_DATA["network"]["speed_test"] = network_test_data

# =============================================================================
# STEP 19: POWER SUPPLY TEST
# =============================================================================

def power_supply_test():
    """Step 19: Test power delivery to GPU and provide recommendations"""
    print_section("STEP 19: POWER SUPPLY TEST")
    print("-" * 50)
    
    notes = """
    Power Supply Test: checks GPU power draw vs expected.
    High-end GPUs need 300W+ under full load. Insufficient power causes throttling.
    Current idle power (~45W) is normal. Under load should reach 300W+.
    """
    print_notes(19, notes)
    
    power_data = {
        "current_power_w": None,
        "power_limit_w": None,
        "gpu_utilization": None,
        "temperature": None,
        "memory_total_gb": None,
        "memory_used_gb": None,
        "is_laptop": False,
        "recommendations": [],
        "status": "PASS"
    }
    
    print("  Power supply information:")
    print("  " + "-" * 50)
    
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=power.draw,power.limit,utilization.gpu,temperature.gpu,memory.total,memory.used',
             '--format=csv,noheader'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = [p.strip() for p in result.stdout.strip().split(',')]
            if len(parts) >= 6:
                power_data["current_power_w"] = parts[0]
                power_data["power_limit_w"] = parts[1]
                power_data["gpu_utilization"] = parts[2]
                power_data["temperature"] = parts[3]
                power_data["memory_total_gb"] = parts[4]
                power_data["memory_used_gb"] = parts[5]
                print(f"  Current Power Draw: {parts[0]}")
                print(f"  Power Limit (Max): {parts[1]}")
                print(f"  GPU Utilization: {parts[2]}")
                print(f"  GPU Temperature: {parts[3]}")
                print(f"  Memory Total: {parts[4]}")
                print(f"  Memory Used: {parts[5]}")
        else:
            print("  ⚠️  Could not get power information")
    except Exception as e:
        print(f"  ⚠️  Could not get power information: {e}")
    
    print("\n  📋 POWER DELIVERY ANALYSIS:")
    print("  " + "-" * 50)
    
    is_laptop = False
    try:
        if IS_WINDOWS:
            result = run_command("wmic computersystem get model")
            if result and any(x in result.lower() for x in ['laptop', 'notebook', 'tablet']):
                is_laptop = True
        elif IS_LINUX:
            if os.path.exists('/sys/class/dmi/id/chassis_type'):
                with open('/sys/class/dmi/id/chassis_type', 'r') as f:
                    chassis = f.read().strip()
                    is_laptop = chassis in ['8', '9', '10', '11', '31', '32']
    except:
        pass
    
    power_data["is_laptop"] = is_laptop
    
    if is_laptop:
        print("  ℹ️  Laptop detected - power delivery may be limited")
        print("  💡 For best performance, plug into AC power")
        power_data["recommendations"].append("Use AC power for maximum performance")
        power_data["status"] = "INFO"
    else:
        print("  ℹ️  Desktop detected - power supply should be adequate")
    
    print("\n  💡 RECOMMENDED POWER SUPPLY SPECIFICATIONS:")
    print("  " + "-" * 50)
    recommendations = [
        "Recommended PSU: 750W - 850W for high-end GPUs",
        "Minimum PSU: 650W for most AI workloads",
        "Ensure proper PCIe power cables are connected"
    ]
    for rec in recommendations:
        print(f"  • {rec}")
        power_data["recommendations"].append(rec)
    
    REPORT_DATA["power_supply"] = power_data

# =============================================================================
# STEP 20: SYSTEM SUMMARY
# =============================================================================

def system_summary():
    """Step 20: Overall system readiness assessment"""
    print_section("STEP 20: SYSTEM SUMMARY")
    print("-" * 50)
    
    notes = """
    System Summary: quick overview of your system's AI readiness.
    CPU, RAM, GPU, Storage, and Network ratings. Shows what AI workloads you can handle.
    """
    print_notes(20, notes)
    
    summary_data = {
        "cpu": {},
        "ram": {},
        "gpu": {},
        "storage": {},
        "network": {},
        "overall_ready": False
    }
    
    print("  📊 System Readiness Assessment:\n")
    
    cpu_cores = psutil.cpu_count(logical=True)
    cpu_score = "✅ Excellent" if cpu_cores >= 16 else "✅ Good" if cpu_cores >= 8 else "⚠️  Adequate" if cpu_cores >= 4 else "❌ Insufficient"
    summary_data["cpu"] = {"cores": cpu_cores, "score": cpu_score}
    print(f"  CPU: {cpu_cores} cores - {cpu_score}")
    
    mem = psutil.virtual_memory()
    mem_gb = mem.total / 1e9
    mem_score = "✅ Excellent" if mem_gb >= 32 else "✅ Good" if mem_gb >= 16 else "⚠️  Adequate" if mem_gb >= 8 else "❌ Insufficient"
    summary_data["ram"] = {"gb": mem_gb, "score": mem_score}
    print(f"  RAM: {mem_gb:.0f} GB - {mem_score}")
    
    if HAS_TORCH and torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        gpu_score = "✅ Excellent" if "RTX 50" in gpu_name or "RTX 40" in gpu_name or "RTX A" in gpu_name else "✅ Good"
        summary_data["gpu"] = {"name": gpu_name, "vram_gb": gpu_mem, "score": gpu_score}
        print(f"  GPU: {gpu_name} ({gpu_mem:.1f} GB) - {gpu_score}")
    elif HAS_TORCH:
        summary_data["gpu"] = {"name": "Not detected", "score": "❌ Not detected"}
        print("  GPU: ❌ Not detected - Will use CPU only (much slower)")
    else:
        summary_data["gpu"] = {"name": "Could not check", "score": "⚠️  Could not check"}
        print("  GPU: ⚠️  Could not check GPU (PyTorch not installed)")
    
    try:
        partitions = psutil.disk_partitions()
        has_ssd = False
        for partition in partitions:
            if IS_WINDOWS:
                result = run_command(f'powershell "Get-PhysicalDisk | Where-Object {{$_.DeviceNumber -eq (Get-Partition -DriveLetter {partition.device[0]} | Get-Disk).Number}} | Select-Object MediaType"')
                if result and "SSD" in result:
                    has_ssd = True
                    break
            elif IS_LINUX:
                # Check if any partition is on SSD (simplified check)
                if partition.device and 'nvme' in partition.device.lower():
                    has_ssd = True
                    break
        
        storage_score = "✅ Excellent (SSD)" if has_ssd else "⚠️  HDD detected (consider SSD upgrade)"
        summary_data["storage"] = {"has_ssd": has_ssd, "score": storage_score}
        print(f"  Storage: {storage_score}")
    except:
        summary_data["storage"] = {"has_ssd": False, "score": "⚠️  Could not determine"}
        print("  Storage: ⚠️  Could not determine drive type")
    
    try:
        socket.gethostbyname('8.8.8.8')
        network_score = "✅ Available"
        summary_data["network"] = {"internet": True, "score": network_score}
    except:
        network_score = "❌ Not available"
        summary_data["network"] = {"internet": False, "score": network_score}
    print(f"  Network Internet: {network_score}")
    
    print("\n" + "="*70)
    print("  Overall Readiness for AI/ML Workloads:")
    
    if HAS_TORCH and torch.cuda.is_available():
        summary_data["overall_ready"] = True
        print("  ✅ Your system is READY for AI/ML development!")
        if "RTX 50" in gpu_name or "RTX 40" in gpu_name:
            print(f"  ✅ {gpu_name} with {gpu_mem:.1f}GB VRAM is excellent for most AI models")
        print("  ✅ Sufficient RAM for data processing")
        print("  ✅ Modern CPU with multiple cores for data preprocessing")
        
        REPORT_DATA["recommendations"].append("Your system is ready for AI/ML development")
        REPORT_DATA["recommendations"].append("Use mixed precision training (AMP) for best performance")
        REPORT_DATA["recommendations"].append("Consider using PyTorch 2.0+ for torch.compile() optimization")
    else:
        summary_data["overall_ready"] = False
        print("  ⚠️  System is partially ready but missing GPU support")
        print("  ℹ️  Install NVIDIA drivers and PyTorch with CUDA support")
        REPORT_DATA["recommendations"].append("Install NVIDIA drivers and PyTorch with CUDA support")
    
    print("="*70)
    
    REPORT_DATA["summary"] = summary_data

# =============================================================================
# VIRTUAL ENVIRONMENT SETUP WIZARD
# =============================================================================

def show_environment_comparison():
    """Display comparison of different virtual environment tools"""
    print("\n  📋 Virtual Environment Comparison:")
    print("  " + "="*70)
    print("  Tool        | Best For                    | Key Features")
    print("  " + "-"*70)
    print("  1. venv     | Simple Python projects      | Built-in, lightweight, pip-based")
    print("  2. conda    | GPU/ML workloads (CUDA)     | Handles non-Python deps, binary packages")
    print("  3. micromamba | Fast conda alternative   | Same as conda, but faster")
    print("  4. uv       | Modern Python projects      | Very fast, lockfiles, pip-compatible")
    print("  5. None     | Skip installation           | No virtual environment setup")
    print("  " + "="*70)
    
    print("\n  📝 Recommendation for your system:")
    print("  🏆  conda or micromamba - Best for CUDA/GPU dependencies")
    print("  ✅  uv - Great for pure Python, but CUDA support is limited")
    print("  ⚠️  venv - Lightweight but doesn't handle CUDA well")
    print("  ⏭️  None - Skip setup for now")

def create_environment_with_tool(tool, env_name, installed_list):
    """Create a virtual environment using the selected tool"""
    
    if tool == "none":
        print("\n⏭️  Skipping virtual environment setup.")
        print("   You can create one manually later when ready.")
        print("\n   Manual setup options:")
        print("   • venv:   python -m venv ai_env")
        print("   • conda:  conda create -n ai_env python=3.12")
        print("   • uv:     uv venv ai_env")
        print("   • micromamba: micromamba create -n ai_env python=3.12")
        return None, None, None
    
    print(f"\n📥 Creating virtual environment '{env_name}' with {tool}...")
    
    if tool == "venv":
        try:
            subprocess.run([sys.executable, '-m', 'venv', env_name], check=True, capture_output=True)
            print(f"  ✅ Virtual environment '{env_name}' created successfully with venv!")
            
            if IS_WINDOWS:
                activate_cmd = f"{env_name}\\Scripts\\activate"
                pip_cmd = f"{env_name}\\Scripts\\pip"
                python_cmd = f"{env_name}\\Scripts\\python"
            else:
                activate_cmd = f"source {env_name}/bin/activate"
                pip_cmd = f"{env_name}/bin/pip"
                python_cmd = f"{env_name}/bin/python"
            
            return activate_cmd, pip_cmd, python_cmd
            
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to create venv: {e}")
            return None, None, None
    
    elif tool == "conda":
        try:
            subprocess.run(['conda', '--version'], check=True, capture_output=True)
            print(f"  ✅ Conda detected, creating environment...")
            
            subprocess.run(['conda', 'create', '-n', env_name, f'python={sys.version_info.major}.{sys.version_info.minor}', '-y'], 
                          check=True, capture_output=True)
            print(f"  ✅ Conda environment '{env_name}' created successfully!")
            
            activate_cmd = f"conda activate {env_name}"
            pip_cmd = f"conda run -n {env_name} pip"
            python_cmd = f"conda run -n {env_name} python"
            
            return activate_cmd, pip_cmd, python_cmd
            
        except FileNotFoundError:
            print("  ❌ Conda is not installed!")
            print("  ℹ️  Install Miniconda from: https://docs.conda.io/en/latest/miniconda.html")
            return None, None, None
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to create conda environment: {e}")
            return None, None, None
    
    elif tool == "micromamba":
        try:
            subprocess.run(['micromamba', '--version'], check=True, capture_output=True)
            print(f"  ✅ Micromamba detected, creating environment...")
            
            subprocess.run(['micromamba', 'create', '-n', env_name, f'python={sys.version_info.major}.{sys.version_info.minor}', '-y'], 
                          check=True, capture_output=True)
            print(f"  ✅ Micromamba environment '{env_name}' created successfully!")
            
            activate_cmd = f"micromamba activate {env_name}"
            pip_cmd = f"micromamba run -n {env_name} pip"
            python_cmd = f"micromamba run -n {env_name} python"
            
            return activate_cmd, pip_cmd, python_cmd
            
        except FileNotFoundError:
            print("  ❌ Micromamba is not installed!")
            print("  ℹ️  Install from: https://github.com/mamba-org/micromamba")
            return None, None, None
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to create micromamba environment: {e}")
            return None, None, None
    
    elif tool == "uv":
        try:
            subprocess.run(['uv', '--version'], check=True, capture_output=True)
            print(f"  ✅ uv detected, creating environment...")
            
            subprocess.run(['uv', 'venv', env_name], check=True, capture_output=True)
            print(f"  ✅ uv environment '{env_name}' created successfully!")
            
            if IS_WINDOWS:
                activate_cmd = f"{env_name}\\Scripts\\activate"
                pip_cmd = f"uv pip install"
                python_cmd = f"{env_name}\\Scripts\\python"
            else:
                activate_cmd = f"source {env_name}/bin/activate"
                pip_cmd = f"uv pip install"
                python_cmd = f"{env_name}/bin/python"
            
            return activate_cmd, pip_cmd, python_cmd
            
        except FileNotFoundError:
            print("  ❌ uv is not installed!")
            print("  ℹ️  Install from: https://docs.astral.sh/uv/")
            print("     pip install uv")
            return None, None, None
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to create uv environment: {e}")
            return None, None, None
    
    return None, None, None

def virtual_environment_setup_wizard(in_venv, installed_list, missing_list):
    """Interactive wizard to set up virtual environment with tool selection"""
    
    print("\n" + "="*70)
    print("🔧 VIRTUAL ENVIRONMENT SETUP WIZARD")
    print("="*70)
    
    # Initialize virtual environment setup data
    venv_setup_data = {
        "created": False,
        "tool_used": None,
        "env_name": None,
        "packages_installed": False
    }
    
    if in_venv:
        print("\n✅ You are already in a virtual environment!")
        print("\n📦 Missing packages to install:")
        if missing_list:
            for pkg in missing_list:
                if pkg != 'torch':
                    print(f"    - {pkg}")
        else:
            print("    ✅ All AI/ML packages are installed!")
        venv_setup_data["created"] = True
        venv_setup_data["tool_used"] = "existing"
        REPORT_DATA["virtual_environment_setup"] = venv_setup_data
        return
    
    print("\n⚠️  You are NOT in a virtual environment.")
    print("   📝 It's highly recommended to use a virtual environment for AI/ML projects.")
    
    show_environment_comparison()
    
    response = input("\nWould you like to create a virtual environment now? (y/n): ").strip().lower()
    
    if response != 'y':
        print("\n⏭️  Skipping virtual environment setup.")
        print("   You can create one manually later when ready.")
        REPORT_DATA["virtual_environment_setup"] = venv_setup_data
        return
    
    print("\n  Which tool would you like to use?")
    print("  [1] venv - Simple, built-in (lightweight, no CUDA handling)")
    print("  [2] conda - Best for GPU/ML workloads (handles CUDA)")
    print("  [3] micromamba - Fast conda alternative (recommended for GPU work)")
    print("  [4] uv - Modern, fast (great for pure Python, limited CUDA)")
    print("  [5] None - Skip installation for now")
    
    while True:
        choice = input("\nEnter your choice (1-5): ").strip()
        if choice in ['1', '2', '3', '4', '5']:
            break
        print("  Invalid choice. Please enter 1, 2, 3, 4, or 5.")
    
    tool_map = {'1': 'venv', '2': 'conda', '3': 'micromamba', '4': 'uv', '5': 'none'}
    tool = tool_map[choice]
    
    if tool == 'none':
        print("\n⏭️  Skipping virtual environment setup.")
        REPORT_DATA["virtual_environment_setup"] = venv_setup_data
        return
    
    env_name = input(f"\nEnter environment name (default: ai_env): ").strip()
    if not env_name:
        env_name = "ai_env"
    
    activate_cmd, pip_cmd, python_cmd = create_environment_with_tool(tool, env_name, installed_list)
    
    if activate_cmd is None:
        REPORT_DATA["virtual_environment_setup"] = venv_setup_data
        return
    
    venv_setup_data["created"] = True
    venv_setup_data["tool_used"] = tool
    venv_setup_data["env_name"] = env_name
    
    print(f"\n  📝 To activate the virtual environment:")
    print(f"     {activate_cmd}")
    
    install_packages = input("\n📦 Install AI/ML packages in the new environment? (y/n): ").strip().lower()
    
    if install_packages == 'y':
        print("\n📥 Installing packages...")
        
        packages = []
        
        if tool in ['conda', 'micromamba']:
            packages.append('pytorch')
            packages.append('torchvision')
            packages.append('torchaudio')
            packages.append('pytorch-cuda=12.1')
            packages.append('-c')
            packages.append('pytorch')
            packages.append('-c')
            packages.append('nvidia')
        else:
            packages.append('torch')
            packages.append('torchvision')
            packages.append('torchaudio')
            packages.append('--index-url')
            packages.append('https://download.pytorch.org/whl/cu121')
        
        for pkg in missing_list:
            if pkg != 'torch':
                packages.append(pkg)
        
        recommended_pkgs = ['transformers', 'accelerate', 'xformers', 'numpy', 'pandas', 'matplotlib', 'seaborn']
        for pkg in recommended_pkgs:
            if pkg not in installed_list and pkg not in packages:
                packages.append(pkg)
        
        if packages:
            print(f"\n  Installing: {' '.join(packages)}")
            
            try:
                if tool in ['conda', 'micromamba']:
                    if tool == 'conda':
                        install_cmd = ['conda', 'install'] + packages + ['-y']
                    else:
                        install_cmd = ['micromamba', 'install'] + packages + ['-y']
                    subprocess.run(install_cmd, check=True)
                else:
                    if pip_cmd:
                        install_cmd = [pip_cmd] + packages
                        subprocess.run(install_cmd, shell=True, check=True)
                    else:
                        subprocess.run([sys.executable, '-m', 'pip', 'install'] + packages, check=True)
                
                print("  ✅ Packages installed successfully!")
                venv_setup_data["packages_installed"] = True
                
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Failed to install packages: {e}")
                print("  ℹ️  Try installing manually after activating the environment")
    
    REPORT_DATA["virtual_environment_setup"] = venv_setup_data
    
    print("\n" + "="*70)
    print("✅ Virtual environment setup complete!")
    print("="*70)

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Run all system checks"""
    print("="*70)
    print("🔍 COMPREHENSIVE SYSTEM SCAN - AI WORKLOAD READINESS")
    print("="*70)
    print(f"Started: {SCAN_START_STR}")
    print(f"OS Detected: {OS_TYPE}")
    print(f"Platform: {'Windows' if IS_WINDOWS else 'Linux' if IS_LINUX else 'macOS' if IS_MACOS else 'Unknown'}")
    if IS_JETSON:
        print("🔹 NVIDIA Jetson Nano Detected")
    print("="*70)
    
    print_table_header()
    
    get_system_info()           # Step 1
    get_cpu_info()              # Step 2
    get_bios_info()             # Step 3
    get_memory_info()           # Step 4
    get_storage_info()          # Step 5
    get_network_info()          # Step 6
    check_pytorch()             # Step 7
    get_gpu_info()              # Steps 8-10
    gpu_performance_test()      # Step 11
    gpu_memory_test()           # Step 12
    get_nvidia_info()           # Step 13
    in_venv, installed_list, missing_list = get_software_info()  # Step 14
    cpu_stress_test()           # Step 15
    gpu_stress_test()           # Step 16
    storage_speed_test()        # Step 17
    network_speed_test()        # Step 18
    power_supply_test()         # Step 19
    system_summary()            # Step 20
    
    # Virtual Environment Setup Wizard
    virtual_environment_setup_wizard(in_venv, installed_list, missing_list)
    
    # Save JSON report after virtual environment setup
    save_json_report()
    
    print("\n" + "="*70)
    print("✅ System scan completed successfully!")
    print("="*70)

if __name__ == "__main__":
    main()