!include "MUI2.nsh"
!include "FileFunc.nsh"

Unicode True
SetCompressor /SOLID lzma

Name "Яндекс Музыка Mod"
OutFile "..\dist\Yandex_Music_x64_5.124.1_Mod.exe"
InstallDir "$LOCALAPPDATA\Programs\YandexMusic"
RequestExecutionLevel user

Icon "..\assets\icon.ico"

VIProductVersion "5.124.1.0"
VIAddVersionKey "ProductName" "Яндекс Музыка Mod"
VIAddVersionKey "CompanyName" "alexis0eu"
VIAddVersionKey "LegalCopyright" "alexis0eu"
VIAddVersionKey "FileDescription" "Яндекс Музыка Mod v1.3.0"
VIAddVersionKey "FileVersion" "5.124.1.0"

!define MUI_ICON "..\assets\icon.ico"
!define MUI_UNICON "..\assets\icon.ico"

!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Russian"

Section "MainSection" SEC01
    DetailPrint "Закрытие запущенных процессов..."
    nsExec::Exec 'taskkill /F /IM "Яндекс Музыка.exe" /T'
    nsExec::Exec 'taskkill /F /IM "YandexMusic.exe" /T'
    Sleep 1000

    DetailPrint "Копирование файлов мода..."
    SetOutPath "$INSTDIR"
    File /r "..\dist\staging\*"

    DetailPrint "Создание ярлыков..."
    Delete "$DESKTOP\Яндекс*.lnk"
    Delete "$SMPROGRAMS\Яндекс*.lnk"

    CreateShortCut "$DESKTOP\Яндекс Музыка Mod.lnk" "$INSTDIR\Яндекс Музыка.exe" "" "$INSTDIR\resources\assets\icon.ico" 0
    CreateDirectory "$SMPROGRAMS\Яндекс Музыка Mod"
    CreateShortCut "$SMPROGRAMS\Яндекс Музыка Mod\Яндекс Музыка Mod.lnk" "$INSTDIR\Яндекс Музыка.exe" "" "$INSTDIR\resources\assets\icon.ico" 0
    CreateShortCut "$SMPROGRAMS\Яндекс Музыка Mod\Удалить.lnk" "$INSTDIR\Uninstall Яндекс Музыка.exe"

    DetailPrint "Завершение установки..."
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "DisplayName" "Яндекс Музыка Mod v1.3.0"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "DisplayVersion" "1.3.0"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "Publisher" "alexis0eu"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "DisplayIcon" "$INSTDIR\resources\assets\icon.ico"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YandexMusic" "UninstallString" '"$INSTDIR\Uninstall Яндекс Музыка.exe"'

    DetailPrint "Запуск Яндекс Музыка Mod..."
    Exec '"$INSTDIR\Яндекс Музыка.exe"'
SectionEnd
