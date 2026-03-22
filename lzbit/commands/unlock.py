import sys
from pathlib import Path

from lzbit.modules import (
    VhdManager, 
    BitLockerManager, 
    DislockerManager, 
    CryptoManager, 
    InputManager
)
from lzbit.modules.bitlocker_manager import BitLockerLockStatus, BitLockerProtectionStatus

def handle(args):
    """BEK 또는 AES 파일로 VHD의 BitLocker 잠금을 해제합니다."""
    vhd_path = Path(args.vhd_path).resolve()
    key_path = Path(args.key_path).resolve()
    
    print(f"[*] 잠금 해제를 시도합니다: {vhd_path}")
    
    vhd_manager = VhdManager()
    bitlocker_manager = BitLockerManager()
    dislocker_manager = DislockerManager()
    crypto_manager = CryptoManager()
    input_manager = InputManager()
    
    ext = key_path.suffix.lower()
    raw_key = None
    secret_string = None
    
    try:
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
        
        protection_status = bitlocker_manager.get_protection_status(device_id)
        
        if protection_status == BitLockerProtectionStatus.ERROR:
            print("[-] 에러: 볼륨의 보호 상태를 확인할 수 없습니다.")
            sys.exit(1)
        elif protection_status == BitLockerProtectionStatus.UNPROTECTED:
            print(f"[+] 볼륨({display_target})은 BitLocker가 적용되지 않은 일반 볼륨입니다. (작업 건너뜀)")
            sys.exit(0)

        lock_status = bitlocker_manager.get_lock_status(device_id)
        
        if lock_status == BitLockerLockStatus.UNLOCKED:
            print(f"[+] 볼륨({display_target})은 이미 잠금 해제되어 있습니다. (작업 건너뜀)")
            sys.exit(0)
        elif lock_status == BitLockerLockStatus.ERROR:
            print("[-] 에러: 볼륨의 잠금 상태를 확인할 수 없습니다.")
            sys.exit(1)

        if ext == '.aes':
            print(f"[*] AES 파일 감지. (인증 방식: {args.method})")
            if args.method == 'pass':
                secret_string = input_manager.get_password()
            elif args.method == 'key':
                secret_string = input_manager.get_key_combination()
            elif args.method == 'pipe':
                secret_string = input_manager.get_from_pipe()
                
            if not secret_string:
                print("[-] 키 입력이 취소되었거나 유효하지 않습니다.")
                sys.exit(0)
            
            raw_key = crypto_manager.load_and_decrypt(str(key_path), secret_string)
            
        elif ext == '.bek':
            print("[*] BEK 파일 감지. 인증 절차를 건너뜁니다...")
            raw_key = dislocker_manager.get_key_from_bek(str(key_path))
            
        else:
            print(f"[-] 지원하지 않는 키 형식입니다: {ext}")
            sys.exit(1)
            
        if not raw_key:
            print("[-] 에러: 키 데이터를 정상적으로 추출하지 못했습니다.")
            sys.exit(1)

        print("[*] 키 추출/복호화 성공. BitLocker 잠금 해제 중...")
        bitlocker_manager.unlock_volume(device_id, raw_key)
        
        final_letter = vhd_manager.get_drive_letter_for_vhd(str(vhd_path))
        success_target = final_letter if final_letter else device_id
        print(f"[+] 잠금 해제 성공! 이제 {success_target} 볼륨을 사용할 수 있습니다.")
        
    except Exception as e:
        print(f"[-] 잠금 해제 과정 실패: {e}")
        sys.exit(1)