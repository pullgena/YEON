# YEON v0.2.0

Discord에서 영감을 받은 YEON Windows 데스크톱 앱입니다.

## Windows EXE 다운로드
[GitHub Releases](https://github.com/pullgena/YEON/releases)에서 **v0.2.0**의 EXE를 선택하세요.
GitHub Actions가 설치형(NSIS) 및 포터블 EXE를 생성하고 릴리스에 업로드하도록 설정되어 있습니다.

## 개발자 실행
Node.js 20+를 설치하고:
```bash
npm install
npm start
```
웹 서버만 실행하려면 `npm run web`, Windows EXE를 직접 빌드하려면 `npm run dist`를 사용하세요.

## 기능
- 디스코드 느낌의 다크 UI, 서버/채널 생성, 텍스트 채팅, 온라인 사용자
- Windows 데스크톱 창, 사용자 데이터 디렉터리 내 메시지 저장
- 로컬 서버를 임의 포트(127.0.0.1)에서 실행해 앱 내부에서 표시

## 중요
**이 초기 데스크톱 버전은 컴퓨터마다 별도의 로컬 서버를 실행합니다.** 따라서 EXE를 설치한 서로 다른 컴퓨터가 자동으로 같은 채팅방에 연결되는 것은 아닙니다. 실제 인터넷 다중 사용자 서비스에는 별도 공용 서버, 로그인/권한/보안 체계가 필요합니다. 현재 로그인 인증·암호화·음성 및 영상 통화는 없습니다. 코드 서명하지 않은 EXE에 Windows SmartScreen 경고가 나타날 수 있습니다.
