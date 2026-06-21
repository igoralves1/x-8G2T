
https://www.msi.com/support/technical_details/vga_msi_utility_afterburner
https://www.msi.com/Landing/afterburner/graphics-cards
https://www.youtube.com/watch?v=f2zQiMKdso8
https://www.youtube.com/watch?v=HZdTex-tsgM


### 🔗 Official Download Links for MSI Afterburner

To ensure you download the correct and safe version of MSI Afterburner, **only use the official sources** .

*   **Official MSI Afterburner Landing Page:** [https://www.msi.com/Landing/afterburner/graphics-cards](https://www.msi.com/Landing/afterburner/graphics-cards) 
*   **Official MSI Support Page:** [https://www.msi.com/support/technical_details/vga_msi_utility_afterburner](https://www.msi.com/support/technical_details/vga_msi_utility_afterburner) 

**⚠️ Important Security Warning:** MSI has warned that many fake Afterburner sites exist. Only download from `msi.com` or `guru3d.com` to avoid potential phishing attacks that could steal your data .

---

### 📥 Installation & Setup Steps

#### Step 1: Download the Latest Version
- Download the latest version from the links above. For the **RTX 5080**, it is recommended to use the latest version (4.6.7 Beta or newer) as it includes important support for newer NVIDIA GPU architectures .

#### Step 2: Run the Installer
1. Extract the downloaded files and run the installer
2. Select your preferred language and click "Next"
3. Accept the license agreement

#### Step 3: Critical Component Selection
**This step is very important:**
- ✅ Check **MSI Afterburner** (the main program)
- ✅ **MUST check** **RivaTuner Statistics Server (RTSS)**  - this is essential for monitoring and OSD display in games

#### Step 4: Complete Installation
1. Choose the installation directory (default is recommended)
2. Click "Install" and wait for the main program to install
3. **Important**: A second installer will automatically pop up for RivaTuner Statistics Server - complete this installation as well

---

### ⚡ Recommended Settings for the RTX 5080

| Setting | Recommended Value | Notes |
|---------|-------------------|-------|
| **Power Limit** | +11% | Maximum available for most cards |
| **Core Clock Offset** | +200 to +245 MHz | Test stability, adjust in +25 MHz steps |
| **Memory Clock Offset** | +2000 MHz | Many RTX 5080s can handle this |
| **Fan Speed** | Custom curve | Set aggressive curve for better cooling |

**Important Notes:**

- **RTX 50-series overclocking is different** from previous generations. The latest MSI Afterburner Beta is specifically designed to handle the new Blackwell architecture limitations .

- **Testing stability**: After each adjustment, test with benchmarks like 3DMark or Unigine Heaven, or run your actual games/AI workloads for at least 30 minutes.

- **Watch for artifacts**: If you see visual glitches, white spots ("snow"), or system crashes, your overclock is unstable. Reduce the clock by 25-50 MHz until stable .

---

### 💡 Automatic Performance for AI Workloads

Since you mentioned wanting automatic overclocking for AI workloads, you can use MSI Afterburner's **profile system**:

1. Save your overclock settings to Profile 1 (e.g., `+200 MHz Core, +1000 MHz Memory`)
2. Save stock settings to Profile 2
3. Manually switch profiles when running AI workloads vs. when idle

You can also use third-party tools like **MSIAfterburnerScript** to automatically switch profiles based on running applications (e.g., Python for AI workloads).

To automate MSI Afterburner profile switching for AI workloads, you have several options ranging from simple command-line scripts to dedicated third-party tools.

### 🔧 Method 1: Command Line with Task Scheduler (No External Tools)

This is the most reliable approach without installing extra software. MSI Afterburner supports command-line profile switching directly .

#### Step 1: Set Up Your Profiles
1. Open MSI Afterburner
2. Configure your AI/performance settings (e.g., +200 MHz Core, +1000 MHz Memory, +11% Power Limit)
3. Click the **Save** icon (floppy disk) and save to **Profile 1**
4. Save your stock/power-saving settings to **Profile 2**

#### Step 2: Create Batch Files

**`enable_ai_overclock.bat`**:
```batch
"C:\Program Files (x86)\MSI Afterburner\MSIAfterburner.exe" -Profile1
```

**`disable_ai_overclock.bat`**:
```batch
"C:\Program Files (x86)\MSI Afterburner\MSIAfterburner.exe" -Profile2
```

#### Step 3: Automate with Task Scheduler
1. Open **Task Scheduler** (search in Start Menu)
2. Create a new task:
   - **Trigger**: "When a program starts" → select `python.exe` (or your AI app)
   - **Action**: "Start a program" → browse to `enable_ai_overclock.bat`
3. Create another task to revert when Python closes:
   - **Trigger**: "When a program stops" → select `python.exe`
   - **Action**: Start `disable_ai_overclock.bat`

> **Note**: MSI Afterburner must be running for command-line switches to work. The commands will apply the profile to the already-running instance .

---

### 🛠️ Method 2: MSIAfterburnerScript (Recommended)

This GitHub tool automatically detects when specific applications (like `python.exe`) are running and switches profiles instantly . It uses an **event-driven** monitoring mode that reacts immediately when you launch a program .

#### Installation & Setup:
1. Download from: [https://github.com/ethanperrine/MSIAfterburnerScript](https://github.com/ethanperrine/MSIAfterburnerScript) 
2. Configure `config.json`:

```json
{
    "afterburner_path": "C:\\Program Files (x86)\\MSI Afterburner\\MSIAfterburner.exe",
    "profile_on": "-Profile1",
    "profile_off": "-Profile2",
    "monitoring_mode": "event",
    "overrides": {
        "python.exe": "-Profile1",
        "pytorch": "-Profile1",
        "tensorflow": "-Profile1",
        "jupyter": "-Profile1"
    }
}
```

3. Run the executable (requires Administrator privileges) 

The tool monitors:
- **Foreground Check**: Applies profile when your AI app is active and in focus 
- **Background Check**: Detects AI processes even if minimized 
- **Partial Matching**: "python" matches "python.exe" automatically 

**Features**:
- State-aware: only sends commands when a profile change is needed 
- Supports multiple target apps with different profiles 
- Can be added to Windows Startup for automatic operation 

---

### 🔄 Method 3: Alternative Tray Utility

If you want a lightweight tray-based switcher without background monitoring, you can use **MSI Afterburner Profile Loader** :

- System tray icon for manual profile switching
- Can be set to run at Windows startup
- Doesn't keep MSI Afterburner running in background (saves resources) 

---

### 💡 Tips for AI Workloads

Based on community experience with RTX 5080 and AI applications:

- **Stability is key**: AI workloads (especially generative AI) are more sensitive to overclocks than games. Many users report "micro crashes" with overclocks that were stable in games .
- **Start conservative**: Test with +200 MHz Core first, then increase in small steps .
- **Memory OC is often safe**: Many RTX 5080 users can push memory to +2000 MHz without issues .
- **Power Limit**: Setting to +11% (or 125% on some cards) gives headroom for AI workloads .
- **Watch temperatures**: With your liquid cooling, aim to keep GPU under 75°C under load .

**For AI performance**, note that RTX 5080's tensor cores are the powerhouse for generative AI models. Some applications may need optimization for the Blackwell architecture to fully utilize them . Overclocking may not give huge gains in AI workloads until software is optimized .

---

### 📋 Recommended Overclock Settings for AI Workloads

| Setting | Recommended Value | Notes |
|---------|-------------------|-------|
| **Core Clock** | +200 to +245 MHz | Start low, increase in +25 MHz steps  |
| **Memory Clock** | +1000 to +2000 MHz | Most RTX 5080s handle this easily  |
| **Power Limit** | +11% (or max available) | Allows full power draw for AI workloads  |
| **Voltage** | Leave at default | AI workloads can be sensitive to voltage spikes  |

**With your liquid cooling**, you have excellent thermal headroom to push these settings safely! 🚀




Here are the full specifications for your **MSI Ventus GeForce RTX 5080 16G VENTUS 3X OC PLUS**, compiled from official MSI sources :

| Category | Specification |
| :--- | :--- |
| **GPU Engine** | NVIDIA GeForce RTX 5080  |
| **CUDA Cores** | 10752 Units  |
| **Core Clocks** | Boost: 2640 MHz<br>Extreme Performance: 2655 MHz (via MSI Center)  |
| **Memory** | 16GB GDDR7  |
| **Memory Interface** | 256-bit  |
| **Memory Clock** | 30 Gbps  |
| **PCI Express** | Gen 5  |
| **Outputs** | 3 x DisplayPort (v2.1b)<br>1 x HDMI™ (2.1b, supporting up to 4K 480Hz or 8K 120Hz with DSC)  |
| **Max Displays** | 4  |
| **Max Resolution** | 7680 x 4320  |
| **Power Connectors** | 16-pin x 1 (ATX 3.1 PSU recommended)  |
| **Recommended PSU** | 850 W  |
| **Power Consumption** | 360 W  |
| **Card Dimensions** | 303 x 121 x 49 mm  |
| **Card Weight** | 1105 g  |
| **API Support** | DirectX 12 Ultimate, OpenGL 4.6  |
| **Features** | SFF-Ready Enthusiast GeForce Card<br>TORX Fan 5.0<br>Nickel-plated Copper Baseplate<br>Core Pipes<br>Metal Backplate<br>Zero Frozr (fan stop at low temps)<br>DrMOS<br>Fuse (overcurrent protection)<br>MSI Center & Afterburner software<br>NVIDIA Blackwell, DLSS 4, Reflex 2  |
| **Included Accessories** | Graphics card holder<br>16-pin to 3x 8-pin power cable adapter  |

This model is designed with a focus on essential, reliable performance and efficient cooling for a wide range of systems, including SFF (Small Form Factor) builds .

## Ventus 3X OC PLUS vs. SUPRIM LIQUID SOC: The Time vs. Cost Decision

### 🆚 Detailed Comparison

| Feature | Ventus 3X OC PLUS | SUPRIM LIQUID SOC | Impact for Fine-Tuning |
| :--- | :--- | :--- | :--- |
| **GPU Architecture** | NVIDIA Blackwell, 10752 CUDA Cores | NVIDIA Blackwell, 10752 CUDA Cores | **Identical** — same compute power for training. |
| **VRAM** | 16GB GDDR7 | 16GB GDDR7 | **Identical** — both can run the same models with QLoRA. |
| **Boost Clock** | 2.655 GHz | 2.760 GHz | SUPRIM has ~4% higher clock, but this is minor for memory-bound AI tasks. |
| **Cooling System** | 3x TORX 5.0 fans (air-cooled) | Hybrid: 360mm liquid radiator | **The deciding factor** — SUPRIM runs cooler and quieter under sustained 100% loads. |
| **Expected Fine-Tuning Time** | ~3.3 hours (10K samples, 8B model)  | Slightly faster due to better thermal headroom | The difference is **marginal** — better cooling prevents thermal throttling but doesn't significantly boost compute speed. |
| **Price** | ~$1,200 | ~$1,700  | Ventus is **~$500 cheaper**. |

---

### 💻 AI Fine-Tuning Capabilities (Identical for Both)

Since both cards share the same 16GB VRAM and CUDA core count, they can handle the same workloads:

| Model Size | Example | Feasibility on Both |
| :--- | :--- | :--- |
| **Small (7-8B)** | Llama 3 8B, Mistral 7B | ✅ **Fully feasible.** Using QLoRA (4-bit quantization), the model fits comfortably in 10-12GB VRAM. Fine-tuning 10K samples takes ~3.3 hours . Real-world testing confirms ~4 hours to fine-tune Llama 3.1 8B on medical data . |
| **Medium (14B)** | Llama 3.1 14B, Phi-4 | ⚠️ **Possible but tight.** With 4-bit QLoRA, a 14B model uses ~10GB VRAM and takes ~3 hours for 5K samples . The 16GB limit works but requires careful batch size tuning. |
| **Large (70B+)** | Llama 3 70B, DeepSeek-R1 | ❌ **Not feasible on either.** A 70B model in 4-bit requires over 32GB VRAM . You'd need multi-GPU or cloud instances. |

**Benchmark Reference:** The RTX 5080 achieves ~7.8 samples/sec for LLaMA 3 8B LoRA fine-tuning with 4-bit precision, completing 10K samples in ~21 minutes .

---

### ⏱️ Does the SUPRIM's Cost Pay Off for Faster Training?

**No — the value proposition heavily favors the Ventus.**

Here's why:

1. **Performance Difference is Minimal for AI:** Fine-tuning is primarily **memory-bandwidth bound** (960 GB/s on both cards). The thermal advantage of liquid cooling prevents throttling but doesn't meaningfully accelerate compute. The SUPRIM might finish a 3.3-hour run a few minutes faster — not hours.

2. **Same VRAM Constraint:** Both are capped at 16GB. The SUPRIM cannot handle larger models than the Ventus. The moment you need a 70B model, both fail.

3. **Cost-to-Time Calculation:** The SUPRIM costs ~$500 more . Over the lifetime of the card, even if it saves you **10 hours** of training time per year, that's ~$50/hour saved — not worth the premium unless your time is extremely valuable. For most users, the Ventus is the smarter choice.

4. **Real-World Perspective:** If fine-tuning is a serious business requiring 24/7 GPU loads, the SUPRIM's superior cooling and quieter operation justify the premium. If you're a researcher or enthusiast running occasional fine-tuning sessions (a few hours per week), the Ventus delivers the **same functional performance** for significantly less money.

---

### 🎯 Which One Should You Choose?

| Scenario | Recommendation |
| :--- | :--- |
| **You do occasional AI fine-tuning (few hours/week)** | ✅ **Ventus 3X OC PLUS.** The $500 saved is better spent on more RAM, storage, or another project. The time difference is negligible. |
| **You run sustained 100% GPU loads for days (training, rendering)** | ✅ **SUPRIM LIQUID SOC.** The liquid cooling ensures stable boost clocks, lower temperatures, and quieter operation under extreme sustained loads. |
| **You need to run 70B+ models** | ❌ **Neither.** Both lack VRAM. Look at RTX 5090 (32GB) or cloud solutions. |
| **You're budget-conscious and want best value** | ✅ **Ventus 3X OC PLUS.** The core AI performance — models you can run, training speed — is identical. The SUPRIM's premium is purely for cooling, not compute . |

**Bottom line:** If your only concern is "can I run the same models and finish with slightly more time?" — the Ventus wins decisively. The SUPRIM's $500 premium does not unlock additional AI capabilities; it simply makes the system quieter and cooler during marathon sessions. For 99% of users, the Ventus offers superior value for money .


Aegis ZS2 B7NUG-1012US  
https://www.msi.com/Motherboard/PRO-B650-VC-WIFI-II  
https://us.msi.com/Desktop/Aegis-ZS2/support?sku_id=95032#bios  

Product Name: Aegis ZS2 B9NVV-1409US-BAR999X5081632GS2TX11MAB5
Model: 9S6-BZ0171-1409
Serial Number: MSBZ01P9A0106107
Mother Board
```
$ Get-CimInstance -ClassName Win32_BaseBoard | Format-List *

Status                  : OK
Name                    : Base Board
PoweredOn               : True
Caption                 : Base Board
Description             : Base Board
InstallDate             :
CreationClassName       : Win32_BaseBoard
Manufacturer            : Micro-Star International Co., Ltd.
Model                   :
OtherIdentifyingInfo    :
PartNumber              :
SerialNumber            : 07E1810_P61E648609
SKU                     :
Tag                     : Base Board
Version                 : 1.0
Depth                   :
Height                  :
HotSwappable            : False
Removable               : False
Replaceable             : True
Weight                  :
Width                   :
HostingBoard            : True
RequirementsDescription :
RequiresDaughterBoard   : False
SlotLayout              :
SpecialRequirements     :
ConfigOptions           : {To be filled by O.E.M.}
Product                 : PRO B650-VC WIFI III (MS-7E18)
PSComputerName          :
CimClass                : root/cimv2:Win32_BaseBoard
CimInstanceProperties   : {Caption, Description, InstallDate, Name...}
CimSystemProperties     : Microsoft.Management.Infrastructure.CimSystemProperties
```

BIOS 
```
$ Get-CimInstance -ClassName Win32_BIOS | Format-List *

Status                         : OK
Name                           : 1.H9
Caption                        : 1.H9
SMBIOSPresent                  : True
Description                    : 1.H9
InstallDate                    :
BuildNumber                    :
CodeSet                        :
IdentificationCode             :
LanguageEdition                :
Manufacturer                   : American Megatrends International, LLC.
OtherTargetOS                  :
SerialNumber                   : MSBZ01P9A0106107
SoftwareElementID              : 1.H9
SoftwareElementState           : 3
TargetOperatingSystem          : 0
Version                        : ALASKA - 1072009
PrimaryBIOS                    : True
BiosCharacteristics            : {7, 11, 12, 15...}
BIOSVersion                    : {ALASKA - 1072009, 1.H9, American Megatrends - 50023}
CurrentLanguage                :
EmbeddedControllerMajorVersion : 255
EmbeddedControllerMinorVersion : 255
InstallableLanguages           :
ListOfLanguages                :
ReleaseDate                    : 8/13/2025 8:00:00 PM
SMBIOSBIOSVersion              : 1.H9
SMBIOSMajorVersion             : 3
SMBIOSMinorVersion             : 7
SystemBiosMajorVersion         : 5
SystemBiosMinorVersion         : 35
PSComputerName                 :
CimClass                       : root/cimv2:Win32_BIOS
CimInstanceProperties          : {Caption, Description, InstallDate, Name...}
CimSystemProperties            : Microsoft.Management.Infrastructure.CimSystemProperties
```

Wifi Adapter
```
$ Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, NetworkInterfaceType

Name     InterfaceDescription                                                           Status       NetworkInterfaceType
----     --------------------                                                           ------       --------------------
Ethernet Realtek PCIe GbE Family Controller                                             Disconnected
Wi-Fi    Qualcomm FastConnect 7800 Wi-Fi 7 High Band Simultaneous (HBS) Network Adapter Up
Wi-Fi 4  Qualcomm FastConnect 7800 Wi-Fi 7 High Band Simultaneous (HBS) Network Adapter Not Present
Wi-Fi 3  Qualcomm FastConnect 7800 Wi-Fi 7 High Band Simultaneous (HBS) Network Adapter Disconnected
```

Current Connection Standard
```
$ netsh wlan show interfaces

There are 2 interfaces on the system:

    Name                   : Wi-Fi
    Description            : Qualcomm FastConnect 7800 Wi-Fi 7 High Band Simultaneous (HBS) Network Adapter
    GUID                   : c62d023f-329b-4d26-8e12-7218d4bf1060
    Physical address       : dc:56:7b:1f:84:fd
    Interface type         : Primary
    State                  : connected
    SSID                   : alextrex
    AP BSSID               : 70:13:01:8a:d9:a3
         Colocated APs:    : 3
            BSSID: 72:13:01:83:d9:a4,  Band: 5 GHz,  Channel: 44
            BSSID: 72:13:01:83:d9:a2,  Band: 5 GHz,  Channel: 44
            BSSID: 72:13:01:83:d9:a6,  Band: 5 GHz,  Channel: 44
    Band                   : 6 GHz
    Channel                : 197
    Connected Akm-cipher   : [ akm = 00-0f-ac:08, cipher =  00-0f-ac:04 ]
    Network type           : Infrastructure
    Radio type             : 802.11ax
    Authentication         : WPA3-Personal  (H2E)
    Cipher                 : CCMP
    Connection mode        : Auto Connect
    Receive rate (Mbps)    : 2401.9
    Transmit rate (Mbps)   : 2401.9
    Signal                 : 100%
    Rssi                   : -43
    Profile                : alextrex
    QoS MSCS Configured         : 0
    QoS Map Configured          : 0
    QoS Map Allowed by Policy   : 0

    Name                   : Wi-Fi 3
    Description            : Qualcomm FastConnect 7800 Wi-Fi 7 High Band Simultaneous (HBS) Network Adapter #3
    GUID                   : 4cc5eb0f-c926-4910-a135-57a0707d49ef
    Physical address       : fe:56:7b:1f:84:fd
    Interface type         : Secondary
    Primary interface      : Wi-Fi
    State                  : disconnected
    Radio status           : Hardware On
                             Software On
```