@echo off
setlocal EnableExtensions
chcp 65001 > nul
title KONEPS Scheduler Registration

REM 나라장터 입찰공고 자동 발굴 시스템 - Windows 작업 스케줄러 등록
REM 실행 시 원하는 시간을 입력하면 매주 월~금 해당 시간에 자동 실행 등록
REM 이미 등록된 경우 덮어쓰기

cd /d "%~dp0"

set "TASK_NAME=나라장터 입찰공고 알리미"
set "TASK_RC=1"
set "RESULT=FAIL"

echo.
echo 매주 월~금 자동 실행할 시간을 입력하세요.
echo 형식: HH:MM (예: 09:00, 14:30)
echo.
set /p SCHEDULE_TIME=실행 시간:

if "%SCHEDULE_TIME%"=="" (
    echo.
    echo [취소] 시간이 입력되지 않았습니다.
    goto :END
)

echo %SCHEDULE_TIME%| findstr /R "^[0-2][0-9]:[0-5][0-9]$" > nul
if errorlevel 1 (
    echo.
    echo [실패] 시간 형식이 올바르지 않습니다. HH:MM 형식으로 입력하세요.
    goto :END
)

for /f "tokens=1 delims=:" %%H in ("%SCHEDULE_TIME%") do set "HOUR=%%H"
if %HOUR% GTR 23 (
    echo.
    echo [실패] 시간 범위가 올바르지 않습니다. 00:00부터 23:59 사이로 입력하세요.
    goto :END
)

for /f "delims=" %%i in ('where python 2^>nul') do (
    if not defined PYTHON_PATH set "PYTHON_PATH=%%i"
)

if not defined PYTHON_PATH (
    echo.
    echo [실패] python 실행 파일을 찾지 못했습니다.
    echo   Python 설치 또는 PATH 설정을 확인하세요.
    goto :END
)

echo.
echo [정보] Python 경로: "%PYTHON_PATH%"
echo [정보] 등록 명령 실행 중...

schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON_PATH%\" \"%~dp0main.py\"" /sc weekly /d MON,TUE,WED,THU,FRI /st "%SCHEDULE_TIME%" /f
set "TASK_RC=%ERRORLEVEL%"

echo.
echo [정보] schtasks 종료 코드: %TASK_RC%

if not "%TASK_RC%"=="0" (
    echo [실패] 스케줄러 등록에 실패했습니다.
    echo   시간 형식 HH:MM 을 확인하거나 관리자 권한으로 실행해보세요.
    goto :END
)

set "RESULT=SUCCESS"
echo [성공] 스케줄러 등록 완료
echo   작업 이름: %TASK_NAME%
echo   실행 시간: 매주 월~금 %SCHEDULE_TIME%

echo.
echo [확인] 등록된 작업 정보:
schtasks /query /tn "%TASK_NAME%" /fo list /v
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo [경고] 작업 조회에 실패했습니다. taskschd.msc에서 직접 확인하세요.
)

:END
echo.
if "%RESULT%"=="SUCCESS" (
    echo [최종 결과] 성공
) else (
    echo [최종 결과] 실패
)
echo.
echo 아무 키나 누르면 창이 닫힙니다.
pause > nul
endlocal & exit /b %TASK_RC%