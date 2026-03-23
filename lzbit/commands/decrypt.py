import sys
import time
from pathlib import Path

from lzbit.modules import VhdManager, BitLockerManager
from lzbit.modules.bitlocker_manager import BitLockerLockStatus, BitLockerProtectionStatus

def handle(args):
    """VHD의 BitLocker 암호화를 완전히 해제하고 일반 볼륨(NTFS)으로 되돌립니다."""
    vhd_path = Path(args.vhd_path).resolve()
    
    print(f"[*] 복호화 셋업을 시작합니다: {vhd_path}")
    
    vhd_manager = VhdManager()
    bitlocker_manager = BitLockerManager()
    
    if not vhd_manager.is_vhd_attached(str(vhd_path)):
        print("[*] VHD가 연결되어 있지 않아 마운트(Attach)를 시도합니다...")
        vhd_manager.mount_vhd(str(vhd_path))

    device_ids = vhd_manager.get_volume_device_ids(str(vhd_path))
    if not device_ids:
        print("[-] 에러: VHD가 연결되었으나 볼륨 ID를 찾을 수 없습니다.")
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
        print("[-] 에러: 볼륨이 잠겨있습니다. 'unlock' 명령어로 잠금을 해제한 뒤 다시 시도하세요.")
        sys.exit(1)
    elif lock_status == BitLockerLockStatus.ERROR:
        print("[-] 에러: 볼륨의 잠금 상태를 확인할 수 없습니다.")
        sys.exit(1)

    try:
        percent = bitlocker_manager.get_encryption_percentage(device_id)
    except Exception as e:
        print(f"[-] 에러: 암호화 진행률을 확인하는 중 예기치 않은 오류 발생: {e}")
        sys.exit(1)

    if 0 < percent < 100:
        print(f"[-] 에러: 볼륨({display_target})은 현재 암호화 또는 복호화가 진행 중입니다. (진행률: {percent}%)\n완료 후 다시 시도해 주세요.")
        sys.exit(1)
    elif percent == 0 and protection_status == BitLockerProtectionStatus.UNPROTECTED:
        print(f"[+] 볼륨({display_target})은 BitLocker가 적용되지 않은 일반 볼륨이거나 완전히 복호화되어 있습니다. (작업 건너뜀)")
        sys.exit(0)

    try:
        print(f"[*] BitLocker 복호화를 시작합니다. (데이터 크기에 따라 시간이 걸릴 수 있습니다.)")
        bitlocker_manager.decrypt_volume(device_id)
        
        while True:
            try:
                current_percent = bitlocker_manager.get_encryption_percentage(device_id)
            except Exception as e:
                print(f"\n[-] 에러: 모니터링 중 볼륨 상태를 읽을 수 없습니다. 상세: {e}")
                sys.exit(1)
            
            print(f"\r[*] 복호화 진행 중... (남은 암호화 비율: {current_percent:>3}%)", end="", flush=True)
            
            if current_percent == 0:
                print(f"\n[+] 복호화가 100% 완료되어 일반 볼륨으로 전환되었습니다!")
                break
                
            time.sleep(1)
            
    except Exception as e:
        print(f"\n[-] 복호화 과정 실패: {e}")
        sys.exit(1)