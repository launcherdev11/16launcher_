@echo off
setlocal EnableExtensions
chcp 65001 >nul


:: Запуск из папки скрипта
cd /d "%~dp0"


echo.
:: Проверка наличия Git
where git >nul 2>&1
if errorlevel 1 (
echo [ОШИБКА] Git не найден в PATH. Установите Git: https://git-scm.com/
goto :end
)


:: Проверка, что это репозиторий
git rev-parse --is-inside-work-tree >nul 2>&1 || (
echo [ОШИБКА] Текущая папка не является репозиторием Git.
goto :end
)


echo ====== Краткий статус (git status -sb) ======
git status -sb
echo.


:: Сообщение коммита: берём из аргументов или спрашиваем
set "MSG=%*"
if not defined MSG (
set /p "MSG=Введите сообщение коммита (Enter — отмена коммита): "
)


:: Добавляем все изменения (и новые файлы)
git add -A


:: Есть ли что коммитить?
git diff --cached --quiet
if errorlevel 1 (
if not defined MSG (
echo Коммит отменён: пустое сообщение.
goto maybe_push
)
echo Коммитим...
git commit -m "%MSG%"
if errorlevel 1 goto :end
) else (
echo Нет изменений для коммита — пропускаю шаг commit.
)


:maybe_push
:: Определяем текущую ветку
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%b"
if not defined BRANCH (
echo [ОШИБКА] Не удалось определить ветку (возможно detached HEAD).
goto :end
)


echo.
choice /M "Сделать pull --rebase перед push?"
if errorlevel 2 (
echo Pull пропущен по вашему выбору.
) else (
git pull --rebase --autostash
if errorlevel 1 (
echo [ОШИБКА] Pull завершился ошибкой. Разрешите конфликты и запустите скрипт снова.
goto :end
)
)


:: Пушим: если upstream не настроен — настраиваем
git rev-parse --abbrev-ref --symbolic-full-name @{u} >nul 2>&1
if errorlevel 1 (
echo Первый push в эту ветку: настраиваю upstream на origin/%BRANCH%...
git push -u origin "%BRANCH%"
) else (
git push
)


if errorlevel 1 (
echo [ОШИБКА] Push завершился с ошибкой.
goto :end
pause