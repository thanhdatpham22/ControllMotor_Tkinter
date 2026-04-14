from vm_sensor.services.basler_camera_service import BaslerCameraService


def test_basler_service_lists_devices_without_crashing() -> None:
    service = BaslerCameraService()

    devices, message = service.list_devices()

    assert isinstance(devices, list)
    assert isinstance(message, str)
