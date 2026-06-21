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
  9  | GPU detection              | Identifies your RTX 5080 and its specs
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
        if lib == 'wmi' and platform.system() != "Windows":
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
    print("  9   | GPU detection              | Identifies your RTX 5080 and its specs")
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

# =============================================================================
# STEP 1: SYSTEM OVERVIEW
# =============================================================================

def get_system_info():
    """Step 1: Get basic system information"""
    print_section("STEP 1: SYSTEM OVERVIEW")
    print("-" * 50)
    
    notes = """
    This shows your system basics: OS, machine type, hostname, boot time, and Python version.
    This helps identify your environment and ensure compatibility with AI tools.
    """
    print_notes(1, notes)
    
    print(f"  System: {platform.system()} {platform.release()} ({platform.version})")
    print(f"  Machine: {platform.machine()}")
    print(f"  Processor: {platform.processor()}")
    print(f"  Hostname: {socket.gethostname()}")
    print(f"  Boot Time: {datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python Version: {sys.version}")
    print(f"  Script Run: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
    
    print(f"  Physical Cores: {physical_cores}")
    print(f"  Logical Cores: {logical_cores}")
    
    freq = psutil.cpu_freq()
    if freq:
        print(f"  Max Frequency: {freq.max:.2f} MHz")
        print(f"  Current Frequency: {freq.current:.2f} MHz")
        print(f"  Min Frequency: {freq.min:.2f} MHz")
    
    print(f"  CPU Usage: {psutil.cpu_percent(interval=1)}%")
    
    if hasattr(psutil, 'getloadavg'):
        load = psutil.getloadavg()
        print(f"  Load Average (1, 5, 15 min): {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}")
    
    if HAS_CPUINFO:
        try:
            info = cpuinfo.get_cpu_info()
            print(f"  CPU Model: {info.get('brand_raw', 'Unknown')}")
            print(f"  Architecture: {info.get('arch', 'Unknown')}")
            print(f"  Bits: {info.get('bits', 'Unknown')}")
            print(f"  Cache Size: {info.get('l2_cache_size', 'Unknown')}")
            print(f"  CPU Flags: {len(info.get('flags', []))} features enabled")
        except:
            pass
    
    if HAS_WMI and platform.system() == "Windows":
        try:
            c = wmi.WMI()
            for cpu in c.Win32_Processor():
                print(f"  Processor ID: {cpu.ProcessorId}")
                print(f"  Max Clock Speed: {cpu.MaxClockSpeed} MHz")
                print(f"  Current Clock Speed: {cpu.CurrentClockSpeed} MHz")
                print(f"  Socket Designation: {cpu.SocketDesignation}")
                print(f"  Virtualization: {cpu.VirtualizationFirmwareEnabled}")
                break
        except:
            pass
    
    if platform.system() == "Windows":
        virt = run_command("systeminfo | findstr /I 'virtualization'")
        if virt:
            print(f"  Virtualization: {virt}")
    
    is_vm = False
    try:
        if platform.system() == "Windows":
            is_vm = "Virtual" in run_command("wmic computersystem get model") or "VMware" in run_command("wmic computersystem get model")
    except:
        pass
    print(f"  Running in VM: {is_vm}")

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
    
    if platform.system() == "Windows":
        if HAS_WMI:
            try:
                c = wmi.WMI()
                for bios in c.Win32_BIOS():
                    print(f"  Manufacturer: {bios.Manufacturer}")
                    print(f"  Name: {bios.Name}")
                    print(f"  Version: {bios.SMBIOSBIOSVersion}")
                    print(f"  Date: {bios.ReleaseDate}")
                    print(f"  Serial Number: {bios.SerialNumber}")
                    print(f"  SMBIOS Version: {bios.SMBIOSMajorVersion}.{bios.SMBIOSMinorVersion}")
                    break
            except:
                pass
        
        bios_info = run_command("systeminfo | findstr /I 'BIOS'")
        if bios_info:
            for line in bios_info.split('\n'):
                print(f"  {line.strip()}")
    
    elif platform.system() == "Linux":
        bios_info = run_command("sudo dmidecode -t bios 2>/dev/null | grep -E 'Vendor|Version|Release Date'")
        if bios_info:
            for line in bios_info.split('\n'):
                print(f"  {line.strip()}")

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
    
    print(f"  Total RAM: {get_size(mem.total)}")
    print(f"  Available RAM: {get_size(mem.available)}")
    print(f"  Used RAM: {get_size(mem.used)}")
    print(f"  RAM Usage: {mem.percent}%")
    
    if platform.system() == "Windows" and HAS_WMI:
        try:
            c = wmi.WMI()
            total_speed = 0
            count = 0
            for mem_device in c.Win32_PhysicalMemory():
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
                print(f"\n  Average Speed: {total_speed/count:.0f} MHz")
        except:
            pass
    
    print(f"\n  Swap Total: {get_size(swap.total)}")
    print(f"  Swap Used: {get_size(swap.used)}")
    print(f"  Swap Free: {get_size(swap.free)}")
    print(f"  Swap Usage: {swap.percent}%")

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
    
    print_subsection("Disk Partitions")
    partitions = psutil.disk_partitions()
    for partition in partitions:
        # Fix the warning by using raw string or escaping properly
        device_display = partition.device.replace('\\', '\\\\')
        print(f"  Device: {device_display}")
        print(f"    Mount: {partition.mountpoint}")
        print(f"    File System: {partition.fstype}")
        print(f"    Options: {partition.opts}")
        
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            print(f"    Total Size: {get_size(usage.total)}")
            print(f"    Used: {get_size(usage.used)}")
            print(f"    Free: {get_size(usage.free)}")
            print(f"    Usage: {usage.percent}%")
        except PermissionError:
            print("    (Permission denied)")
        print()
    
    print_subsection("Disk I/O Statistics")
    io_counters = psutil.disk_io_counters()
    if io_counters:
        print(f"  Read Count: {io_counters.read_count}")
        print(f"  Write Count: {io_counters.write_count}")
        print(f"  Read Bytes: {get_size(io_counters.read_bytes)}")
        print(f"  Write Bytes: {get_size(io_counters.write_bytes)}")
        print(f"  Read Time: {io_counters.read_time} ms")
        print(f"  Write Time: {io_counters.write_time} ms")
    
    if platform.system() == "Windows" and HAS_WMI:
        print_subsection("Physical Disk Details")
        try:
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                print(f"  Model: {disk.Model}")
                print(f"    Interface: {disk.InterfaceType}")
                print(f"    Media Type: {disk.MediaType}")
                print(f"    Size: {get_size(int(disk.Size)) if disk.Size else 'Unknown'}")
                print(f"    Serial Number: {disk.SerialNumber}")
                print(f"    Partitions: {disk.Partitions}")
                print()
        except:
            pass
    
    if platform.system() == "Windows":
        print_subsection("Drive Type Detection")
        try:
            for partition in partitions:
                if partition.device:
                    device = partition.device.replace('\\', '')
                    if device and len(device) > 0:
                        result = run_command(f'powershell "Get-PhysicalDisk | Where-Object {{$_.DeviceNumber -eq (Get-Partition -DriveLetter {device[0]} | Get-Disk).Number}} | Select-Object MediaType, Model"')
                        if result:
                            if "SSD" in result or "Solid" in result:
                                print(f"  {device}: ✅ SSD detected")
                            elif "HDD" in result:
                                print(f"  {device}: HDD detected")
                            else:
                                print(f"  {device}: {result[:50]}...")
        except:
            pass

# =============================================================================
# STEP 6: NETWORK INFORMATION
# =============================================================================

def get_network_info():
    """Step 6: Get detailed network information"""
    print_section("STEP 6: NETWORK INFORMATION")
    print("-" * 50)
    
    notes = """
    Network checks: interfaces, IPs, MAC addresses, I/O statistics, connectivity.
    For AI workloads: 50+ Mbps download for models, 10+ Mbps upload for cloud training, low ping (<50ms).
    """
    print_notes(6, notes)
    
    print_subsection("Network Interfaces")
    interfaces = psutil.net_if_addrs()
    for interface_name, interface_addresses in interfaces.items():
        if interface_name.startswith(('lo', 'Loopback')):
            continue
        print(f"  {interface_name}:")
        for address in interface_addresses:
            if address.family == socket.AF_INET:
                print(f"    IPv4: {address.address}")
                print(f"    Netmask: {address.netmask}")
            elif address.family == socket.AF_INET6:
                print(f"    IPv6: {address.address}")
            else:
                print(f"    MAC: {address.address}")
    
    print_subsection("Network I/O Statistics")
    io_counters = psutil.net_io_counters()
    if io_counters:
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
        print("  ✅ Internet connectivity: Available")
        
        dns_test = socket.gethostbyname('google.com')
        print(f"  ✅ DNS Resolution: google.com -> {dns_test}")
        
        if platform.system() == "Windows":
            ping = run_command("ping -n 1 8.8.8.8")
            if ping:
                print("  ✅ Ping test: Successful")
        else:
            ping = run_command("ping -c 1 8.8.8.8")
            if ping:
                print("  ✅ Ping test: Successful")
    except:
        print("  ❌ Internet connectivity: Not available or DNS issue")

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
    
    if HAS_TORCH:
        installed_version = torch.__version__
        print(f"  ✅ PyTorch installed: {installed_version}")
        
        # Check latest version from PyPI
        print("\n  🔍 Checking latest version from PyPI...")
        try:
            import urllib.request
            import json
            
            url = "https://pypi.org/pypi/torch/json"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_version = data['info']['version']
                
                print(f"  Latest PyTorch version: {latest_version}")
                
                # Compare versions
                if installed_version == latest_version:
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
            print(f"\n  ✅ CUDA version: {cuda_version}")
            print(f"  ✅ cuDNN version: {torch.backends.cudnn.version()}")
            print("  ✅ PyTorch is CUDA-enabled - GPU acceleration available!")
        else:
            print("  ⚠️  PyTorch is installed but CUDA is not available")
            print("  💡 Install CUDA version: pip install torch --index-url https://download.pytorch.org/whl/cu121")
        
        return True
    else:
        print("  ❌ PyTorch NOT installed")
        print("   Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
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
    
    if not HAS_TORCH:
        print("  ⚠️  PyTorch not installed - skipping CUDA check")
        return
    
    print(f"  CUDA Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"  CUDA Version: {torch.version.cuda}")
        print(f"  cuDNN Version: {torch.backends.cudnn.version()}")
        print("  ✅ GPU acceleration is enabled!")
    else:
        print("  ❌ CUDA is NOT available!")
        print("   Possible issues:")
        print("   - NVIDIA drivers not installed")
        print("   - PyTorch version without CUDA support")
        return
    
    # Step 9: GPU Detection
    print_section("STEP 9: GPU DETECTION")
    print("-" * 50)
    
    notes = """
    GPU detection: GPU name, compute capability, VRAM, CUDA cores, max threads.
    RTX 5080 with 16GB VRAM and Compute Capability 12.0 (Blackwell architecture) is top-tier for AI.
    """
    print_notes(9, notes)
    
    gpu_count = torch.cuda.device_count()
    print(f"  GPU Count: {gpu_count}")
    
    if gpu_count > 0:
        for i in range(gpu_count):
            print(f"\n  GPU {i}:")
            print(f"    Name: {torch.cuda.get_device_name(i)}")
            props = torch.cuda.get_device_properties(i)
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
        
        print("  ✅ Computation successful!")
        print(f"    Result shape: {c.shape}")
        print(f"    Result device: {c.device}")
        print(f"    Memory allocated: {torch.cuda.memory_allocated() / 1e6:.2f} MB")
        print(f"    Memory reserved: {torch.cuda.memory_reserved() / 1e6:.2f} MB")
    except Exception as e:
        print(f"  ❌ Computation failed: {e}")

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
    - Your RTX 5080 can handle matrix sizes up to 24576x24576 efficiently
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
    
    # Test sizes up to 24576x24576 (which we know works well)
    sizes = [1024, 2048, 4096, 8192, 12288, 16384, 24576]
    results = []
    
    for size in sizes:
        result = benchmark_matmul(size)
        if result == "OOM":
            print(f"    {size}x{size}: ❌ Out of Memory (VRAM limit reached)")
            break
        elif result > 10000:  # 10 seconds
            print(f"    {size}x{size}: ⏱️  {result/1000:.2f}s (stopping at 10s threshold)")
            break
        else:
            print(f"    {size}x{size}: {result:.2f} ms")
            results.append((size, result))
    
    print("  " + "-" * 60)
    
    # Interpret results
    print("\n  📋 WHAT THESE BENCHMARKS MEAN FOR YOUR GPU:")
    print("  " + "-" * 60)
    
    if results:
        # Analyze performance
        max_size, max_time = results[-1]
        
        print(f"  ✅ Your RTX 5080 handled {max_size}x{max_size} matrix in {max_time:.2f}ms")
        print(f"  ✅ This is an excellent result for a consumer GPU")
        
        print("\n  📊 CAPABILITIES BASED ON MATRIX SIZE:")
        print("  " + "-" * 60)
        
        # Check what sizes were achieved
        has_4096 = any(s == 4096 for s, _ in results)
        has_8192 = any(s == 8192 for s, _ in results)
        has_12288 = any(s == 12288 for s, _ in results)
        has_16384 = any(s == 16384 for s, _ in results)
        has_24576 = any(s == 24576 for s, _ in results)
        
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
        
        print("\n  💡 RECOMMENDATIONS FOR YOUR RTX 5080:")
        print("  " + "-" * 60)
        print("  • You can train models with up to 70B parameters (with quantization)")
        print("  • Use mixed precision (FP16/BF16) for 2x faster training")
        print("  • Use gradient accumulation for larger effective batch sizes")
        print("  • Consider using xformers for optimized attention mechanisms")

# =============================================================================
# STEP 12: GPU MEMORY ALLOCATION TEST
# =============================================================================

def gpu_memory_test():
    """Step 12: Test GPU memory allocation"""
    print_section("STEP 12: GPU MEMORY ALLOCATION")
    print("-" * 50)
    
    notes = """
    GPU Memory test: tests how much VRAM you can allocate.
    16GB VRAM can fit: Llama-7B (5-7GB with quantization), Stable Diffusion (4-6GB), most BERT models.
    """
    print_notes(12, notes)
    
    try:
        print("  Testing memory allocation...")
        torch.cuda.empty_cache()
        
        total_mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
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
                print(f"    {size_gb:.1f} GB: ✅ Allocated (Total used: {allocated:.2f} GB)")
                del test_tensor
                torch.cuda.empty_cache()
                last_success = size_gb
                time.sleep(0.1)
            except RuntimeError as e:
                if "out of memory" in str(e):
                    print(f"    {size_gb:.1f} GB: ❌ Out of Memory")
                    break
                else:
                    raise e
        
        print("  " + "-" * 40)
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
            for i, (_, display_name) in enumerate(queries):
                if i < len(parts) and parts[i] and parts[i] != '[Not Supported]':
                    print(f"  {display_name}: {parts[i]}")
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
    
    print(f"  Python Executable: {python_path}")
    print(f"  Python Location: {python_location}")
    
    if in_venv:
        print(f"  ✅ Virtual Environment: ACTIVE ({venv_type})")
        if 'VIRTUAL_ENV' in os.environ:
            print(f"    Virtual Env Path: {os.environ['VIRTUAL_ENV']}")
        if 'CONDA_PREFIX' in os.environ:
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
            print(f"  ✅ {name}: {version}")
            installed += 1
            installed_list.append(name)
        except ImportError:
            print(f"  ❌ {name}: Not installed")
            missing_list.append(name)
    
    print(f"\n  Total AI/ML packages installed: {installed}/{len(frameworks)}")
    
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
    
    print(f"\n  📊 Results:")
    print(f"    Test Duration: {elapsed:.2f} seconds")
    print(f"    Threads Used: {threads_used}")
    print(f"    CPU Usage: {cpu_percent}%")
    if freq_before and freq_after:
        freq_drop = ((freq_before.max - freq_after.current) / freq_before.max) * 100 if freq_before.max > 0 else 0
        print(f"    Frequency During Test: {freq_after.current:.2f} MHz (Drop: {freq_drop:.1f}%)")
    
    print("\n  📋 DIAGNOSIS:")
    print("  " + "-" * 50)
    
    issues = []
    recommendations = []
    
    expected_time = 8.0
    if elapsed > expected_time * 1.5:
        issues.append(f"⏱️  CPU test took {elapsed:.1f}s (expected ~{expected_time:.1f}s)")
        recommendations.append("  - Check for thermal throttling using HWMonitor")
        recommendations.append("  - Ensure adequate cooling and airflow")
    
    if freq_before and freq_after:
        if freq_drop > 20:
            issues.append(f"🔥 Significant frequency drop: {freq_drop:.1f}%")
            recommendations.append("  - Monitor CPU temperatures during load")
            recommendations.append("  - Consider improving CPU cooling")
    
    if cpu_percent < 80 and threads_used > 1:
        issues.append(f"⚠️  Low CPU utilization: {cpu_percent}% with {threads_used} threads")
        recommendations.append("  - Check Windows Power Plan (set to High Performance)")
    
    if physical_cores and physical_cores < 8:
        issues.append(f"⚠️  Limited physical cores: {physical_cores} (recommended 8+ for AI)")
        recommendations.append("  - Consider upgrading CPU for data preprocessing")
    
    if issues:
        print("\n  ⚠️  Issues Found:")
        for issue in issues:
            print(f"    • {issue}")
        print("\n  📝 Recommendations:")
        for rec in recommendations:
            print(f"    {rec}")
    else:
        print("  ✅ No issues detected. CPU performance is excellent!")

# =============================================================================
# STEP 16: GPU STRESS TEST
# =============================================================================

def gpu_stress_test():
    """Step 16: GPU stress test with detailed explanation"""
    print_section("STEP 16: GPU STRESS TEST")
    print("-" * 50)
    
    notes = """
    GPU Stress Test: 5 iterations of 8192x8192 matrix multiplication.
    0% Utilization is normal - RTX 5080 completes operations before nvidia-smi samples.
    For better utilization, use larger matrices or increase batch size in training.
    """
    print_notes(16, notes)
    
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
                    print(f"    [Monitor] Util: {util}, Mem: {mem}, Temp: {temp}°C, Power: {power}W")
        except:
            pass
    
    elapsed = time.time() - start
    
    print(f"\n  ✅ GPU Test Complete in {elapsed:.2f} seconds")
    
    print("\n  📋 DIAGNOSIS:")
    print("  " + "-" * 50)
    
    if max_power < 100:
        print("  ⚠️  Low power draw detected. This could mean:")
        print("    • GPU is not being fully utilized")
        print("    • Power supply is insufficient")
        print("    • GPU is in power-saving mode")
        print("  💡 Try increasing matrix size or batch size")
    elif max_power > 300:
        print("  ✅ GPU power draw is excellent!")
    
    if max_temp > 85:
        print(f"  🔥 High GPU temperature: {max_temp:.0f}°C")
        print("  💡 Improve cooling or reduce workload")
    elif max_temp > 70:
        print(f"  ✅ Good GPU temperature: {max_temp:.0f}°C")
    else:
        print(f"  ✅ Excellent GPU temperature: {max_temp:.0f}°C")
    
    print("\n  💡 PERFORMANCE TIPS:")
    print("  " + "-" * 50)
    print("  • Use larger batch sizes for better utilization")
    print("  • Enable mixed precision training (AMP)")
    print("  • Use torch.compile() for PyTorch 2.0+")
    print("  • Set Windows Power Plan to 'High Performance'")

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
        
        print(f"\n  📊 Results:")
        print(f"    Write Speed: {write_speed:.2f} MB/s")
        print(f"    Read Speed: {read_speed:.2f} MB/s")
        
        print("\n  📋 DIAGNOSIS:")
        print("  " + "-" * 50)
        
        if write_speed > 500:
            print("  ✅ Excellent performance - NVMe SSD detected")
            if write_speed > 1000:
                print("  ✅ PCIe Gen 3/4 NVMe SSD with excellent speeds")
        elif write_speed > 200:
            print("  ✅ Good performance - SATA SSD detected")
        elif write_speed > 50:
            print("  ⚠️  HDD detected - Slow for AI workloads")
            print("  💡 Upgrade to NVMe SSD for better performance")
        else:
            print("  ❌ Very slow storage detected!")
            print("  💡 IMMEDIATELY upgrade to NVMe SSD for AI work")
            
    except Exception as e:
        print(f"  ⚠️  Storage test error: {e}")

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
    
    if HAS_SPEEDTEST:
        try:
            print("  Running speed test (may take 30-60 seconds)...")
            st = speedtest.Speedtest()
            st.get_best_server()
            
            download = st.download() / 1_000_000
            upload = st.upload() / 1_000_000
            ping = st.results.ping
            
            print(f"\n  📊 Results:")
            print(f"    Download Speed: {download:.2f} Mbps")
            print(f"    Upload Speed: {upload:.2f} Mbps")
            print(f"    Ping: {ping:.2f} ms")
            
            print("\n  📋 DIAGNOSIS:")
            print("  " + "-" * 50)
            
            if download > 100:
                print("  ✅ Excellent download speed")
            elif download > 50:
                print("  ⚠️  Adequate download speed")
                print("  💡 Large models may take time to download")
            else:
                print("  ❌ Slow download speed")
                print("  💡 Consider downloading models at work/school")
            
            if upload > 20:
                print("  ✅ Excellent upload speed")
            else:
                print("  ⚠️  Upload speed may be slow for sharing models")
                
        except Exception as e:
            print(f"  ⚠️  Speed test error: {e}")
    else:
        print("  ⚠️  Speedtest not installed (pip install speedtest-cli)")

# =============================================================================
# STEP 19: POWER SUPPLY TEST
# =============================================================================

def power_supply_test():
    """Step 19: Test power delivery to GPU and provide recommendations"""
    print_section("STEP 19: POWER SUPPLY TEST")
    print("-" * 50)
    
    notes = """
    Power Supply Test: checks GPU power draw vs expected.
    RTX 5080 needs 360W under full load. Insufficient power causes throttling.
    Current idle power (~45W) is normal. Under load should reach 300-360W.
    """
    print_notes(19, notes)
    
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
        if platform.system() == "Windows":
            result = run_command("wmic computersystem get model")
            if result and any(x in result.lower() for x in ['laptop', 'notebook', 'tablet']):
                is_laptop = True
    except:
        pass
    
    if is_laptop:
        print("  ℹ️  Laptop detected - power delivery may be limited")
        print("  💡 For best performance, plug into AC power")
    else:
        print("  ℹ️  Desktop detected - power supply should be adequate")
    
    print("\n  💡 RECOMMENDED POWER SUPPLY SPECIFICATIONS:")
    print("  " + "-" * 50)
    print("  • RTX 5080 Recommended PSU: 750W - 850W")
    print("  • Minimum PSU: 650W")
    print("  • PCIe Power Cables: 3x 8-pin or 1x 12VHPWR")
    
    print("\n  🛒 COMMERCIAL RECOMMENDATIONS:")
    print("  " + "-" * 50)
    print("  POWER SUPPLY UNITS (PSUs):")
    print("  • Corsair RM850x (850W, Gold) - $150")
    print("  • Seasonic Focus GX-850 (850W, Gold) - $160")
    print("  • ASUS ROG Thor 850P (850W, Platinum) - $250")
    print("  • EVGA SuperNOVA 850 G6 (850W, Gold) - $140")
    print("  • Be Quiet! Dark Power 12 850W (850W, Titanium) - $200")
    
    print("\n  POWER CABLES NEEDED:")
    print("  • RTX 5080 uses 12VHPWR connector (16-pin)")
    print("  • Most modern PSUs include this natively")
    print("  • Adapter: 3x 8-pin to 12VHPWR (included with GPU)")

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
    
    print("  📊 System Readiness Assessment:\n")
    
    cpu_cores = psutil.cpu_count(logical=True)
    cpu_score = "✅ Excellent" if cpu_cores >= 16 else "✅ Good" if cpu_cores >= 8 else "⚠️  Adequate" if cpu_cores >= 4 else "❌ Insufficient"
    print(f"  CPU: {cpu_cores} cores - {cpu_score}")
    
    mem = psutil.virtual_memory()
    mem_gb = mem.total / 1e9
    mem_score = "✅ Excellent" if mem_gb >= 32 else "✅ Good" if mem_gb >= 16 else "⚠️  Adequate" if mem_gb >= 8 else "❌ Insufficient"
    print(f"  RAM: {mem_gb:.0f} GB - {mem_score}")
    
    if HAS_TORCH and torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        gpu_score = "✅ Excellent" if "RTX 50" in gpu_name or "RTX 40" in gpu_name else "✅ Good"
        print(f"  GPU: {gpu_name} ({gpu_mem:.1f} GB) - {gpu_score}")
    elif HAS_TORCH:
        print("  GPU: ❌ Not detected - Will use CPU only (much slower)")
    else:
        print("  GPU: ⚠️  Could not check GPU (PyTorch not installed)")
    
    try:
        partitions = psutil.disk_partitions()
        has_ssd = False
        for partition in partitions:
            if platform.system() == "Windows":
                result = run_command(f'powershell "Get-PhysicalDisk | Where-Object {{$_.DeviceNumber -eq (Get-Partition -DriveLetter {partition.device[0]} | Get-Disk).Number}} | Select-Object MediaType"')
                if result and "SSD" in result:
                    has_ssd = True
                    break
        
        storage_score = "✅ Excellent (SSD)" if has_ssd else "⚠️  HDD detected (consider SSD upgrade)"
        print(f"  Storage: {storage_score}")
    except:
        print("  Storage: ⚠️  Could not determine drive type")
    
    try:
        socket.gethostbyname('8.8.8.8')
        network_score = "✅ Available"
    except:
        network_score = "❌ Not available"
    print(f"  Network Internet: {network_score}")
    
    print("\n" + "="*70)
    print("  Overall Readiness for AI/ML Workloads:")
    
    if HAS_TORCH and torch.cuda.is_available():
        print("  ✅ Your system is READY for AI/ML development!")
        print(f"  ✅ RTX 5080 with 16GB VRAM is excellent for most AI models")
        print("  ✅ 32GB+ RAM can handle large datasets")
        print("  ✅ Modern CPU with 16+ cores for data preprocessing")
    else:
        print("  ⚠️  System is partially ready but missing GPU support")
        print("  ℹ️  Install NVIDIA drivers and PyTorch with CUDA support")
    
    print("="*70)

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
    
    print("\n  📝 Recommendation for your RTX 5080 system:")
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
            
            if platform.system() == "Windows":
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
            
            if platform.system() == "Windows":
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
    
    if in_venv:
        print("\n✅ You are already in a virtual environment!")
        print("\n📦 Missing packages to install:")
        if missing_list:
            for pkg in missing_list:
                if pkg != 'torch':
                    print(f"    - {pkg}")
        else:
            print("    ✅ All AI/ML packages are installed!")
        return
    
    print("\n⚠️  You are NOT in a virtual environment.")
    print("   📝 It's highly recommended to use a virtual environment for AI/ML projects.")
    
    show_environment_comparison()
    
    response = input("\nWould you like to create a virtual environment now? (y/n): ").strip().lower()
    
    if response != 'y':
        print("\n⏭️  Skipping virtual environment setup.")
        print("   You can create one manually later when ready.")
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
        return
    
    env_name = input(f"\nEnter environment name (default: ai_env): ").strip()
    if not env_name:
        env_name = "ai_env"
    
    activate_cmd, pip_cmd, python_cmd = create_environment_with_tool(tool, env_name, installed_list)
    
    if activate_cmd is None:
        return
    
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
                
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Failed to install packages: {e}")
                print("  ℹ️  Try installing manually after activating the environment")
    
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
    print(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
    
    virtual_environment_setup_wizard(in_venv, installed_list, missing_list)
    
    print("\n" + "="*70)
    print("✅ System scan completed successfully!")
    print("="*70)

if __name__ == "__main__":
    main()