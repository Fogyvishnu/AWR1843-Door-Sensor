@echo off
setlocal enabledelayedexpansion

echo ==============================================================================
echo   TI AWR1843BOOST Standalone Door Sensor - Automated Firmware Builder
echo ==============================================================================
echo.

REM 1. Setup SDK and Tools Paths
set MMWAVE_SDK_TOOLS_INSTALL_PATH=C:/ti
set MMWAVE_SDK_INSTALL_PATH=C:/ti/mmwave_sdk_03_06_02_00-LTS/packages
set MMWAVE_SDK_DEVICE=awr18xx
set MMWAVE_SDK_DEVICE_TYPE=xwr18xx
set DOWNLOAD_FROM_CCS=yes

echo [*] Initializing TI mmWave SDK Build Environment...
pushd C:\ti\mmwave_sdk_03_06_02_00-LTS\packages\scripts\windows
call setenv.bat
popd
if %ERRORLEVEL% NEQ 0 (
    echo [!] ERROR: Failed to configure build environment.
    goto error
)

REM 2. Change to MMW Demo directory
cd /d C:\ti\mmwave_sdk_03_06_02_00-LTS\packages\ti\demo\xwr18xx\mmw

echo.
echo [*] Building MSS and DSS binaries for AWR1843...
C:\ti\xdctools_3_50_08_24_core\gmake.exe mmwDemo
if %ERRORLEVEL% NEQ 0 (
    echo [!] ERROR: Compilation failed!
    goto error
)

echo.
echo [*] Copying generated binary to project workspace...
set PROJECT_DIR=%~dp0..\..
copy /Y "xwr18xx_mmw_demo.bin" "%PROJECT_DIR%\firmware\prebuilt_binaries\awr1843_door_sensor.bin"
if %ERRORLEVEL% NEQ 0 (
    echo [!] Warning: Could not copy binary to prebuilt_binaries directory.
) else (
    echo [+] Successfully copied: firmware\prebuilt_binaries\awr1843_door_sensor.bin
)

echo.
echo ==============================================================================
echo   SUCCESS! Flashable MetaImage generated:
echo   firmware\prebuilt_binaries\awr1843_door_sensor.bin
echo.
echo   You can now flash this directly to AWR1843BOOST using UniFlash!
echo   No DCA1000 required - everything runs on-chip.
echo ==============================================================================
goto end

:error
echo.
echo [!] BUILD FAILED. Check compiler error messages above.
exit /b 1

:end
endlocal
exit /b 0
