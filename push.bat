@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ====== Краткий Git статус ======
git status -sb
echo.

:: Всегда спрашиваем сообщение
set /p msg=Введите комментарий к коммиту: 

:: Добавляем изменения
git add -A

:: Проверяем, есть ли что коммитить
git diff --cached --quiet
if errorlevel 1 (
    echo Создаём коммит...
    git commit -m "%msg%"
) else (
    echo Нет изменений для коммита — шаг commit пропущен.
)

:: Определяем текущую ветку
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b

:: Если upstream не настроен — пушим с -u
git rev-parse --abbrev-ref --symbolic-full-name @{u} >nul 2>&1
if errorlevel 1 (
    echo Первый push: настраиваю origin/%BRANCH% ...
    git push -u origin %BRANCH%
) else (
    git push
)

if errorlevel 1 (
    echo [ОШИБКА] Push завершился с ошибкой.
    goto end
)

echo.
echo ====== Последний коммит ======
git --no-pager log -1 --pretty=oneline --decorate

:end
echo.
echo ====== Скрипт завершён ======
pause
