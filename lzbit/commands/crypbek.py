import sys
from pathlib import Path

from lzbit.modules import DislockerManager, CryptoManager, InputManager

def handle(args):
    """원본 BEK 파일을 읽어 사용자가 지정한 인증 방식으로 AES 암호화합니다."""
    bek_path = Path(args.bek_path).resolve()
    
    print(f"[*] BEK 파일을 AES로 암호화합니다: {bek_path} (모드: {args.method})")
    
    dislocker_manager = DislockerManager()
    input_manager = InputManager()
    crypto_manager = CryptoManager()
    
    try:
        if args.method == 'pass':
            secret_string = input_manager.get_password()
        elif args.method == 'key':
            secret_string = input_manager.get_key_combination()
        elif args.method == 'pipe':
            secret_string = input_manager.get_from_pipe()
            
        if not secret_string:
            print("[-] 키 입력이 취소되었거나 유효하지 않습니다.")
            sys.exit(0)
            
        raw_key = dislocker_manager.get_key_from_bek(str(bek_path))
        
        aes_path = bek_path.with_suffix('.aes')
        crypto_manager.encrypt_and_save(raw_key, secret_string, str(aes_path))
        
        print(f"[+] 변환 성공. AES 키가 저장되었습니다: {aes_path}")
        print("[-] 이제 원본 .bek 파일을 삭제하셔도 좋습니다.")
        
    except Exception as e:
        print(f"[-] 변환 실패: {e}")
        sys.exit(1)