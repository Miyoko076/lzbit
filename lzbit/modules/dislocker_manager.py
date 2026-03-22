import subprocess
import re
from pathlib import Path

class DislockerManager:
    def get_key_from_bek(self, bek_file_path: str) -> bytes:
        target_path = Path(bek_file_path).resolve()
        
        if not target_path.exists():
            raise FileNotFoundError(f"BEK file not found: {target_path}")

        if not target_path.is_file():
            raise ValueError(f"Path exists but is not a file: {target_path}")

        wsl_ram_path = f"/dev/shm/{target_path.name}"
        
        try:
            with open(target_path, "rb") as f:
                bek_data = f.read()

            setup_cmd = ["wsl", "bash", "-c", f"cat > '{wsl_ram_path}'"]
            subprocess.run(setup_cmd, input=bek_data, check=True)

            command = ["wsl", "-e", "dislocker-bek", "-f", wsl_ram_path]
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                raise Exception(f"dislocker-bek failed:\n{result.stderr.strip()}")
                
            raw_output = result.stdout.strip()
            
            if "[INFO] Key:" not in raw_output:
                raise ValueError("Could not find '[INFO] Key:' section in the output.")
                
            key_section = raw_output.split("[INFO] Key:")[-1]
            key_hex = ""
            
            for line in key_section.splitlines():
                match = re.search(r'0x[0-9a-fA-F]{8}\s+(.*)', line)
                if match:
                    clean_hex = re.sub(r'[\s\-]', '', match.group(1))
                    key_hex += clean_hex
            
            if len(key_hex) >= 64:
                return bytes.fromhex(key_hex[:64])
            else:
                raise ValueError(f"Extracted hex string is too short: {key_hex}")
                
        except Exception as e:
            if 'raw_output' in locals():
                raise Exception(f"Parsing failed: {e}\nRaw output:\n{raw_output}")
            else:
                raise Exception(f"Process failed: {e}")
                
        finally:
            subprocess.run(["wsl", "rm", "-f", wsl_ram_path])