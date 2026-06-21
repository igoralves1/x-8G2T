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
 19  | System Summary             | Provides overall readiness assessment
================================================================================
"""

import sys
import subprocess
import importlib
import os
import platform

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
                                print(f"    PID: {parts[0]}")
                                print(f"    Process: {parts[1]}")
                                print(f"    Used Memory: {parts[2]}")
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
    print(" 19   | System Summary             | Provides overall readiness assessment")
    print("="*70)

# =============================================================================
# STEP 1: SYSTEM OVERVIEW
# =============================================================================

def get_system_info():
    """Step 1: Get basic system information"""
    print_section("STEP 1: SYSTEM OVERVIEW")
    print("Why it matters: Identifies OS, hostname, boot time")
    print("-" * 50)
    
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
    print("Why it matters: AI training needs multi-core performance")
    print("-" * 50)
    
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
    print("Why it matters: Firmware compatibility for hardware")
    print("-" * 50)
    
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
    print("Why it matters: Large models need lots of memory")
    print("-" * 50)
    
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
    print("Why it matters: Fast storage for datasets/checkpoints")
    print("-" * 50)
    
    print_subsection("Disk Partitions")
    partitions = psutil.disk_partitions()
    for partition in partitions:
        print(f"  Device: {partition.device}")
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
    print("Why it matters: For cloud/remote training")
    print("-" * 50)
    
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
# STEP 7: PYTORCH INSTALLATION
# =============================================================================

def check_pytorch():
    """Step 7: Check if PyTorch is installed"""
    print_section("STEP 7: PYTORCH INSTALLATION")
    print("Why it matters: Ensures the AI framework is installed")
    print("-" * 50)
    
    if HAS_TORCH:
        print(f"  ✅ PyTorch installed: {torch.__version__}")
        return True
    else:
        print("  ❌ PyTorch NOT installed")
        print("   Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        return False

# =============================================================================
# STEPS 8-13: GPU INFORMATION (Comprehensive)
# =============================================================================

def get_gpu_info():
    """Steps 8-13: Comprehensive GPU information"""
    
    # Step 8: Check CUDA availability
    print_section("STEP 8: CUDA AVAILABILITY")
    print("Why it matters: Confirms GPU drivers work with PyTorch")
    print("-" * 50)
    
    if not HAS_TORCH:
        print("  ⚠️  PyTorch not installed - skipping CUDA check")
        return
    
    print(f"  CUDA Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"  CUDA Version: {torch.version.cuda}")
        print(f"  cuDNN Version: {torch.backends.cudnn.version()}")
    else:
        print("  ❌ CUDA is NOT available!")
        print("   Possible issues:")
        print("   - NVIDIA drivers not installed")
        print("   - PyTorch version without CUDA support")
        return
    
    # Step 9: GPU Detection
    print_section("STEP 9: GPU DETECTION")
    print("Why it matters: Identifies your RTX 5080 and its specs")
    print("-" * 50)
    
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
    print("Why it matters: Verifies the GPU can do math correctly")
    print("-" * 50)
    
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
    
    # Step 11: GPU Performance Test
    print_section("STEP 11: GPU PERFORMANCE")
    print("Why it matters: Benchmarks your GPU's speed")
    print("-" * 50)
    
    def benchmark_matmul(size, repeats=10):
        a = torch.randn(size, size, device='cuda')
        b = torch.randn(size, size, device='cuda')
        
        for _ in range(3):
            torch.matmul(a, b)
        torch.cuda.synchronize()
        
        start = time.perf_counter()
        for _ in range(repeats):
            torch.matmul(a, b)
        torch.cuda.synchronize()
        elapsed = (time.perf_counter() - start) / repeats * 1000
        
        return elapsed
    
    print("  Matrix Multiplication Benchmark (10 iterations):")
    print("  " + "-" * 40)
    for size in [1024, 2048, 4096]:
        ms = benchmark_matmul(size)
        print(f"    {size}x{size}: {ms:.2f} ms")
    print("  " + "-" * 40)
    
    # Step 12: GPU Memory Test
    print_section("STEP 12: GPU MEMORY ALLOCATION")
    print("Why it matters: Tests VRAM allocation and limits")
    print("-" * 50)
    
    try:
        print("  Testing memory allocation...")
        torch.cuda.empty_cache()
        
        test_size_mb = 100
        for i in range(3):
            size = test_size_mb * (i + 1)
            elements = int(size * 1e6 / 4)
            
            try:
                test_tensor = torch.randn(elements, device='cuda')
                allocated = torch.cuda.memory_allocated() / 1e9
                print(f"    ✅ Allocated {size}MB (Total used: {allocated:.2f} GB)")
                del test_tensor
                torch.cuda.empty_cache()
            except RuntimeError as e:
                if "out of memory" in str(e):
                    print(f"    ⚠️  {size}MB allocation failed (OOM)")
                    break
                else:
                    raise e
    except Exception as e:
        print(f"  ⚠️  Memory test warning: {e}")
    
    # Step 13: NVIDIA Driver Info - Enhanced with FULL nvidia-smi
    print_section("STEP 13: NVIDIA DRIVER INFO (FULL nvidia-smi)")
    print("Why it matters: Shows NVIDIA driver details")
    print("-" * 50)
    
    # FULL nvidia-smi output - NO TRUNCATION
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            print("  FULL nvidia-smi output:")
            print("=" * 80)
            print(result.stdout)  # Full output - no truncation
            print("=" * 80)
        else:
            print("  ⚠️  nvidia-smi returned an error")
    except Exception as e:
        print(f"  ⚠️  Could not run nvidia-smi: {e}")
    
    # Query specific GPU details
    print_subsection("Detailed GPU Query (nvidia-smi --query)")
    try:
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
            capture_output=True, text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = [p.strip() for p in result.stdout.strip().split(',')]
            for i, (_, display_name) in enumerate(queries):
                if i < len(parts) and parts[i]:
                    print(f"  {display_name}: {parts[i]}")
        else:
            print("  ⚠️  Could not query GPU details")
    except Exception as e:
        print(f"  ⚠️  Error querying GPU: {e}")
    
    # GPU Processes
    print_subsection("GPU Processes")
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print("  Current GPU processes:")
            print("-" * 50)
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 3:
                        print(f"    PID: {parts[0]}")
                        print(f"    Process: {parts[1]}")
                        print(f"    Used Memory: {parts[2]}")
                        print("-" * 30)
        else:
            print("  No GPU processes running")
    except Exception as e:
        print(f"  ⚠️  Could not query GPU processes: {e}")

# =============================================================================
# STEP 14: AI/ML SOFTWARE & VIRTUAL ENVIRONMENT
# =============================================================================

def get_software_info():
    """Step 14: Check installed software, versions, and virtual environment"""
    print_section("STEP 14: AI/ML SOFTWARE & VIRTUAL ENVIRONMENT")
    print("Why it matters: Checks installed frameworks, tools, and environment")
    print("-" * 50)
    
    # ======================================================================
    # VIRTUAL ENVIRONMENT CHECK
    # ======================================================================
    print_subsection("Python Environment Check")
    
    # Check if running in a virtual environment
    in_venv = False
    venv_type = "None"
    
    # Method 1: Check sys.prefix vs sys.base_prefix
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        in_venv = True
        venv_type = "venv"
    
    # Method 2: Check for conda environment
    if 'CONDA_PREFIX' in os.environ:
        in_venv = True
        venv_type = "Conda"
    
    # Method 3: Check for virtualenv
    if hasattr(sys, 'prefix') and 'VIRTUAL_ENV' in os.environ:
        in_venv = True
        venv_type = "virtualenv"
    
    # Get Python location
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
    
    # Check pip location
    try:
        import pip
        print(f"  Pip Location: {pip.__file__}")
    except:
        pass
    
    # ======================================================================
    # AI/ML FRAMEWORKS CHECK
    # ======================================================================
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
# STEP 15: CPU STRESS TEST WITH DIAGNOSIS
# =============================================================================

def cpu_stress_test():
    """Step 15: CPU stress test with diagnosis"""
    print_section("STEP 15: CPU STRESS TEST")
    print("Why it matters: Tests CPU performance under load")
    print("-" * 50)
    
    # Get initial CPU info
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
    
    # Get CPU info after test
    cpu_percent = psutil.cpu_percent(interval=1)
    freq_after = psutil.cpu_freq()
    
    print(f"\n  📊 Results:")
    print(f"    Test Duration: {elapsed:.2f} seconds")
    print(f"    Threads Used: {threads_used}")
    print(f"    CPU Usage: {cpu_percent}%")
    if freq_before and freq_after:
        freq_drop = ((freq_before.max - freq_after.current) / freq_before.max) * 100 if freq_before.max > 0 else 0
        print(f"    Frequency During Test: {freq_after.current:.2f} MHz (Drop: {freq_drop:.1f}%)")
    
    # DIAGNOSIS
    print("\n  📋 DIAGNOSIS:")
    print("  " + "-" * 50)
    
    issues = []
    recommendations = []
    
    # Check performance
    expected_time = 8.0
    if elapsed > expected_time * 1.5:
        issues.append(f"⏱️  CPU test took {elapsed:.1f}s (expected ~{expected_time:.1f}s)")
        recommendations.append("  - Check for thermal throttling using HWMonitor or MSI Afterburner")
        recommendations.append("  - Ensure adequate cooling and airflow")
        recommendations.append("  - Check for background processes consuming CPU")
    
    # Check frequency
    if freq_before and freq_after:
        if freq_drop > 20:
            issues.append(f"🔥 Significant frequency drop: {freq_drop:.1f}%")
            recommendations.append("  - Monitor CPU temperatures during load")
            recommendations.append("  - Consider improving CPU cooling")
            recommendations.append("  - Check BIOS for power limit settings")
    
    # Check CPU usage
    if cpu_percent < 80 and threads_used > 1:
        issues.append(f"⚠️  Low CPU utilization: {cpu_percent}% with {threads_used} threads")
        recommendations.append("  - Check for system power saving settings")
        recommendations.append("  - Ensure Windows Power Plan is set to 'High Performance'")
    
    # Check core count for AI workloads
    if physical_cores and physical_cores < 8:
        issues.append(f"⚠️  Limited physical cores: {physical_cores} (recommended 8+ for AI workloads)")
        recommendations.append("  - Consider upgrading to a CPU with more cores for data preprocessing")
    elif physical_cores and physical_cores >= 16:
        print(f"  ✅ Excellent CPU: {physical_cores} physical cores - ideal for AI workloads")
    
    if freq_before and freq_after:
        if freq_drop > 30:
            issues.append("🔥 Severe thermal throttling detected!")
            recommendations.append("  - Check CPU cooler mounting and thermal paste")
            recommendations.append("  - Ensure case has adequate airflow")
            recommendations.append("  - Consider upgrading CPU cooler")
    
    if issues:
        print("\n  ⚠️  Issues Found:")
        for issue in issues:
            print(f"    • {issue}")
        print("\n  📝 Recommendations:")
        for rec in recommendations:
            print(f"    {rec}")
    else:
        print("  ✅ No issues detected. CPU performance is excellent!")
        if physical_cores and physical_cores >= 16:
            print("  ✅ Your CPU is well-suited for AI/ML workloads with 16+ cores")
    
    print("\n  ⭐ Performance Rating:")
    if physical_cores and physical_cores >= 16 and elapsed < 10:
        print("    🏆 Excellent - Ideal for AI/ML development")
    elif physical_cores and physical_cores >= 8 and elapsed < 15:
        print("    ✅ Good - Capable for most AI/ML workloads")
    elif physical_cores and physical_cores >= 4:
        print("    ⚠️  Adequate - May struggle with large datasets")
    else:
        print("    ❌ Insufficient - Consider upgrading for AI/ML work")

# =============================================================================
# STEP 16: GPU STRESS TEST WITH DIAGNOSIS
# =============================================================================

def gpu_stress_test():
    """Step 16: GPU stress test with diagnosis"""
    print_section("STEP 16: GPU STRESS TEST")
    print("Why it matters: Tests GPU performance under load")
    print("-" * 50)
    
    if not HAS_TORCH:
        print("  ⚠️  GPU stress test skipped (PyTorch not installed)")
        return
    
    if not torch.cuda.is_available():
        print("  ⚠️  GPU stress test skipped (CUDA not available)")
        return
    
    # Get GPU info
    gpu_name = torch.cuda.get_device_name(0)
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"  GPU: {gpu_name}")
    print(f"  VRAM: {gpu_mem:.2f} GB")
    
    # Get initial GPU stats
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
    
    print("\n  Running GPU stress test with monitoring...")
    start = time.time()
    
    # Track metrics
    max_temp = 0
    max_power = 0
    all_temps = []
    
    # Run stress test
    for i in range(5):
        print(f"  Iteration {i+1}/5...")
        a = torch.randn(4096, 4096, device='cuda')
        b = torch.randn(4096, 4096, device='cuda')
        c = torch.matmul(a, b)
        torch.cuda.synchronize()
        
        # Get stats during test
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
    avg_temp = sum(all_temps) / len(all_temps) if all_temps else 0
    
    print(f"\n  ✅ GPU Test Complete in {elapsed:.2f} seconds")
    
    # Final GPU stats
    print("\n  Final GPU Status:")
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw',
             '--format=csv,noheader'],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            stats = [s.strip() for s in result.stdout.strip().split(',')]
            if len(stats) >= 4:
                print(f"    GPU Utilization: {stats[0]}")
                print(f"    Memory Used: {stats[1]}")
                print(f"    Temperature: {stats[2]}")
                print(f"    Power Draw: {stats[3]}")
    except:
        pass
    
    torch.cuda.empty_cache()
    
    # DIAGNOSIS
    print("\n  📋 DIAGNOSIS:")
    print("  " + "-" * 50)
    
    issues = []
    recommendations = []
    
    # Check temperature
    if max_temp > 85:
        issues.append(f"🔥 High GPU temperature detected: {max_temp:.0f}°C (recommended < 85°C)")
        recommendations.append("  - Check GPU fan speed and cooling")
        recommendations.append("  - Ensure case has adequate airflow")
        recommendations.append("  - Consider adjusting fan curve in MSI Afterburner")
    elif max_temp > 80:
        issues.append(f"⚠️  Elevated GPU temperature: {max_temp:.0f}°C (recommended < 85°C)")
        recommendations.append("  - Monitor GPU temperatures during extended workloads")
        recommendations.append("  - Ensure case has good airflow")
    else:
        print(f"  ✅ GPU temperatures are excellent: {max_temp:.0f}°C max, {avg_temp:.0f}°C avg")
    
    # Check power
    if max_power > 300:
        print(f"  ✅ GPU power draw is good: {max_power:.0f}W (near 360W TDP)")
    elif max_power > 200:
        issues.append(f"⚠️  Low GPU power draw: {max_power:.0f}W (expected ~300W under load)")
        recommendations.append("  - Check power supply connections")
        recommendations.append("  - Verify GPU is not power-limited in BIOS")
    else:
        issues.append(f"⚠️  Very low GPU power draw: {max_power:.0f}W (expected ~300W)")
        recommendations.append("  - Check if GPU is throttling due to temperature")
        recommendations.append("  - Verify power supply is adequate")
    
    # Check performance
    expected_time = 3.0
    if elapsed > expected_time * 1.5:
        issues.append(f"⏱️  GPU test took {elapsed:.1f}s (expected ~{expected_time:.1f}s)")
        recommendations.append("  - Check for thermal throttling")
        recommendations.append("  - Ensure drivers are up to date")
        recommendations.append("  - Close background applications using GPU")
    
    # Check memory
    if gpu_mem >= 16:
        print(f"  ✅ Excellent VRAM: {gpu_mem:.1f} GB - ideal for large AI models")
    elif gpu_mem >= 12:
        print(f"  ✅ Good VRAM: {gpu_mem:.1f} GB - suitable for most AI models")
    elif gpu_mem >= 8:
        issues.append(f"⚠️  Limited VRAM: {gpu_mem:.1f} GB (recommended 12GB+ for AI)")
        recommendations.append("  - Consider models optimized for lower VRAM")
        recommendations.append("  - Use memory optimization techniques (gradient checkpointing)")
    
    # Check compute capability
    props = torch.cuda.get_device_properties(0)
    if props.major >= 12:
        print(f"  ✅ Excellent compute capability: {props.major}.{props.minor} (Blackwell architecture)")
    elif props.major >= 10:
        print(f"  ✅ Good compute capability: {props.major}.{props.minor}")
    
    if issues:
        print("\n  ⚠️  Issues Found:")
        for issue in issues:
            print(f"    • {issue}")
        print("\n  📝 Recommendations:")
        for rec in recommendations:
            print(f"    {rec}")
    else:
        print("  ✅ No issues detected. GPU performance is excellent!")
    
    print("\n  ⭐ Performance Rating:")
    if "RTX 50" in gpu_name or "RTX 40" in gpu_name:
        print("    🏆 Excellent - Top-tier GPU for AI/ML workloads")
        print("    ✅ Ideal for training large models and running LLMs")
    elif "RTX 30" in gpu_name:
        print("    ✅ Good - Capable for most AI/ML workloads")
        print("    ⚠️  May struggle with very large models (>13B parameters)")
    else:
        print("    ⚠️  Moderate - Consider upgrading for serious AI work")

# =============================================================================
# STEP 17: STORAGE SPEED TEST WITH DIAGNOSIS
# =============================================================================

def storage_speed_test():
    """Step 17: Storage speed test with diagnosis"""
    print_section("STEP 17: STORAGE SPEED TEST")
    print("Why it matters: Measures read/write speeds")
    print("-" * 50)
    
    try:
        import tempfile
        
        test_size = 100 * 1024 * 1024
        temp_file = tempfile.mktemp()
        
        print(f"  Testing with {get_size(test_size)} file...")
        
        # Write test
        start = time.time()
        with open(temp_file, 'wb') as f:
            f.write(os.urandom(test_size))
        write_time = time.time() - start
        write_speed = test_size / write_time / 1024 / 1024
        
        # Read test
        start = time.time()
        with open(temp_file, 'rb') as f:
            data = f.read()
        read_time = time.time() - start
        read_speed = test_size / read_time / 1024 / 1024
        
        os.remove(temp_file)
        
        print(f"\n  📊 Results:")
        print(f"    Write Speed: {write_speed:.2f} MB/s")
        print(f"    Read Speed: {read_speed:.2f} MB/s")
        
        # DIAGNOSIS
        print("\n  📋 DIAGNOSIS:")
        print("  " + "-" * 50)
        
        issues = []
        recommendations = []
        drive_type = "Unknown"
        
        if write_speed > 500:
            drive_type = "NVMe SSD"
            print("  ✅ Excellent performance - NVMe SSD detected")
            if write_speed > 1000:
                print("  ✅ PCIe Gen 3/4 NVMe SSD with excellent speeds")
        elif write_speed > 200:
            drive_type = "SATA SSD"
            print("  ✅ Good performance - SATA SSD detected")
            issues.append("⏱️  SATA SSD detected (slower than NVMe)")
            recommendations.append("  - Consider upgrading to NVMe SSD for faster data loading")
            recommendations.append("  - SATA SSDs are still adequate for most AI workloads")
        elif write_speed > 50:
            drive_type = "HDD"
            issues.append("⚠️  HDD detected - Slow for AI workloads")
            recommendations.append("  - Upgrade to SSD for significantly better performance")
            recommendations.append("  - If using HDD, store datasets on SSD for faster loading")
            recommendations.append("  - Consider using NVMe SSD for best performance")
        else:
            drive_type = "Very Slow Drive"
            issues.append("❌  Very slow storage detected!")
            recommendations.append("  - IMMEDIATELY upgrade to SSD for AI work")
            recommendations.append("  - NVMe SSD recommended for AI/ML workloads")
            recommendations.append("  - HDD will significantly slow down training")
        
        # Check read vs write balance
        if read_speed > write_speed * 1.5:
            issues.append("⚠️  Read speed significantly faster than write")
            recommendations.append("  - Normal for most drives, but affects checkpoint saving")
            recommendations.append("  - Consider faster drive for training checkpoints")
        
        print("\n  📝 AI Workload Recommendations:")
        if drive_type == "NVMe SSD":
            print("    ✅ Storage is excellent for AI workloads")
            print("    ✅ Fast data loading for large datasets")
            print("    ✅ Quick checkpoint saving and loading")
        elif drive_type == "SATA SSD":
            print("    ⚠️  SATA SSD is adequate but slower than NVMe")
            print("    ℹ️  Consider NVMe SSD for large datasets (>100GB)")
        else:
            print("    ❌ HDD is NOT recommended for AI workloads")
            print("    ℹ️  Upgrade to NVMe SSD for best performance")
        
        if issues:
            print("\n  ⚠️  Issues Found:")
            for issue in issues:
                print(f"    • {issue}")
            print("\n  📝 Recommendations:")
            for rec in recommendations:
                print(f"    {rec}")
        else:
            print("  ✅ No storage issues detected")
        
        print("\n  ⭐ Performance Rating:")
        if write_speed > 1000:
            print("    🏆 Excellent - High-end NVMe SSD")
        elif write_speed > 500:
            print("    ✅ Good - Standard NVMe SSD")
        elif write_speed > 200:
            print("    ⚠️  Adequate - SATA SSD (consider NVMe upgrade)")
        else:
            print("    ❌ Insufficient - Upgrade to SSD immediately")
            
    except Exception as e:
        print(f"  ⚠️  Storage test error: {e}")

# =============================================================================
# STEP 18: NETWORK SPEED TEST WITH DIAGNOSIS
# =============================================================================

def network_speed_test():
    """Step 18: Network speed test with diagnosis"""
    print_section("STEP 18: NETWORK SPEED TEST")
    print("Why it matters: Measures download/upload speeds")
    print("-" * 50)
    
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
            
            # DIAGNOSIS
            print("\n  📋 DIAGNOSIS:")
            print("  " + "-" * 50)
            
            issues = []
            recommendations = []
            
            if download > 100:
                print(f"  ✅ Excellent download speed: {download:.1f} Mbps")
                if download > 500:
                    print("  ✅ Very fast connection - ideal for cloud/remote training")
            elif download > 50:
                issues.append(f"⚠️  Moderate download speed: {download:.1f} Mbps")
                recommendations.append("  - Consider faster internet for downloading large models")
                recommendations.append("  - Download models once, use local cache")
            else:
                issues.append(f"❌  Slow download speed: {download:.1f} Mbps")
                recommendations.append("  - Internet is too slow for large model downloads")
                recommendations.append("  - Consider using a download manager or scheduling downloads")
                recommendations.append("  - Use local model storage when possible")
            
            if upload > 50:
                print(f"  ✅ Excellent upload speed: {upload:.1f} Mbps")
            elif upload > 10:
                issues.append(f"⚠️  Moderate upload speed: {upload:.1f} Mbps")
                recommendations.append("  - Uploading large checkpoints may be slow")
                recommendations.append("  - Consider local backup instead of cloud")
            else:
                issues.append(f"❌  Slow upload speed: {upload:.1f} Mbps")
                recommendations.append("  - Uploading models/checkpoints will be very slow")
                recommendations.append("  - Use local storage for model artifacts")
            
            if ping < 20:
                print(f"  ✅ Excellent ping: {ping:.1f} ms")
            elif ping < 50:
                print(f"  ✅ Good ping: {ping:.1f} ms")
            elif ping < 100:
                issues.append(f"⚠️  High ping: {ping:.1f} ms")
                recommendations.append("  - May affect SSH/remote connections")
                recommendations.append("  - Consider using a VPN or different network")
            else:
                issues.append(f"❌  Very high ping: {ping:.1f} ms")
                recommendations.append("  - Remote development will be challenging")
                recommendations.append("  - Consider local development or better internet")
            
            print("\n  📝 AI Workload Recommendations:")
            if download > 100:
                print("    ✅ Internet is fast enough for cloud-based AI work")
                print("    ✅ Downloading large models and datasets is practical")
            elif download > 50:
                print("    ⚠️  Internet is adequate but may be slow for large downloads")
                print("    ℹ️  Pre-download models and cache datasets when possible")
            else:
                print("    ❌ Internet is too slow for cloud-based AI work")
                print("    ℹ️  Work with local models and datasets")
                print("    ℹ️  Consider using a faster connection or data center")
            
            if issues:
                print("\n  ⚠️  Issues Found:")
                for issue in issues:
                    print(f"    • {issue}")
                print("\n  📝 Recommendations:")
                for rec in recommendations:
                    print(f"    {rec}")
            else:
                print("  ✅ No network issues detected")
            
            print("\n  ⭐ Performance Rating:")
            if download > 500:
                print("    🏆 Excellent - High-speed connection (500+ Mbps)")
            elif download > 100:
                print("    ✅ Good - Suitable for cloud AI work (100+ Mbps)")
            elif download > 50:
                print("    ⚠️  Adequate - May be slow for large downloads (50+ Mbps)")
            else:
                print("    ❌ Insufficient - Upgrade internet for cloud AI work")
                
        except Exception as e:
            print(f"  ⚠️  Speed test error: {e}")
            print("  ℹ️  Network diagnosis limited - speedtest-cli may need reinstallation")
    else:
        print("  ⚠️  Speedtest not installed (pip install speedtest-cli)")

# =============================================================================
# STEP 19: SYSTEM SUMMARY
# =============================================================================

def system_summary():
    """Step 19: Overall system readiness assessment"""
    print_section("STEP 19: SYSTEM SUMMARY")
    print("Why it matters: Provides overall readiness assessment")
    print("-" * 50)
    
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
# VIRTUAL ENVIRONMENT SETUP WIZARD WITH CHOICES
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
    print("  " + "="*70)

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
            # Check if conda is installed
            subprocess.run(['conda', '--version'], check=True, capture_output=True)
            print(f"  ✅ Conda detected, creating environment...")
            
            # Create conda environment with Python
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
            # Check if micromamba is installed
            subprocess.run(['micromamba', '--version'], check=True, capture_output=True)
            print(f"  ✅ Micromamba detected, creating environment...")
            
            # Create micromamba environment
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
            # Check if uv is installed
            subprocess.run(['uv', '--version'], check=True, capture_output=True)
            print(f"  ✅ uv detected, creating environment...")
            
            # Create uv virtual environment
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
    
    # Show comparison
    show_environment_comparison()
    
    response = input("\nWould you like to create a virtual environment now? (y/n): ").strip().lower()
    
    if response != 'y':
        print("\n⏭️  Skipping virtual environment setup.")
        print("   You can create one manually later when ready.")
        print("\n   Manual setup options:")
        print("   • venv:   python -m venv ai_env")
        print("   • conda:  conda create -n ai_env python=3.12")
        print("   • uv:     uv venv ai_env")
        print("   • micromamba: micromamba create -n ai_env python=3.12")
        return
    
    # Select tool
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
        print("   You can create one manually later when ready.")
        print("\n   Manual setup options:")
        print("   • venv:   python -m venv ai_env")
        print("   • conda:  conda create -n ai_env python=3.12")
        print("   • uv:     uv venv ai_env")
        print("   • micromamba: micromamba create -n ai_env python=3.12")
        return
    
    # Get environment name
    env_name = input(f"\nEnter environment name (default: ai_env): ").strip()
    if not env_name:
        env_name = "ai_env"
    
    # Create environment
    activate_cmd, pip_cmd, python_cmd = create_environment_with_tool(tool, env_name, installed_list)
    
    if activate_cmd is None:
        return
    
    print(f"\n  📝 To activate the virtual environment:")
    print(f"     {activate_cmd}")
    
    # Ask if user wants to install packages
    install_packages = input("\n📦 Install AI/ML packages in the new environment? (y/n): ").strip().lower()
    
    if install_packages == 'y':
        print("\n📥 Installing packages...")
        
        # Determine packages to install based on tool
        packages = []
        
        # Always include essential packages
        if tool in ['conda', 'micromamba']:
            # Conda/Micromamba - install with CUDA support
            packages.append('pytorch')
            packages.append('torchvision')
            packages.append('torchaudio')
            packages.append('pytorch-cuda=12.1')
            packages.append('-c')
            packages.append('pytorch')
            packages.append('-c')
            packages.append('nvidia')
        else:
            # venv/uv - pip install with CUDA index
            packages.append('torch')
            packages.append('torchvision')
            packages.append('torchaudio')
            packages.append('--index-url')
            packages.append('https://download.pytorch.org/whl/cu121')
        
        # Add missing packages
        for pkg in missing_list:
            if pkg != 'torch':
                if tool in ['conda', 'micromamba'] and pkg in ['numpy', 'pandas', 'matplotlib', 'scikit-learn']:
                    packages.append(pkg)
                elif tool in ['conda', 'micromamba'] and pkg == 'scikit-learn':
                    packages.append('scikit-learn')
                else:
                    packages.append(pkg)
        
        # Add recommended packages
        recommended_pkgs = ['transformers', 'accelerate', 'xformers', 'numpy', 'pandas', 'matplotlib', 'seaborn']
        for pkg in recommended_pkgs:
            if pkg not in installed_list and pkg not in packages:
                if tool in ['conda', 'micromamba']:
                    packages.append(pkg)
                else:
                    packages.append(pkg)
        
        if packages:
            print(f"\n  Installing: {' '.join(packages)}")
            
            try:
                if tool in ['conda', 'micromamba']:
                    # Use conda/micromamba to install
                    if tool == 'conda':
                        install_cmd = ['conda', 'install'] + packages + ['-y']
                    else:
                        install_cmd = ['micromamba', 'install'] + packages + ['-y']
                    subprocess.run(install_cmd, check=True)
                else:
                    # Use pip with the environment's pip
                    if pip_cmd:
                        install_cmd = [pip_cmd] + packages
                        subprocess.run(install_cmd, shell=True, check=True)
                    else:
                        # Fallback to system pip
                        subprocess.run([sys.executable, '-m', 'pip', 'install'] + packages, check=True)
                
                print("  ✅ Packages installed successfully!")
                
                # Create requirements.txt
                print("\n  📝 Creating requirements.txt...")
                if pip_cmd:
                    subprocess.run([pip_cmd, 'freeze', '>', 'requirements.txt'], shell=True)
                else:
                    subprocess.run([sys.executable, '-m', 'pip', 'freeze', '>', 'requirements.txt'], shell=True)
                print("  ✅ requirements.txt created!")
                
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Failed to install packages: {e}")
                print("  ℹ️  Try installing manually after activating the environment:")
                print(f"     {activate_cmd}")
                if tool in ['conda', 'micromamba']:
                    print(f"     conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia")
                    print(f"     conda install transformers pandas numpy matplotlib seaborn scikit-learn accelerate")
                else:
                    print(f"     pip install torch transformers pandas numpy matplotlib seaborn scikit-learn accelerate")
        else:
            print("  ✅ All packages are already installed!")
    
    print("\n" + "="*70)
    print("✅ Virtual environment setup complete!")
    print("="*70)
    print(f"\n📝 Next steps:")
    print(f"  1. Activate: {activate_cmd}")
    print(f"  2. Verify GPU: {python_cmd} -c 'import torch; print(torch.cuda.is_available())'")
    print(f"  3. Install additional packages: {pip_cmd} install <package>")
    print(f"  4. Freeze dependencies: {pip_cmd} freeze > requirements.txt")
    
    # Tool-specific notes
    print(f"\n  📌 {tool.upper()} Tips:")
    if tool == 'conda':
        print("    - conda install <package>  # Install packages")
        print("    - conda env export > environment.yml  # Export environment")
        print("    - conda env create -f environment.yml  # Create from file")
    elif tool == 'micromamba':
        print("    - micromamba install <package>  # Install packages")
        print("    - micromamba env export > environment.yml  # Export environment")
    elif tool == 'uv':
        print("    - uv pip install <package>  # Install packages")
        print("    - uv pip freeze > requirements.txt  # Export requirements")
        print("    - uv venv --python 3.12  # Create with specific Python")
    else:  # venv
        print("    - pip install <package>  # Install packages")
        print("    - pip freeze > requirements.txt  # Export requirements")
        print("    - deactivate  # Deactivate when done")

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
    get_gpu_info()              # Steps 8-13
    in_venv, installed_list, missing_list = get_software_info()  # Step 14
    cpu_stress_test()           # Step 15
    gpu_stress_test()           # Step 16
    storage_speed_test()        # Step 17
    network_speed_test()        # Step 18
    system_summary()            # Step 19
    
    # Virtual Environment Setup Wizard
    virtual_environment_setup_wizard(in_venv, installed_list, missing_list)
    
    print("\n" + "="*70)
    print("✅ System scan completed successfully!")
    print("="*70)

if __name__ == "__main__":
    main()