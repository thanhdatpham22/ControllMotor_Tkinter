from pathlib import Path

from vm_sensor.services.image_source_service import ImageFolderService


def test_load_folder_returns_false_for_missing_directory(tmp_path: Path) -> None:
    service = ImageFolderService()

    success, message = service.load_folder(str(tmp_path / "missing_images"))

    assert success is False
    assert "Folder not found" in message
