# YEON KeyView v1.3.0

검정·보라색 테마의 Windows 키보드 입력 시각화 프로그램입니다.
104키 전체 표시를 유지하면서 사진과 같은 16키, WASD+스페이스바 화면을 단축키로 바꿔 볼 수 있습니다.

## 표시 화면 전환

| 단축키 | 표시 모드 |
| --- | --- |
| **Shift + 1** | 보내주신 사진과 같은 **2줄 × 8개(16키)** 화면 |
| **Shift + 2** | 게임용 **W, A, S, D + Space** 화면 |
| **Shift + 3** | 기존 **ANSI 104키 전체** 화면 |

왼쪽 Shift, 오른쪽 Shift 모두 지원합니다. 단축키는 실제 키보드 입력을 차단하지 않으므로 해당 프로그램/게임에도 Shift+숫자 조합이 입력됩니다.

우클릭 메뉴나 Windows 시스템 트레이 아이콘에서도 화면을 변경할 수 있습니다.

### Shift + 1: 사진 화면

```text
 ~     1     2     E     P     =    Back   \
 ↑    L⇧     C     ~    RAlt    .     ↵   RCtrl
 KPS                     Total
```

각 칸 아래에 **키별 입력 횟수**가 나타납니다.

### Shift + 2: 게임 화면

W 키가 위, A/S/D 키가 아래, 큰 스페이스바가 하단에 나타납니다. 다섯 키의 카운트와 KPS/Total이 표시됩니다.

## 렉 감소

기존 버전은 104개 키와 모든 도형을 **매 50ms마다 지우고 새로 그리는 방식**이었습니다.
이번 버전은 모드를 바꿀 때만 도형을 생성하고, 일반 키 입력에는 **변경된 키의 색상·문구·숫자만 갱신**합니다.
창을 트레이로 숨기면 화면 갱신은 중단하고 키 입력 카운트만 유지합니다.
주기적 입력 확인도 숨김 상태에서는 낮은 빈도로 실행합니다.

## 기타

- 항상 위: 기본 켜짐, 우클릭 메뉴에서 전환
- 백그라운드로 숨기기: 창 우클릭 → 메뉴; Windows 알림 영역에서 다시 표시
- 카운터 초기화, 키 입력 감지 중지/재개, 완전히 종료
- Shift + 숫자 조합에서 실제 물리키 카운트를 유지
- 키별 횟수·KPS·Total은 프로그램을 종료하면 사라짐. 타이핑한 문장이나 비밀번호 텍스트를 파일/네트워크로 저장·전송하지 않음
- 게임 안티치트·관리자 권한 프로그램·특수 드라이버는 키 후킹을 제한할 수 있음
- Windows에 로그인할 때 자동으로 실행되는 기능은 아직 없음

## 다운로드

[GitHub Releases](https://github.com/pullgena/YEON/releases)에서 **KeyView v1.3** `YEON-KeyView.exe`를 받으세요.

## 소스 실행 (Windows, Python 3.12+)

```powershell
cd keyview
py -m pip install -r requirements.txt
py -m unittest discover -s tests -p "test_*.py"
py app.py
```

## GitHub Actions 빌드

`.github/workflows/keyview-windows.yml`에서 테스트, Windows EXE 빌드, 아티팩트 업로드 및 별도 릴리스 게시를 진행합니다.
