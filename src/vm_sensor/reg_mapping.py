class RegisterMap:
    # ===== COILS =====
    COIL_HOME = 0
    COIL_SET_POINT = 1
    COIL_EMERGENCY = 2
    COIL_STOP = 4

    COIL_JOG = {
        ("x", -1): 8,
        ("x", 1): 9,
        ("y", 1): 10,
        ("y", -1): 11,
        ("z", 1): 12,
        ("z", -1): 13,
    }

    # ===== INPUT REGISTERS =====
    REG_POS = {
        "x": 0,
        "y": 3,
        "z": 6,
    }

    # ===== HOLDING REGISTERS =====
    REG_TARGET = {
        "x": 0,
        "y": 3,
        "z": 6,
    }

    REG_SPEED = {
        "x": 1,
        "y": 4,
        "z": 7,
    }