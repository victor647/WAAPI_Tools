@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem  一键打包并发布：package_gui.py -> package_mcp.py -> publish_merged.py
rem  任一步失败立即中断，不会继续后续步骤（也不会递增发布号）。
rem  可用环境变量 WAAPI_PYTHON 指定 Python 解释器路径。
rem  自动化调用时可加 --no-pause，避免结束前的按键等待。
rem ============================================================

set "SCRIPT_DIR=%~dp0"
set "NOPAUSE="
if /i "%~1"=="--no-pause" set "NOPAUSE=1"

pushd "%SCRIPT_DIR%.." || (
    echo [ERROR] 无法进入仓库根目录: %SCRIPT_DIR%..
    exit /b 1
)

rem 选择解释器：优先 WAAPI_PYTHON，其次固定的构建环境，最后 PATH 中的 python
set "PY="
if defined WAAPI_PYTHON set "PY=%WAAPI_PYTHON%"
if not defined PY if exist "P:\Python314\python.exe" set "PY=P:\Python314\python.exe"
if not defined PY set "PY=python"

"%PY%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 找不到可用的 Python 解释器: %PY%
    echo         可设置环境变量 WAAPI_PYTHON 指向 python.exe。
    set "EXITCODE=1"
    goto :finish
)

echo ============================================================
echo   开始时间: %DATE% %TIME%
echo   Python  : %PY%
echo   工作目录: %CD%
echo ============================================================

call :step "1/3" "打包 GUI（package_gui.py）" "packager\package_gui.py"
if errorlevel 1 (
    set "EXITCODE=1"
    goto :finish
)

call :step "2/3" "打包 MCP（package_mcp.py）" "packager\package_mcp.py"
if errorlevel 1 (
    set "EXITCODE=1"
    goto :finish
)

call :step "3/3" "发布（publish_merged.py）" "packager\publish_merged.py"
if errorlevel 1 (
    set "EXITCODE=1"
    goto :finish
)

set "EXITCODE=0"

:finish
echo.
echo ============================================================
if "%EXITCODE%"=="0" (
    echo   全部完成: %DATE% %TIME%
) else (
    echo   中断: 上一步失败，后续步骤未执行
)
echo ============================================================
popd
rem 双击运行时暂停一下，便于查看结果（可用 --no-pause 关闭）
if defined NOPAUSE goto :nopause
echo %cmdcmdline% | find /i "%~nx0" >nul
if not errorlevel 1 pause
:nopause
endlocal & exit /b %EXITCODE%

:step
set "STEP_NO=%~1"
set "STEP_NAME=%~2"
set "STEP_SCRIPT=%~3"
echo.
echo ------------------------------------------------------------
echo   %STEP_NO%  %STEP_NAME%
echo ------------------------------------------------------------
"%PY%" "%STEP_SCRIPT%"
if errorlevel 1 (
    echo.
    echo [FAILED] %STEP_NAME% 失败，exit code = !ERRORLEVEL!
    exit /b 1
)
echo [OK] %STEP_NAME%
exit /b 0
