# YEON X Mission

크롬 스타일의 X 버튼 미션 앱입니다. 미션 내용은 나중에 추가됩니다.

## Windows EXE
[GitHub 릴리스](https://github.com/pullgena/YEON/releases/tag/x-mission-v1.0.0)에서 Windows 포터블 EXE를 받을 수 있습니다 (빌드 성공 후).

## 실행
Node.js 22 이상에서 `npm install`, `npm start`. Windows 빌드: `npm run build:win`.

이 프로젝트는 기존 YEON 채팅 앱과 분리된 `x-mission/` 폴더에 있습니다. 앱의 내부 X 및 창 닫기 동작은 미션을 시작하지만 OS 강제 종료는 차단하지 않습니다. 경고음은 오디오 자체 설정상 최대치이며 시스템 볼륨을 강제로 바꾸지는 못합니다.
