# lzbit (Lazy BitLocker Decryptor CLI)

A command-line tool designed to easily encrypt, decrypt, unlock, lock VHD/VHDX files. Through this CLI, you can encrypt or unlock VHDs using file inputs or key inputs without any length or special characters limit. It also allows you to unlock volumes instantly without needing to manually enter a password.

## System Requirements

* Operating System: Windows 11 Pro or higher (Pro, Enterprise, Education, etc.). *Windows Home edition is not supported
* WSL2: Windows Subsystem for Linux 2 must be enabled and set up.  

## Installation

1. Open a terminal (PowerShell or Command Prompt) with administrator privileges and clone the repository:
```bash
git clone https://github.com/Miyoko076/lzbit.git
```

2. Install Python dependencies using uv:  
```bash
uv pip install -r requirements.txt
```

3. Install WSL dependencies (dislocker is required to extract the BEK file header using dislocker-bek):
```
wsl sudo apt install dislocker
```

## Usage

> NOTE: Please ensure you run your terminal (PowerShell or Command Prompt) as an Administrator

### General Syntax
```bash
uv run lzbit <command> [arguments]
```

### Commands
```plain
1. Encrypt
Encrypts a target VHD/VHDX file and generates a .BEK key file.  
uv run lzbit encrypt <VHD_FILE>  
uv run lzbit encrypt "D:\Ubuntu-Volume.vhdx"

2. Decrypt
Completely removes BitLocker encryption from the target VHD/VHDX, converting it back to a normal volume.  
uv run lzbit decrypt <VHD_FILE>  
uv run lzbit decrypt "D:\Ubuntu-Volume.vhdx"

3. Unlock
Unlocks a target VHD/VHDX using the provided .BEK or .aes key file.  
uv run lzbit unlock <VHD_FILE> <KEY_FILE> [-m {pass,key,pipe}]  
uv run lzbit unlock "D:\Ubuntu-Volume.vhdx" "D:\Ubuntu-Volume-KEY.BEK"
uv run lzbit unlock "D:\Ubuntu-Volume.vhdx" "D:\Ubuntu-Volume-KEY_pass.aes" -m pass
uv run lzbit unlock "D:\Ubuntu-Volume.vhdx" "D:\Ubuntu-Volume-KEY_key.aes" -m key
curl --silent "https://172.17.0.0:7860" | uv run lzbit unlock "D:\Ubuntu-Volume.vhdx" "D:\Ubuntu-Volume-KEY_pipe.aes" -m pipe

4. Lock
Securely locks and unmounts the currently unlocked VHD/VHDX.  
uv run lzbit lock <VHD_FILE>  
uv run lzbit lock "D:\Ubuntu-Volume.vhdx"

5. Generate AES from BEK
Generates a secure AES file from the original .BEK file.
uv run lzbit crypbek <BEK_FILE> [-m {pass,key,pipe}]  
uv run lzbit crypbek "D:\Ubuntu-Volume.vhdx" "D:\Ubuntu-Volume-KEY_pass.aes" -m pass
uv run lzbit crypbek "D:\Ubuntu-Volume.vhdx" "D:\Ubuntu-Volume-KEY_key.aes" -m key
curl --silent https://172.17.0.0:7860 | uv run lzbit crypbek "D:\Ubuntu-Volume.vhdx" "D:\Ubuntu-Volume-KEY_pipe.aes" -m pipe
```