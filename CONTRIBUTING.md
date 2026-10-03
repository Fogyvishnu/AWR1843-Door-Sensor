# Contributing to the TI AWR1843 Door Sensor Project

Thank you for your interest in contributing to the **TI AWR1843 Standalone Door Sensor** project! We welcome contributions from embedded engineers, radar scientists, and IoT developers.

---

## 🛠️ Development Environment Setup

### 1. Python Toolchain Setup
```bash
git clone https://github.com/Fogyvishnu/AWR1843-Door-Sensor.git
cd AWR1843-Door-Sensor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package in editable mode with development dependencies
pip install -e ".[dev,mqtt]"
```

### 2. Running Automated Tests
Before submitting a PR, verify all unit tests pass:
```bash
# Run Python test suite
python tests/run_tests.py

# Run C firmware tests (if GCC/Clang is installed)
cd firmware/tests
make
```

### 3. Firmware Build Environment (TI mmWave SDK)
To compile the embedded multi-core MetaImage:
- Install **TI mmWave SDK 03.06.02.00-LTS** in `C:\ti`.
- Install **Code Composer Studio (CCS) v10+** or standalone TI CGT compilers:
  - ARM Compiler: `ti-cgt-arm_16.9.6.LTS`
  - C6000 DSP Compiler: `ti-cgt-c6000_8.3.3`
  - XDC Tools: `xdctools_3_50_08_24_core`
- Execute:
  ```cmd
  firmware\build\build_firmware.bat
  ```

---

## 📋 Pull Request Process

1. **Branching**: Fork the repo and create a feature branch (`git checkout -b feature/awesome-addition`).
2. **Code Standards**:
   - **C Code**: Follow MISRA C guidelines and avoid dynamic memory allocations (`malloc`/`free`) on the radar data path.
   - **Python Code**: Adhere to PEP 8 standards. Format using `black` and check with `flake8`.
3. **Commit Messages**: Use Conventional Commits formatting:
   - `feat: Add MQTT TLS authentication`
   - `fix: Correct boundary clipping in spatial gating`
   - `docs: Update radome wall thickness calculations`
4. **Testing**: Add unit tests for any new features or bug fixes under `tests/` or `firmware/tests/`.
