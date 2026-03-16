@echo off
REM 나라장터 입찰공고 자동 발굴 시스템 - 수동 실행
REM 더블클릭으로 즉시 실행. 결과는 Slack과 log/bid_monitor.log에 기록됨

cd /d "%~dp0"
python main.py %*
pause
