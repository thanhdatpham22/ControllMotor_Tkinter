from vm_sensor.services.motor_service import MotorControllerService


def test_motor_service_mock_jog_updates_position() -> None:
    service = MotorControllerService()

    ok, _ = service.jog("x", 1, 2.5)

    assert ok is True
    assert service.snapshot()["positions"]["x"] == 2.5


def test_motor_service_set_all_speeds_updates_snapshot() -> None:
    service = MotorControllerService()

    ok, _ = service.set_all_speeds(12.0, 13.0, 14.0)
    speeds = service.snapshot()["speeds"]

    assert ok is True
    assert speeds["x"] == 12.0
    assert speeds["y"] == 13.0
    assert speeds["z"] == 14.0
