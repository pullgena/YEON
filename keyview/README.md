# YEON KeyView v1.0.0

Windows에서 **실제 키보드를 누르면 옆의 가상 키보드가 함께 눌리는** 실시간 키 표시 프로그램입니다.

## 기능

- 다른 프로그램을 사용하면서도 키 누름/떼기를 실시간으로 표시
- 동시 입력(예: Ctrl + Shift + A) 시 여러 키 동시 강조
- 일반 키, 기능 키, 방향키, 숫자패드, 한/영·한자 키 표시
- 창을 다른 창 위에 유지하는 **항상 위** 버튼
- 입력 감지 중지/시작 및 눌린 키 초기화
- 입력 문자열을 **기록하거나 파일/서버로 전송하지 않음**

> 키보드 제조사/드라이버/한글 IME 설정에 따라 한/영, 한자, Fn, 일부 특수키는 감지되지 않을 수 있습니다. Fn 키는 대개 운영체제로 이벤트가 전달되지 않습니다. 관리자 권한으로 실행한 프로그램의 키를 감지하려면 이 앱도 관리자 권한으로 실행해야 할 수 있습니다.

## 사용법

1. [Actions](https://github.com/pullgena/YEON/actions/workflows/keyview-windows.yml)에서 최신 성공한 **KeyView Windows EXE** 작업을 엽니다.
2. 작업의 **Artifacts**에서 `YEON-KeyView-Windows`를 내려받고 압축을 풉니다.
3. `YEON-KeyView.exe`를 실행한 다음 창을 화면 옆으로 옮깁니다.
4. 다른 창에서 키를 눌러 가상 키보드가 반응하는지 확인합니다.

릴리스가 생성되었다면 [Releases](https://github.com/pullgena/YEON/releases)에서도 EXE를 받을 수 있습니다.

## 직접 실행 (Python 3.12+ / Windows)

```powershell
cd keyview
py -m pip install -r requirements.txt
py app.py
```

## Windows EXE 빌드

GitHub Actions는 `main` 브랜치의 `keyview/` 변경 사항을 감지하면 Windows에서 자동 빌드하고 실행 파일을 아티팩트에 업로드합니다.

수동 빌드도 가능합니다.

```powershell
py -m pip install -r keyview/requirements.txt
py -m pip install pyinstaller
py -m unittest discover -s keyview/tests -p "test_*.py"
py -m PyInstaller --noconfirm --clean --onefile --windowed --name YEON-KeyView --paths keyview keyview/app.py
```

출력: `dist/YEON-KeyView.exe`

## 개인정보

전역 키보드 이벤트를 프로그램 내부의 화면 표시용으로만 사용합니다. 원문 입력 내역, 비밀번호, 타이핑 기록을 저장하거나 네트워크로 전송하는 기능이 없습니다. 다만 앱이 실행 중인 동안 키가 눌렸다는 사실은 내부적으로 읽으므로, 민감한 환경에서는 **입력 감지 중지**를 사용하세요.
