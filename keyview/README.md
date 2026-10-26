# YEON KeyView v1.2.0 — ANSI 104-key Purple Overlay

Windows 화면에서 **실제 키보드의 104개 키가 보라색으로 반응하는 프로그램**입니다.
이전 참고 이미지의 어두운 배경, 보라색 테두리, 입력 횟수, **KPS** 및 **Total** 스타일을 유지하면서
기존 16키 표시를 **전체 104키 배열**로 교체했습니다.

## 주요 기능

- **ANSI 104키 레이아웃**: Esc·F1~F12·문자·Shift·Ctrl·방향키·숫자패드 포함
- 실제 키를 누르면 해당 키가 밝아지고, 키마다 누른 횟수가 화면에 표시됨
- **Shift 조합의 실제 출력 기호 표시**: Shift+1 → `!`, Shift+2 → `@`, Shift+/ → `?` 등
- Shift를 눌러도 **1 키의 카운트는 1 키에 누적**됨 (Shift는 자체 카운트 별도)
- 자동 반복 키 이벤트는 중복 카운트하지 않음
- **KPS**는 최근 1초간 새로 눌린 키 수, **Total**은 실행 후 누른 키 전체 횟수
- 창은 마우스로 옮길 수 있고 기본적으로 다른 창 위에 유지됨
- **백그라운드 실행**: 우클릭 → 백그라운드로 숨기기 → 트레이에서 계속 실행
- Windows 알림 영역에서 아이콘을 더블클릭하거나 우클릭 → **YEON KeyView 표시**로 복원
- 우클릭 메뉴에서 입력 감지 중지/재개, 항상 위 설정, 카운터 초기화, 완전히 종료
- 화면보다 키보드가 크면 **자동 축소하여 전체 104키를 표시**

> 화면의 `RAlt`·`RCtrl` 키는 한국어 키보드에서 한/영·한자로 동작할 수도 있지만,
> ANSI 104키의 **물리적 배열**을 기준으로 표시합니다.
> Fn 키는 표준 104키 수에 포함되지 않으며 일반적으로 OS에 독립 키 이벤트가 전달되지 않습니다.

## 설치 및 사용

1. [GitHub Releases](https://github.com/pullgena/YEON/releases)에서 KeyView 최신 Windows EXE를 받습니다.
2. `YEON-KeyView.exe`를 실행하고 표시창을 원하는 위치로 드래그합니다.
3. 보라색 키를 확인하면서 다른 앱을 사용할 수 있습니다.
4. 창 우클릭 → **백그라운드로 숨기기**를 선택하면 화면은 숨겨지지만 트레이에서 계속 실행됩니다.
5. 작업 표시줄 알림 영역의 보라색 K 아이콘에서 다시 열거나 **완전히 종료**합니다.

**Windows 로그인 시 자동 시작은 하지 않습니다.**
키보드 입력의 문자 내용·입력 순서·암호 텍스트를 디스크나 서버에 저장하지 않습니다.
다만 **키별 횟수는 프로그램이 실행되는 동안 메모리에 보관**됩니다. 민감한 작업 중에는 트레이의 **입력 감지 중지**를 사용하세요.

## Python 3.12+ Windows 개발 실행

```powershell
cd keyview
py -m pip install -r requirements.txt
py -m unittest discover -s tests -p "test_*.py"
py app.py
```

## Windows EXE 빌드

GitHub Actions가 main 브랜치의 변경 사항을 자동 테스트하고 `YEON-KeyView.exe`를 빌드합니다.
별도 릴리스에 EXE 업로드를 시도하며, 빌드 아티팩트에서도 내려받을 수 있습니다.

```powershell
py -m pip install -r keyview/requirements.txt
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name YEON-KeyView --paths keyview --hidden-import pystray._win32 keyview/app.py
```

게임 안티치트·권한 제한이나 특수 키보드 드라이버에서는 일부 키 입력이 감지되지 않을 수 있습니다.
