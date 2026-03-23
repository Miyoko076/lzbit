import sys
import subprocess
import time
from pathlib import Path

from lzbit.modules import VhdManager, BitLockerManager
from lzbit.modules.bitlocker_manager import BitLockerLockStatus, BitLockerProtectionStatus

def handle(args):
    """VHD를 시스템에 연결하고 BitLocker 외부 키 보호기(BEK)를 추가하여 암호화를 시작합니다."""
    vhd_path = Path(args.vhd_path).resolve()
    
    print(f"[*] 암호화 셋업을 시작합니다: {vhd_path}")
    
    vhd_manager = VhdManager()
    bitlocker_manager = BitLockerManager()
    
    if not vhd_manager.is_vhd_attached(str(vhd_path)):
        print("[*] VHD가 연결되어 있지 않아 마운트(Attach)를 시도합니다...")
        vhd_manager.mount_vhd(str(vhd_path))
    
    device_ids = vhd_manager.get_volume_device_ids(str(vhd_path))
    if not device_ids:
        print("[-] 에러: VHD가 연결되었으나 볼륨 ID를 찾을 수 없습니다. 파티션이 생성되지 않은 VHD일 수 있습니다.")
        sys.exit(1)
        
    device_id = device_ids[0]

    drive_letter = vhd_manager.get_drive_letter_for_vhd(str(vhd_path))
    display_target = drive_letter if drive_letter else device_id
    print(f"[*] 대상 볼륨 확인됨: {display_target}")

    try:
        protection_status = bitlocker_manager.get_protection_status(device_id)
    except Exception as e:
        print(f"[-] 에러: 볼륨 보호 상태를 확인하는 중 예기치 않은 오류 발생: {e}")
        sys.exit(1)

    if protection_status == BitLockerProtectionStatus.ERROR:
        print("[-] 에러: 볼륨의 보호 상태를 확인할 수 없습니다.")
        sys.exit(1)

    try:
        lock_status = bitlocker_manager.get_lock_status(device_id)
    except Exception as e:
        print(f"[-] 에러: 볼륨 잠금 상태(lock status)를 확인하는 중 오류 발생: {e}")
        sys.exit(1)

    if lock_status == BitLockerLockStatus.LOCKED:
        print("[-] 에러: 볼륨이 잠겨있습니다. 새로운 키를 추가하거나 암호화하려면 먼저 'unlock' 명령어로 잠금을 해제하세요.")
        sys.exit(1)
    elif lock_status == BitLockerLockStatus.ERROR:
        print("[-] 에러: 볼륨의 잠금 상태를 확인할 수 없습니다.")
        sys.exit(1)

    try:
        percent = bitlocker_manager.get_encryption_percentage(device_id)
    except Exception as e:
        print(f"[-] 에러: 암호화 진행률을 확인하는 중 예기치 않은 오류 발생: {e}")
        sys.exit(1)

    is_already_encrypted = False

    if 0 < percent < 100:
        print(f"[-] 에러: 볼륨({display_target})은 현재 암호화 또는 복호화가 진행 중입니다. (진행률: {percent}%)\n완료 후 다시 시도해 주세요.")
        sys.exit(1)
    elif percent == 100 and protection_status == BitLockerProtectionStatus.PROTECTED:
        print(f"[*] 볼륨({display_target})은 이미 암호화되어 있습니다. 추가 보조용 BEK 키를 생성합니다.")
        is_already_encrypted = True
    elif percent == 0 and protection_status == BitLockerProtectionStatus.UNPROTECTED:
        print(f"[*] 볼륨({display_target})은 일반 볼륨입니다. 최초 암호화를 준비합니다.")
       
    vhd_dir = vhd_path.parent
    
    try:
        bek_path_str = bitlocker_manager.encrypt_volume(device_id, str(vhd_dir))
        bek_path = Path(bek_path_str) if bek_path_str else None
        
        if bek_path and bek_path.exists():
            subprocess.run(["attrib", "-s", "-h", str(bek_path)], creationflags=subprocess.CREATE_NO_WINDOW)
            
            print(f"[+] 성공적으로 BEK 파일이 생성되었습니다: {bek_path}")
            print("[!] 보안을 위해 'crypbek' 명령어로 이 BEK 파일을 AES로 암호화할 것을 권장합니다.")
            
            if not is_already_encrypted:
                print(f"[*] BitLocker 암호화 진행률을 모니터링합니다. (데이터 크기에 따라 시간이 걸릴 수 있습니다.)")
                while True:
                    try:
                        current_percent = bitlocker_manager.get_encryption_percentage(device_id)
                    except Exception as e:
                        print(f"\n[-] 에러: 모니터링 중 볼륨 상태를 읽을 수 없습니다. 상세: {e}")
                        sys.exit(1)
                    
                    print(f"\r[*] 암호화 진행 중... (현재 암호화 비율: {current_percent:>3}%)", end="", flush=True)
                    
                    if current_percent == 100:
                        print(f"\n[+] 암호화가 100% 완료되었습니다!")
                        break
                        
                    time.sleep(1)

        else:
            print("[-] 명령은 수행되었으나 반환된 경로에서 BEK 파일을 찾을 수 없습니다.")
            sys.exit(1)
            
    except Exception as e:
        print(f"[-] 암호화(또는 키 추가) 실패: {e}")
        sys.exit(1)