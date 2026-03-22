import wmi
from enum import Enum
from pathlib import Path

class BitLockerLockStatus(Enum):
    UNLOCKED = "UNLOCKED"
    LOCKED = "LOCKED"
    ERROR = "ERROR"

class BitLockerProtectionStatus(Enum):
    UNPROTECTED = "UNPROTECTED"
    PROTECTED = "PROTECTED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"

class BitLockerManager:
    def __init__(self):
        """Initializes the WMI connection to the BitLocker namespace."""
        self.namespace = r"root\CIMV2\Security\MicrosoftVolumeEncryption"
        self.wmi_conn = wmi.WMI(namespace=self.namespace)

    def _get_volume_instance(self, device_id: str):
        """Retrieves the WMI instance for a specific BitLocker volume using DeviceID.
        """
        target_id = device_id.strip()
        all_volumes = self.wmi_conn.Win32_EncryptableVolume()
        
        for vol in all_volumes:
            if vol.DeviceID == target_id:
                return vol
                
        return None

    def get_protection_status(self, device_id: str) -> BitLockerProtectionStatus:
        """Returns the real-time protection status of the volume as an Enum."""
        try:
            volume = self._get_volume_instance(device_id)
            
            if not volume:
                return BitLockerProtectionStatus.UNPROTECTED
                
            status_tuple = volume.GetProtectionStatus()
            protection_status = status_tuple[0]
            return_code = status_tuple[-1]
            
            if return_code != 0:
                return BitLockerProtectionStatus.ERROR
                
            if protection_status == 0:
                return BitLockerProtectionStatus.UNPROTECTED
            elif protection_status == 1:
                return BitLockerProtectionStatus.PROTECTED
            elif protection_status == 2:
                return BitLockerProtectionStatus.UNKNOWN
            else:
                return BitLockerProtectionStatus.ERROR
                
        except wmi.x_wmi as e:
            return BitLockerProtectionStatus.ERROR
            
        except Exception as e:
            return BitLockerProtectionStatus.ERROR

    def get_lock_status(self, device_id: str) -> BitLockerLockStatus:
        """Returns the lock status of the volume as an Enum."""
        try:
            volume = self._get_volume_instance(device_id)
            if not volume:
                return BitLockerLockStatus.ERROR
                
            status_tuple = volume.GetLockStatus()
            lock_status = status_tuple[0]
            return_code = status_tuple[-1]
            
            if return_code != 0:
                return BitLockerLockStatus.ERROR
                
            if lock_status == 0:
                return BitLockerLockStatus.UNLOCKED
            elif lock_status == 1:
                return BitLockerLockStatus.LOCKED
            else:
                return BitLockerLockStatus.ERROR
                
        except wmi.x_wmi as e:
            return BitLockerLockStatus.ERROR
            
        except Exception as e:
            return BitLockerLockStatus.ERROR

    def get_encryption_percentage(self, device_id: str) -> int:
        """
        Returns the current encryption percentage of the volume.
        """
        volume = self._get_volume_instance(device_id)
        
        if not volume:
            return 0
            
        status_tuple = volume.GetConversionStatus(PrecisionFactor=0)
        return_code = status_tuple[-1]

        if return_code != 0:
            return 0
            
        conversion_status = status_tuple[0]
        encryption_percentage = status_tuple[2]
        
        if conversion_status == 1:
            return 100
        elif conversion_status == 0:
            return 0
            
        return encryption_percentage

    def encrypt_volume(self, device_id: str, target_directory: str) -> str:
        """
        Adds an external key protector, saves the .bek file, and starts encryption.
        If the volume is already encrypted, it simply adds the new key and skips the encryption start.
        """
        volume = self._get_volume_instance(device_id)
        if not volume:
            raise Exception(f"Volume not found or not applicable for BitLocker: {device_id}")

        result, protector_id = volume.ProtectKeyWithExternalKey()
        if result != 0:
            raise Exception(f"Failed to create new key protector. WMI return code: 0x{(result & 0xFFFFFFFF):08X}")

        Path(target_directory).mkdir(parents=True, exist_ok=True)

        result, = volume.SaveExternalKeyToFile(VolumeKeyProtectorID=protector_id, Path=target_directory)
        if result != 0:
            raise Exception(f"Failed to save new key to file. WMI return code: 0x{result:X}")

        final_file_path = ""
        file_name, result_code = volume.GetExternalKeyFileName(VolumeKeyProtectorID=protector_id)
        
        if result_code == 0:
            actual_file_path = Path(target_directory) / file_name
            final_file_path = str(actual_file_path.resolve())
            print(f"[+] Success: Key saved to {final_file_path}")
        else:
            raise Exception(f"Failed to retrieve key file name. WMI return code: 0x{(result_code & 0xFFFFFFFF):08X}")

        status_tuple = volume.GetConversionStatus(PrecisionFactor=0)
        conversion_return_code = status_tuple[-1]

        if conversion_return_code == 0:
            conversion_status = status_tuple[0]
            if conversion_status in (1, 2):
                print("[*] Volume is already encrypted (or encrypting). A new key has been added successfully.")
            else:
                encrypt_result, = volume.Encrypt()
                if encrypt_result != 0:
                    raise Exception(f"Failed to start encryption. WMI return code: 0x{(encrypt_result & 0xFFFFFFFF):08X}")
                print("[*] Encryption process started successfully.")
        else:
            print(f"[-] Warning: Could not check conversion status (Code: 0x{(conversion_return_code & 0xFFFFFFFF):08X}). Skipping Encrypt() call.")

        return final_file_path

    def unlock_volume(self, device_id: str, external_key: bytes) -> int:
        """
        Unlocks the volume using a raw 32-byte external key array.
        """
        volume = self._get_volume_instance(device_id)
        if not volume:
            raise Exception(f"Volume not found or not applicable for BitLocker: {device_id}")

        key_list = list(external_key)
        
        result, = volume.UnlockWithExternalKey(ExternalKey=key_list)
        
        if result != 0:
            raise Exception(f"Failed to unlock volume for {device_id}. WMI return code: 0x{(result & 0xFFFFFFFF):08X}")
            
        return result

    def lock_volume(self, device_id: str, force_dismount: bool = True) -> int:
        """
        Locks the volume and optionally forces a dismount.
        """
        volume = self._get_volume_instance(device_id)
        if not volume:
            raise Exception(f"Volume not found or not applicable for BitLocker: {device_id}")

        result, = volume.Lock(ForceDismount=force_dismount)
        
        if result != 0:
            # 0x80310001 (FVE_E_NOT_ENCRYPTED): 암호화되지 않은 볼륨
            # 0x80310021 (FVE_E_PROTECTION_DISABLED): 보호가 비활성화된 볼륨
            raise Exception(f"Failed to lock volume for {device_id}. WMI return code: 0x{(result & 0xFFFFFFFF):08X}")
            
        return result

    def decrypt_volume(self, device_id: str) -> int:
        """
        Starts the decryption process for the volume.
        """
        volume = self._get_volume_instance(device_id)
        if not volume:
            raise Exception(f"Volume not found or not applicable for BitLocker: {device_id}")

        result, = volume.Decrypt()
        
        if result != 0:
            # 0x80310000 (FVE_E_LOCKED_VOLUME): 볼륨이 잠겨있어 복호화 불가
            # 0x80310029 (FVE_E_AUTOUNLOCK_ENABLED): 자동 잠금 해제가 켜져 있어 불가
            raise Exception(f"Failed to start decryption for {device_id}. WMI return code: 0x{(result & 0xFFFFFFFF):08X}")
            
        return result