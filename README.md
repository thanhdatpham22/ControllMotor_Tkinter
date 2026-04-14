# VM Sensor

Simple Python project scaffold for a Tkinter desktop UI that combines:

- realtime camera preview
- source switch: camera or image folder
- optional Basler Vision camera input
- motor control tab scaffold for RS232 / Modbus RTU
- one-click capture
- segmentation preview
- image tuning controls
- save options for image / YOLO / JSON annotations

## Project layout

```text
VM_Sensor/
|-- assets/
|   `-- models/
|-- outputs/
|   `-- captures/
|-- src/
|   `-- vm_sensor/
|       |-- services/
|       |-- ui/
|       `-- utils/
|-- tests/
|-- pyproject.toml
|-- requirements.txt
`-- run.py
```

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Optional YOLO support

If you want real YOLO segmentation:

```bash
pip install ultralytics
```

Then load a segmentation model from the **Settings** tab, for example a `yolo11n-seg.pt`
or another `.pt` segmentation model.

## Optional Basler Vision support

If you want to connect a Basler Vision camera:

```bash
pip install pypylon
```

Then in the **Settings** tab:

- choose `Camera` as source
- choose `Basler Vision` as camera backend
- click `Refresh Devices`
- select the detected device
- click `Apply Camera` or `Apply Source`

## Optional motor RS232 support

If you want to start wiring the motor controller over RS232 / Modbus RTU:

```bash
pip install pyserial
```

The **Motor** tab now includes:

- COM port connect / disconnect
- Start / Stop / Home buttons
- Jog controls for X / Y / Z
- speed controls for X / Y / Z
- a live camera preview for the current camera point
- a command log area

The communication service is a scaffold for you to extend in:

- `src/vm_sensor/services/motor_service.py`

## Notes

- The app falls back to a contour-based segmentation demo when no YOLO model is loaded.
- Basler support is optional and only works when `pypylon` is installed and a Basler camera is available.
- Motor RS232 support is scaffolded and currently sends mock-safe placeholder payloads until you replace them with your Modbus RTU frames.
- Captures are stored in `outputs/captures/`.
- Save options support image only, image + YOLO `.txt`, or image + JSON metadata.
