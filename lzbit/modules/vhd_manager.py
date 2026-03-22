import subprocess
import textwrap
import sys
import base64
import json

class VhdManager:
    def _run_powershell_script(self, script: str) -> str:
        header = textwrap.dedent("""
            $ProgressPreference = 'SilentlyContinue'
            $InformationPreference = 'SilentlyContinue'
            $WarningPreference = 'SilentlyContinue'
            Import-Module Storage -ErrorAction SilentlyContinue
            $ErrorActionPreference = 'Stop'
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        """).strip()
        
        full_script = f"{header}\n{script}"
        encoded_script = base64.b64encode(full_script.encode('utf-16le')).decode('utf-8')
        
        command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded_script]
        
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            err_msg = result.stderr.strip() if result.stderr else "Unknown error occurred during script execution."
            raise Exception(f"PowerShell Execution Failed:\n{err_msg}")

        if result.stderr:
            print(f"[VhdManager Warning] {result.stderr.strip()}", file=sys.stderr)
            
        return result.stdout.strip() if result.stdout else None

    def is_vhd_attached(self, vhd_path: str) -> bool:
        safe_path = self._escape_path(vhd_path)
        script = textwrap.dedent(f"""
            try {{
                $diskImage = Get-DiskImage -ImagePath '{safe_path}'
                if ($diskImage) {{
                    [Console]::WriteLine($diskImage.Attached)
                }} else {{
                    [Console]::WriteLine($false)
                }}
            }} catch {{
                [Console]::Error.WriteLine("VHD 상태 확인 실패: $($_.Exception.Message)")
                exit 1
            }}
        """).strip()
        
        try:
            result = self._run_powershell_script(script)
            return result is not None and result.strip().lower() == "true"
        except Exception as e:
            print(f"[-] {e}", file=sys.stderr)
            return False

    def get_volume_device_ids(self, vhd_path: str) -> list[str]:
        safe_path = self._escape_path(vhd_path)
        
        script = textwrap.dedent(f"""
            try {{
                $diskImage = Get-DiskImage -ImagePath '{safe_path}'
                if ($diskImage -and $diskImage.Attached) {{
                    $volumes = $diskImage | Get-Disk | Get-Partition | Get-Volume
                    if ($volumes) {{
                        @($volumes.UniqueId) | ConvertTo-Json -Compress
                    }} else {{
                        "null"
                    }}
                }} else {{
                    "null"
                }}
            }} catch {{
                [Console]::Error.WriteLine("볼륨 ID 추출 실패: $($_.Exception.Message)")
                exit 1
            }}
        """).strip()
        
        try:
            result = self._run_powershell_script(script)
            if not result:
                return []
                
            parsed_ids = json.loads(result)
            if parsed_ids is None:
                return []
                
            if isinstance(parsed_ids, str):
                parsed_ids = [parsed_ids]
                
            return [v for v in parsed_ids if isinstance(v, str) and v.startswith(r"\\?\Volume")]
            
        except json.JSONDecodeError as e:
            print(f"[-] JSON 파싱 실패: {e}\n원본 데이터: {result}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"[-] {e}", file=sys.stderr)
            return []

    def mount_vhd(self, vhd_path: str):
        """VHD를 시스템에 물리적으로 연결(Attach)만 합니다. (드라이브 문자 할당 여부 무관)"""
        if self.is_vhd_attached(vhd_path):
            return 
            
        safe_path = self._escape_path(vhd_path)
        
        script = textwrap.dedent(f"""
            try {{
                Mount-DiskImage -ImagePath '{safe_path}'
            }} catch {{
                [Console]::Error.WriteLine("Mount-DiskImage 실패: $($_.Exception.Message)")
                exit 1
            }}
        """).strip()
        
        self._run_powershell_script(script)

    def dismount_vhd(self, vhd_path: str):
        """VHD의 물리적 연결(Attach)을 해제합니다."""
        if not self.is_vhd_attached(vhd_path):
            return
            
        safe_path = self._escape_path(vhd_path)
        
        script = textwrap.dedent(f"""
            try {{
                Dismount-DiskImage -ImagePath '{safe_path}'
            }} catch {{
                [Console]::Error.WriteLine("Dismount-DiskImage 실패: $($_.Exception.Message)")
                exit 1
            }}
        """).strip()
        
        self._run_powershell_script(script)

    def get_drive_letter_for_vhd(self, vhd_path: str) -> str | None:
        """VHD에 할당된 첫 번째 드라이브 문자(예: 'D:')를 반환합니다. 할당되지 않은 경우 None을 반환합니다."""
        safe_path = self._escape_path(vhd_path)
        
        script = textwrap.dedent(f"""
            try {{
                $diskImage = Get-DiskImage -ImagePath '{safe_path}'
                
                if ($diskImage -and $diskImage.Attached) {{
                    $disk = $diskImage | Get-Disk
                    if (-not $disk) {{ throw "Attached VHD found, but Get-Disk returned null." }}
                    
                    $partitions = @($disk | Get-Partition | Where-Object {{ $_.Type -ne 'Recovery' -and $_.Type -ne 'System' -and $_.DriveLetter }})
                    
                    if ($partitions.Count -gt 0) {{
                        if ($partitions.Count -gt 1) {{
                            [Console]::Error.WriteLine("Warning: Multiple partitions are currently mounted for '{safe_path}'. Returning the first one.")
                        }}
                        
                        $volume = $partitions[0] | Get-Volume
                        if (-not $volume) {{ throw "Get-Volume returned null." }}
                        
                        $volume.DriveLetter | ConvertTo-Json -Compress
                    }} else {{
                        "null"
                    }}
                }} else {{
                    "null"
                }}
            }} catch {{
                [Console]::Error.WriteLine("드라이브 문자 추출 실패: $($_.Exception.Message)")
                exit 1
            }}
        """).strip()
        
        try:
            result = self._run_powershell_script(script)
            if not result:
                return None
                
            parsed_letter = json.loads(result)
            if parsed_letter and isinstance(parsed_letter, str):
                return f"{parsed_letter}:"
            
            return None
            
        except json.JSONDecodeError as e:
            print(f"[-] JSON 파싱 실패: {e}\n원본 데이터: {result}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[-] {e}", file=sys.stderr)
            return None

    def _escape_path(self, path: str) -> str:
        return path.replace("'", "''")