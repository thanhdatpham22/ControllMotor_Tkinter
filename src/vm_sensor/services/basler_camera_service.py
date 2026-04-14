from dataclasses import dataclass
import numpy as np
from vm_sensor.utils.frame_utils import build_placeholder_frame
try:
    from pypylon import pylon
except ImportError:  # pragma: no cover - optional runtime dependency
    pylon = None


@dataclass(slots=True)
class BaslerDeviceInfo:
    display_name: str
    serial_number: str
    model_name: str
    ip_address: str = ""


class BaslerCameraService:
    def __init__(self) -> None:
        self.camera = None
        self.converter = None
        self.connected_device: BaslerDeviceInfo | None = None
        self.last_frame = build_placeholder_frame("Basler camera offline")
        self.status_message = self.sdk_status()

    def sdk_status(self) -> str:
        if pylon is None:
            return "Basler SDK not ready. Install pypylon to enable Basler Vision cameras."
        return "Basler SDK ready."

    def list_devices(self) -> tuple[list[BaslerDeviceInfo], str]:
        if pylon is None:
            return [], self.sdk_status()

        try:
            factory = pylon.TlFactory.GetInstance()
            devices = factory.EnumerateDevices()
        except Exception as exc:  # pragma: no cover - hardware dependent
            return [], f"Basler device scan failed: {exc}"

        found_devices: list[BaslerDeviceInfo] = []
        for device in devices:
            serial_number = self._safe_get(device, "GetSerialNumber")
            model_name = self._safe_get(device, "GetModelName")
            friendly_name = self._safe_get(device, "GetFriendlyName")
            ip_address = self._safe_get(device, "GetIpAddress")
            display_name = friendly_name or model_name or serial_number or "Basler device"
            if serial_number:
                display_name = f"{display_name} [{serial_number}]"

            found_devices.append(
                BaslerDeviceInfo(
                    display_name=display_name,
                    serial_number=serial_number,
                    model_name=model_name,
                    ip_address=ip_address,
                )
            )

        if not found_devices:
            return [], "No Basler camera found."

        return found_devices, f"Found {len(found_devices)} Basler camera(s)."

    def connect(self, serial_number: str | None = None) -> tuple[bool, str]:
        self.release()

        if pylon is None:
            self.last_frame = build_placeholder_frame("Basler SDK is missing")
            self.status_message = self.sdk_status()
            return False, self.status_message

        try:
            factory = pylon.TlFactory.GetInstance()
            device = None
            for candidate in factory.EnumerateDevices():
                candidate_serial = self._safe_get(candidate, "GetSerialNumber")
                if serial_number is None or candidate_serial == serial_number:
                    device = candidate
                    break

            if device is None:
                self.last_frame = build_placeholder_frame("Basler device not found")
                self.status_message = "Selected Basler camera was not found."
                return False, self.status_message

            self.camera = pylon.InstantCamera(factory.CreateDevice(device))
            self.camera.Open()
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

            self.converter = pylon.ImageFormatConverter()
            self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

            model_name = self._safe_get(device, "GetModelName")
            friendly_name = self._safe_get(device, "GetFriendlyName")
            actual_serial = self._safe_get(device, "GetSerialNumber")
            ip_address = self._safe_get(device, "GetIpAddress")
            display_name = friendly_name or model_name or actual_serial or "Basler device"
            if actual_serial:
                display_name = f"{display_name} [{actual_serial}]"

            self.connected_device = BaslerDeviceInfo(
                display_name=display_name,
                serial_number=actual_serial,
                model_name=model_name,
                ip_address=ip_address,
            )
            self.status_message = f"Connected to {display_name}."

            self.read_frame()
            return True, self.status_message
        except Exception as exc:  # pragma: no cover - hardware dependent
            self.release()
            self.last_frame = build_placeholder_frame("Basler connection failed")
            self.status_message = f"Basler connection failed: {exc}"
            return False, self.status_message

    def read_frame(self) -> np.ndarray:
        if pylon is None or self.camera is None:
            self.last_frame = build_placeholder_frame("Basler camera offline")
            return self.last_frame.copy()

        if not self.camera.IsOpen() or not self.camera.IsGrabbing():
            self.last_frame = build_placeholder_frame("Basler camera is not grabbing")
            return self.last_frame.copy()

        grab_result = None
        try:
            grab_result = self.camera.RetrieveResult(
                2000,
                pylon.TimeoutHandling_ThrowException,
            )
            if grab_result.GrabSucceeded():
                converted = self.converter.Convert(grab_result)
                frame = converted.GetArray()
                self.last_frame = frame
                return frame.copy()

            error_text = grab_result.GetErrorDescription()
            self.last_frame = build_placeholder_frame("Basler frame grab failed")
            self.status_message = f"Basler frame error: {error_text}"
            return self.last_frame.copy()
        except Exception as exc:  # pragma: no cover - hardware dependent
            self.last_frame = build_placeholder_frame("Basler frame timeout")
            self.status_message = f"Basler frame read failed: {exc}"
            return self.last_frame.copy()
        finally:
            if grab_result is not None:
                grab_result.Release()

    def release(self) -> None:
        if self.camera is not None:
            try:
                if self.camera.IsGrabbing():
                    self.camera.StopGrabbing()
            except Exception:
                pass

            try:
                if self.camera.IsOpen():
                    self.camera.Close()
            except Exception:
                pass

        self.camera = None
        self.converter = None
        self.connected_device = None

    @staticmethod
    def _safe_get(device, method_name: str) -> str:
        getter = getattr(device, method_name, None)
        if getter is None:
            return ""

        try:
            return str(getter())
        except Exception:
            return ""
