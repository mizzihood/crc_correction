@echo off
REM skripta za izvajanje transformacije NC programov z anglec.exe preko menuja Send to
REM verzija 24.11.2013 
REM avtor: Jernej Pristavec
set p1=2811.0
set p2=2815.0

echo anglec %p1% %p2%
FOR %%A IN (%*) DO (
echo %%A "->" %%~dpnAp.nc
REM c:\anglec\anglec %%A %%~dpnAp.nc 2813.7 2910.7
c:\anglec\anglec %%A %%~dpnAp.nc %p1% %p2%
)


echo.
echo --------------------
echo KONEC
echo --------------------
pause
