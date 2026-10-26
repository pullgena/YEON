# YEON KeyView v1.1.0 — Purple KPS Overlay

**실제 키를 누르면 작은 보라색 키보드 표시창이 반응하는 Windows 앱**입니다.
참고 이미지처럼 8개 × 2줄 키 박스, 각 키의 누른 횟수, KPS와 Total을 표시합니다.

## 주요 기능

- 검정·보라 테마, 밝은 보라색 키 누름 효과
- 키를 누를 때 키별 입력 횟수 증가, 하단 **Total**(총 눌림)과 **KPS**(최근 1초 키 눌림) 표시
- 화면에 없는 키를 누르면 **오래 사용되지 않은 칸이 자동으로 새 키로 교체**되어 모든 지원 키를 볼 수 있음
- 키보드 자동 반복(길게 눌렀을 때 반복 발생하는 down 이벤트)은 추가 타수로 계산하지 않음
- 게임이나 다른 앱을 쓸 때도 입력 감지 (전역 키보드 훅, 다른 프로그램 키 입력 차단 안 함)
- 드래그하여 화면 원하는 위치에 배치, 기본 항상 위
- **백그라운드 실행**: 우클릭 → 백그라운드로 숨기기 → 작업 표시줄 알림 영역(트레이)에서 계속 실행
- 트레이 아이콘을 더블클릭하거나 우클릭 → YEON KeyView 표시를 눌러 다시 열기
- 트레이 또는 표시창 우클릭 메뉴에서 입력 감지 중지, 카운터 초기화, 완전히 종료

> **중요:** 창을 숨겨도 프로그램은 계속 실행됩니다. **완전히 종료**를 눌러야 키보드 감지가 해제됩니다. Windows 로그인 시 자동으로 실행되도록 등록하지는 않습니다.
>
> 화면은 입력된 문장·비밀번호 문자열을 표시하거나 저장하지 않습니다. 다만 키별 횟수와 총 타수는 프로그램이 실행되는 동안 메모리에 보관하며, 저장·전송 기능은 없습니다. 암호 입력 등 민감한 작업 중에는 트레이 메뉴의 **입력 감지 중지**를 선택하세요.

## 다운로드 및 실행

1. [YEON GitHub Releases](https://github.com/pullgena/YEON/releases)에서 **YEON KeyView**의 최신 Windows `.exe`를 다운로드합니다.
2. `YEON-KeyView.exe`를 실행하면 보라색 미니 표시창이 나타납니다.
3. 표시창을 **마우스 왼쪽 버튼으로 드래그**하면 이동할 수 있습니다.
4. 표시창에서 **마우스 오른쪽 버튼**을 눌러 **백그라운드로 숨기기**를 선택할 수 있습니다.
5. Windows의 **알림 영역(시스템 트레이)**에서 K 아이콘을 찾아 다시 표시하거나 완전히 종료할 수 있습니다.

## 개발 및 테스트 (Windows / Python 3.12+)

```powershell
cd keyview
py -m pip install -r requirements.txt
py -m unittest discover -s tests -p "test_*.py"
py app.py
```

## EXE 빌드

`.github/workflows/keyview-windows.yml` GitHub Actions가 수정사항을 감지하면 Windows에서 자동 테스트·EXE 빌드·아티팩트 업로드·별도 KeyView 릴리스를 진행합니다.
직접 빌드하려면:

```powershell
py -m pip install -r keyview/requirements.txt
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name YEON-KeyView --paths keyview --hidden-import pystray._win32 keyview/app.py
```

실행 파일: `dist/YEON-KeyView.exe`

## 참고사항

- Windows 10/11 데스크톱용이며, 관리자 권한 프로그램의 키 감지는 관리자 권한을 요구할 수 있습니다.
- Fn·한/영·한자·키패드 특수키는 키보드 제조사·IME에 따라 다르게 감지될 수 있습니다.
- 멀티미디어 등 OS가 전달하지 않는 일부 키는 표시되지 않을 수 있습니다.
- **KPS**는 지난 1초간 발생한 새로운 key-down 이벤트 수이며, **Total**은 앱 실행 이후 새로 눌린 횟수의 누계입니다.
