import sys
from pathlib import Path

from lzbit.modules import VhdManager, BitLockerManager
from lzbit.modules.bitlocker_manager import BitLockerLockStatus, BitLockerProtectionStatus

def handle(args):
    """VHD를 안전하게 잠그고 시스템에서 마운트를 해제(Dismount)합니다."""
    vhd_path = Path(args.vhd_path).resolve()
    
    print(f"[*] 잠금 및 마운트 해제를 시도합니다: {vhd_path}")
    
    vhd_manager = VhdManager()
    bitlocker_manager = BitLockerManager()
    
    if not vhd_manager.is_vhd_attached(str(vhd_path)):
        print("[+] VHD가 이미 연결 해제(Detached)되어 있습니다. 작업을 종료합니다.")
        sys.exit(0)

    device_ids = vhd_manager.get_volume_device_ids(str(vhd_path))
    
    if device_ids:
        device_id = device_ids[0]
        
        drive_letter = vhd_manager.get_drive_letter_for_vhd(str(vhd_path))
        display_target = drive_letter if drive_letter else device_id
        
        print(f"[*] 대상 볼륨 확인됨: {display_target}")
        
        try:
            protection_status = bitlocker_manager.get_protection_status(device_id)

            if protection_status == BitLockerProtectionStatus.ERROR:
                print("[-] 경고: 볼륨의 보호 상태를 확인할 수 없습니다. 안전을 위해 바로 마운트 해제를 시도합니다.")
            
            elif protection_status == BitLockerProtectionStatus.UNPROTECTED:
                print("[*] 이 VHD는 BitLocker 암호화가 적용되지 않은 일반 볼륨입니다. 잠금 단계를 건너뜁니다.")
            
            else:
                lock_status = bitlocker_manager.get_lock_status(device_id)

                if lock_status == BitLockerLockStatus.UNLOCKED:
                    print(f"[*] BitLocker 볼륨이 열려있습니다. 잠금을 시도합니다. (열려있는 파일 핸들 강제 해제)")

                    bitlocker_manager.lock_volume(device_id)
                    print("[+] BitLocker 잠금 성공.")
                    
                elif lock_status == BitLockerLockStatus.LOCKED:
                    print("[*] BitLocker가 이미 잠겨있습니다.")
                    
                elif lock_status == BitLockerLockStatus.ERROR:
                    print("[-] 경고: 볼륨의 잠금 상태를 확인할 수 없습니다. 안전을 위해 바로 마운트 해제를 시도합니다.")

        except Exception as e:
            print(f"[-] 잠금 처리 중 예기치 않은 오류 발생: {e}")
            print("[*] 안전을 위해 VHD 물리적 연결 해제(Detach)를 강행합니다...")
            
    else:
        print("[*] 인식된 볼륨이 없습니다. 잠금 단계를 건너뛰고 바로 마운트 해제를 시도합니다.")

    try:
        vhd_manager.dismount_vhd(str(vhd_path))
        print(f"[+] 마운트가 해제(Detach)되었습니다! 이제 VHD 파일을 안전하게 이동할 수 있습니다.")
    except Exception as e:
        print(f"[-] VHD 마운트 해제(Detach) 실패: {e}")
        sys.exit(1)