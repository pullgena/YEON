# YEON v0.3.0

Discord 스타일의 Windows 데스크톱 채팅 앱 프로토타입입니다.

## Windows 다운로드
[YEON GitHub Releases](https://github.com/pullgena/YEON/releases)에서 v0.3.0의 EXE 파일을 다운로드하세요. GitHub Actions가 빌드를 마치고 릴리스 자산을 올려야 다운로드 가능합니다.

## 구현된 기능
- 서버 아이콘 레일, 텍스트 채널 목록, 메시지 본문, 온라인 사용자 목록
- 홈/친구 소개 화면, 닉네임 변경, 메시지 검색
- 채널 및 서버 생성, 실시간 텍스트 메시지, 로컬 JSON 저장
- Windows 설치형/포터블 EXE 빌드

## 주의
이 버전은 **Discord 완제품이 아닌 UI 및 채팅 프로토타입**입니다. 친구 요청/DM, 음성/화상 통화, 계정 인증, 초대 및 권한 시스템은 미구현입니다. Windows EXE의 서버는 컴퓨터마다 로컬로 실행되어 서로 다른 기기 간 메시지가 자동으로 공유되지 않습니다. 서로 다른 PC 간 실제 채팅은 별도로 배포한 공용 서버와 사용자 인증이 필요합니다.

## 개발 실행
Node.js 20 이상 설치 후:

```bash
npm install
npm start
```

웹 서버만 실행하려면 `npm run web`, EXE 빌드는 Windows에서 `npm run dist`를 실행합니다.
