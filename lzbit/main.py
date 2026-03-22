import argparse
import sys
import ctypes
from pathlib import Path

from lzbit.commands import encrypt, crypbek, unlock, lock, decrypt

class AlwaysHelpParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs['add_help'] = False
        super().__init__(*args, **kwargs)
        self.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    def error(self, message):
        print(f"invalid argument: {message}", file=sys.stderr)
        
        if len(sys.argv) > 1:
            subcommand = sys.argv[1]
            subparsers = next((a for a in self._actions if isinstance(a, argparse._SubParsersAction)), None)
            
            if subparsers and subcommand in subparsers.choices:
                subparsers.choices[subcommand].print_usage(sys.stderr)
                sys.exit(2)
        
        self.print_usage(sys.stderr)
        sys.exit(2)

def is_admin() -> bool:
    """Checks if the current user has administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def main():
    parser = AlwaysHelpParser(
        description="[ Lazy BitLocker Decryptor CLI ]",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=AlwaysHelpParser)

    encrypt_parser = subparsers.add_parser("encrypt", help="VHD를 암호화하고 BEK 파일을 생성합니다.", formatter_class=argparse.RawTextHelpFormatter)
    encrypt_parser.add_argument("vhd_path", metavar="<VHD_FILE>", help="대상 VHD/VHDX '파일'의 절대/상대 경로\n(예: C:\\vhds\\secret.vhdx)")

    crypbek_parser = subparsers.add_parser("crypbek", help="BEK 파일을 aes 파일로 암호화합니다.", formatter_class=argparse.RawTextHelpFormatter)
    crypbek_parser.add_argument("bek_path", metavar="<BEK_FILE>", help="원본 .BEK '파일'의 절대/상대 경로\n(예: C:\\vhds\\1234-5678.BEK)")
    crypbek_parser.add_argument("-m", "--method", choices=["pass", "key", "pipe"], default="pass", help="인증 방식 (pass, key, pipe / 기본값: pass)")

    unlock_parser = subparsers.add_parser("unlock", help="BEK 또는 aes 파일로 VHD를 해제합니다.", formatter_class=argparse.RawTextHelpFormatter)
    unlock_parser.add_argument("vhd_path", metavar="<VHD_FILE>", help="대상 VHD/VHDX '파일'의 절대/상대 경로")
    unlock_parser.add_argument("key_path", metavar="<KEY_FILE>", help="잠금 해제에 사용할 키 파일(.bek 또는 .aes)의 경로")
    unlock_parser.add_argument("-m", "--method", choices=["pass", "key", "pipe"], default="pass", help="AES 인증 방식 (BEK 사용 시 무시됨)")

    lock_parser = subparsers.add_parser("lock", help="VHD를 안전하게 잠그고 마운트를 해제합니다.", formatter_class=argparse.RawTextHelpFormatter)
    lock_parser.add_argument("vhd_path", metavar="<VHD_FILE>", help="대상 VHD/VHDX '파일'의 절대/상대 경로")

    decrypt_parser = subparsers.add_parser("decrypt", help="VHD의 BitLocker 암호화를 완전히 해제합니다(일반 볼륨으로 전환).", formatter_class=argparse.RawTextHelpFormatter)
    decrypt_parser.add_argument("vhd_path", metavar="<VHD_FILE>", help="대상 VHD/VHDX '파일'의 절대/상대 경로")

    args = parser.parse_args()

    if args.command in ["encrypt", "unlock", "lock", "decrypt"]:
        if not is_admin():
            print("[-] 에러: VHD 마운트 및 BitLocker 제어를 위해 터미널을 '관리자 권한'으로 실행해 주세요.")
            sys.exit(1)
            
        vhd_path = Path(args.vhd_path).resolve()
        
        if vhd_path.suffix.lower() not in [".vhd", ".vhdx"]:
            print(f"[-] 에러: 대상 파일은 VHD 또는 VHDX 확장자여야 합니다.")
            print(f"    입력된 파일: {args.vhd_path}")
            sys.exit(1)
            
        if not vhd_path.is_file():
            print(f"[-] 에러: 대상 VHD/VHDX 파일을 찾을 수 없습니다.")
            print(f"    경로: {vhd_path}")
            sys.exit(1)

    if args.command in ["crypbek", "unlock"]:
        key_path_str = args.bek_path if args.command == "crypbek" else args.key_path
        key_path = Path(key_path_str).resolve()
        
        valid_exts = [".bek"] if args.command == "crypbek" else [".bek", ".aes"]

        if key_path.suffix.lower() not in valid_exts:
            print(f"[-] 에러: 대상 키 파일은 {' 또는 '.join(valid_exts)} 확장자여야 합니다.")
            print(f"    입력된 파일: {key_path_str}")
            sys.exit(1)

        if not key_path.is_file():
            print(f"[-] 에러: 키 파일을 찾을 수 없습니다.")
            print(f"    경로: {key_path}")
            sys.exit(1)

    if args.command == "encrypt":
        encrypt.handle(args)
    elif args.command == "crypbek":
        crypbek.handle(args)
    elif args.command == "unlock":
        unlock.handle(args)
    elif args.command == "lock":
        lock.handle(args)
    elif args.command == "decrypt":
        decrypt.handle(args)

if __name__ == "__main__":
    main()