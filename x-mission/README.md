# YEON X Mission v1.1.0

크롬 스타일 X 버튼 미션 Windows 앱입니다. 기존 YEON 채팅 앱과 별개로 `x-mission/`에서 관리합니다.

## 미션
- 탭의 X 버튼: 랜덤하게 클릭 챌린지 또는 움직이는 과녁 명중 게임 시작
- 클릭 미션 횟수 확률: 300번 60%, 900번 20%, 2000번 10%, 100번 10% (남는 10% 임시 배정)
- 화살 명중: 움직이는 과녁을 클릭하거나 가운데 조준점을 기준으로 스페이스바를 눌러서 5회 맞히기
- 성공하면 **처음 화면으로** 버튼으로 복귀

## 창 조작
- 창 오른쪽 최상단 X: **실제 창 종료**
- 탭 X: 미션 시작
- 최소화/최대화 버튼: 정상 동작
- 시스템 `Alt + F4`: 창 종료

## Windows 앱
[릴리스 다운로드](https://github.com/pullgena/YEON/releases) (GitHub Actions의 빌드와 업로드 성공 후)

로컬 개발: Node.js 22 이상에서
```bash
npm install
npm start
```
Windows 포터블 EXE 빌드: `npm run build:win`

경고음은 앱 내부 오디오 레벨로 출력하며 Windows 시스템 음량을 강제로 바꾸지 않습니다.
