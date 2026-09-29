@echo off
REM Backup PostgreSQL database to timestamped file
setlocal
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (
    set D=%%d-%%b-%%c
)
for /f "tokens=1-2 delims=:." %%a in ('time /t') do (
    set T=%%a%%b
)
set FILENAME=backups\campus_%D%_%T%.sql
if not exist backups mkdir backups
pg_dump -U campus_user -h localhost campus_platform > %FILENAME%
echo Backup saved: %FILENAME%
endlocal