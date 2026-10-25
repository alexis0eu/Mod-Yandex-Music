!include "MUI2.nsh"
!include "FileFunc.nsh"

Unicode True
SetCompressor /SOLID lzma

Name "Яндекс Музыка"
OutFile "..\dist\Yandex_Music_x64_5.124.1_Mod.exe"
InstallDir "$LOCALAPPDATA\Programs\YandexMusic"
RequestExecutionLevel user

Icon "..\dist\staging\resources\assets\icon.ico"

VIProductVersion "5.124.1.0"
VIAddVersionKey "ProductName" "Яндекс Музыка"
VIAddVersionKey "CompanyName" "Яндекс Музыка"
VIAddVersionKey "LegalCopyright" "Яндекс Музыка"
VIAddVersionKey "FileDescription" "Яндекс Музыка v1.2.0 (с модом)"
VIAddVersionKey "FileVersion" "5.124.1.0"

!define MUI_ICON "..\dist\staging\resources\assets\icon.ico"
!define MUI_UNICON "..\dist\staging\resources\assets\icon.ico"

!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Russian"

Section "MainSection" SEC01
    DetailPrint "Закрытие работающих процессов Яндекс Музыки..."
    nsExec::Exec 'taskkill /F /IM "Яндекс Музыка.exe" /T'
    nsExec::Exec 'taskkill /F /IM "YandexMusic.exe" /T'
    Sleep 1000

    DetailPrint "Установка файлов Яндекс Музыки с модом..."
    SetOutPath "$INSTDIR"
    File /r "..\dist\staging\*"

    DetailPrint "Создание ярлыков на рабочем столе и в меню Пуск..."
    ; Clean up any older mojibake or broken shortcuts
    Delete "$DESKTOP\РЇ*.lnk"
    Delete "$DESKTOP\Яндекс Музик.lnk"
    Delete "$SMPROGRAMS\РЇ*.lnk"
    RMDir /r "$SMPROGRAMS\РЇ*"

    CreateShortCut "$DESKTOP\Яндекс Музыка.lnk" "$INSTDIR\Яндекс Музыка.exe" "" "$INSTDIR\resources\assets\icon.ico" 0
    CreateDirectory "$SMPROGRAMS\Яндекс Музыка"
    CreateShortCut "$SMPROGRAMS\Яндекс Музыка\Яндекс Музыка.lnk" "$INSTDIR\Яндекс Музыка.exe" "" "$INSTDIR\resources\assets\icon.ico" 0
    CreateShortCut "$SMPROGRAMS\Яндекс Музыка\Удалить Яндекс Музыка.lnk" "$INSTDIR\Uninstall Яндекс Музыка.exe"

    DetailPrint "Регистрация приложения в системе..."
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "DisplayName" "Яндекс Музыка"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "DisplayVersion" "5.124.1"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "Publisher" "Яндекс Музыка"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "DisplayIcon" "$INSTDIR\resources\assets\icon.ico"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "UninstallString" '"$INSTDIR\Uninstall Яндекс Музыка.exe"'

    DetailPrint "Запуск Яндекс Музыки..."
    Exec '"$INSTDIR\Яндекс Музыка.exe"'
SectionEnd
