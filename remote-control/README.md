# YEON 원격 조정 · 관리 대상 v1.2.0

이 프로그램은 관리자의 원격 조작을 받는 **Windows PC용 앱**입니다. 관리자용 앱은 별도 릴리스(`remote-admin-v1.1.0`)에서 받을 수 있습니다.

## 사용 방법

1. 관리 대상 PC에서 `YEON-Managed-PC-v1.2.0.exe`를 실행합니다. 화면 오른쪽 알림 영역(숨겨진 아이콘 `^` 포함)에 **YEON 아이콘**이 나타납니다.
2. 제어판에서 **공유 시작**을 누릅니다. 컴퓨터 화면과 입력 제어는 이때부터 허용됩니다. (프로그램을 실행하는 것만으로 공유가 시작되지는 않습니다.)
3. 화면에 표시되는 `http://192.168.x.x:8765` 같은 주소와 8자리 코드를 관리자에게 전달합니다. 두 PC는 같은 신뢰할 수 있는 Wi-Fi 또는 LAN에 있어야 합니다.
4. 창의 `X` 버튼이나 **백그라운드로 보내기**를 누르면 **프로그램을 종료하지 않고 알림 영역에 남아** 공유를 유지합니다. 공유 중이면 아이콘 상태 표시가 초록색으로 바뀝니다.
5. 작업 표시줄 오른쪽 `^`에서 **YEON 아이콘을 오른쪽 클릭**하면 `관리 대상 창 열기`, `화면 공유 시작`, `공유 즉시 중지`, `프로그램 완전 종료`를 사용할 수 있습니다.

프로그램을 정말로 끄려면 트레이 메뉴의 **프로그램 완전 종료**를 누르세요. 공유 중지 버튼은 연결된 모든 원격 세션을 즉시 무효화합니다. 프로그램 완전 종료를 선택하면 모든 공유가 종료됩니다.

## 보안 및 제한

- 같은 로컬 네트워크에서만 사용하도록 설계되었으며 인터넷 공개, 자동 부팅 실행, 숨겨진 실행, 임의 명령 실행을 제공하지 않습니다.
- **명시적으로 `공유 시작`을 누르기 전에는 원격 제어할 수 없습니다.** 백그라운드 실행 시에도 트레이 아이콘을 표시합니다.
- HTTP 연결은 암호화되지 않으므로 신뢰할 수 있는 개인 네트워크만 사용하세요. 포트 8765를 인터넷에 공개하지 마세요.
- 8자리 접속 코드, 접속 실패 제한, 세션 만료, 원격 세션 차단 기능을 갖췄습니다.
- Windows 로그인 화면과 UAC 보안 화면은 제어할 수 없습니다.

## Windows EXE 빌드

```powershell
cd remote-control
python -m pip install -r requirements.txt pyinstaller
python -m unittest discover -s tests -v
python tools/make_icon.py
pyinstaller --noconfirm --clean --onefile --windowed --name 'YEON-Managed-PC-v1.2.0' --icon 'assets/yeon-managed.ico' --add-data 'assets/yeon-managed.ico;assets' --add-data 'web/index.html;web' --hidden-import 'pystray._win32' app.py
```

릴리스 태그는 `remote-managed-v1.2.0`이며 GitHub Actions 자동 빌드를 사용합니다. 기존 관리자의 v1.1.0 릴리스는 수정하지 않습니다.
