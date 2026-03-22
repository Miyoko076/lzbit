import sys
import getpass
import subprocess
import textwrap
import base64

class InputManager:
    def get_password(self) -> str:
        """Prompts the user for a standard text password and encodes it safely in Base64."""
        try:
            raw_pass = getpass.getpass("[?] 비밀번호를 입력하세요: ")
        except KeyboardInterrupt:
            print("\n[!] 입력이 취소되었습니다. (Ctrl+C 입력됨)") 
            return None
        
        if not raw_pass:
            return None
            
        encoded_pass = base64.b64encode(raw_pass.encode('utf-8')).decode('utf-8')
        return encoded_pass

    def get_key_combination(self) -> str | None:
        """Captures a single key combination using PowerShell and returns it as a formatted string."""
        print("[*] 암호로 사용할 키 조합을 누르세요 (예: Ctrl + Shift + A).")
        print("[!] 주의: Ctrl, Alt, Shift와 같은 수식키는 단독으로 사용할 수 없으며, 다른 키와 조합해야 합니다.")
        print("[*] 시스템 입력기를 불러오는 중입니다. 잠시만 기다려주세요...", flush=True)

        script = textwrap.dedent("""
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

            [Console]::TreatControlCAsInput = $true

            Write-Output "READY"

            while ([System.Console]::KeyAvailable) {
                $null = [System.Console]::ReadKey($true)
            }

            $keyInfo = [System.Console]::ReadKey($true)
            $isCtrl = [int]$keyInfo.Modifiers.HasFlag([System.ConsoleModifiers]::Control)
            $isAlt = [int]$keyInfo.Modifiers.HasFlag([System.ConsoleModifiers]::Alt)
            $isShift = [int]$keyInfo.Modifiers.HasFlag([System.ConsoleModifiers]::Shift)
            
            $keyName = $keyInfo.Key.ToString()
              
            if ($keyName -eq 'Escape' -or ($keyName -eq 'C' -and $isCtrl -eq 1)) {
                Write-Output "ABORT"
                exit 0
            }

            Write-Output "RESULT:${keyName}_${isCtrl}_${isAlt}_${isShift}"
        """).strip()

        encoded_script = base64.b64encode(script.encode('utf-16le')).decode('utf-8')
        command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded_script]

        p = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            encoding='utf-8', 
            errors='replace', 
            bufsize=1
        )
        
        try:
            for line in iter(p.stdout.readline, ''):
                line = line.strip()
                
                if line == "READY":
                    print("[*] (대기 중... 지금 키를 누르세요!)", flush=True)
                elif line == "ABORT":
                    print("\n[!] 입력이 취소되었습니다. (Esc 또는 Ctrl+C 입력됨)")
                    return None
                elif line.startswith("RESULT:"):
                    output = line.replace("RESULT:", "")
                    print("[+] 키 조합이 성공적으로 캡처되었습니다. (보안을 위해 조합 내용은 가려집니다)")
                    return output

            p.wait(timeout=1)
            if p.returncode != 0:
                raise Exception(f"PowerShell 실행 오류 (Exit Code {p.returncode})")
            
        finally:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    p.kill()
            
            if p.stdout: p.stdout.close()

        raise Exception("PowerShell 프로세스가 정상적으로 키를 캡처하지 못하고 종료되었습니다.")

    def get_from_pipe(self) -> str:
        """
        [-m pipe 모드] 
        표준 입력(stdin)으로 들어온 데이터를 바이트로 읽어 Base64 문자열로 인코딩하여 반환합니다.
        어떤 데이터(텍스트, 바이너리, 파일)가 들어와도 인코딩 에러 없이 안전한 키로 변환됩니다.
        """
        if sys.stdin.isatty():
            raise ValueError("파이프라인 입력이 감지되지 않았습니다. '명령어 | python main.py ... -m pipe' 형태로 사용하세요.")
        
        raw_bytes = sys.stdin.buffer.read().rstrip(b'\r\n')
        
        if not raw_bytes:
            raise ValueError("파이프라인으로 전달된 데이터가 비어있습니다.")

        b64_string = base64.b64encode(raw_bytes).decode('utf-8')
        
        print("[+] 파이프라인 데이터를 성공적으로 읽어 Base64 키로 변환했습니다.")
        return b64_string