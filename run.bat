@echo off
title SA Quant Racing Predictor Launcher
color 0A

:menu
cls
echo ===================================================
echo   SA QUANT RACING PREDICTOR Launcher
echo ===================================================
echo.
echo  Please select a prediction engine to run:
echo.
echo  1 -^> v3.9 7-Track Adaptive (default)
echo  2 -^> v4.2 ML Calibration
echo  3 -^> v3.8 Legacy Rule
echo  4 -^> Static Web Version
echo.
set /p choice="Enter selection [1-4] (default is 1): "

if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo.
    echo [v3.9] Disabling ML model pkl temporarily...
    if exist "calibration_model_v42.pkl" (
        ren "calibration_model_v42.pkl" "calibration_model_v42.pkl.disabled"
    )
    set MODEL_MODE=v3.9
    goto launch_streamlit
)

if "%choice%"=="2" (
    echo.
    echo [v4.2] Enabling ML model pkl...
    if exist "calibration_model_v42.pkl.disabled" (
        ren "calibration_model_v42.pkl.disabled" "calibration_model_v42.pkl"
    )
    if not exist "calibration_model_v42.pkl" (
        echo ML model calibration_model_v42.pkl not found. Training it first...
        py train_model.py
    )
    set MODEL_MODE=v4.2
    goto launch_streamlit
)

if "%choice%"=="3" (
    echo.
    echo [v3.8] Disabling ML model pkl temporarily...
    if exist "calibration_model_v42.pkl" (
        ren "calibration_model_v42.pkl" "calibration_model_v42.pkl.disabled"
    )
    set MODEL_MODE=v3.8
    goto launch_streamlit
)

if "%choice%"=="4" (
    echo.
    echo Launching static web version...
    start index.html
    exit
)

echo Invalid selection. Please try again.
pause
goto menu

:launch_streamlit
echo Launching Streamlit app in %MODEL_MODE% mode...
py -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
