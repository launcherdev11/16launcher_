@echo off
cd /d %~dp0
echo.
echo ====== Git статус перед коммитом ======
git status
echo.

set /p msg=Введите комментарий к коммиту: 
git add .
git commit -m "%msg%"
git push origin main

echo.
echo ====== Пуш завершён ======
pause
