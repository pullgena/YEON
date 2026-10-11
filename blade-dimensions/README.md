# Blade Dimensions

3D 검 액션 + 멀티플레이 게임의 Windows Electron 앱 버전입니다.

## 실행
```bash
npm install
npm start
```

`npm start` 전에 `game_parts/`의 조각들을 자동으로 합쳐 `game.html`을 만듭니다.

## Windows EXE 빌드
```bash
npm install
npm run dist:win
```

빌드 결과:
`dist/Blade-Dimensions-Setup-0.2.0-x64.exe`

## 방 코드 판정
- 이 기기에서 실제로 생성했거나 연결에 성공한 방 코드는 로컬 기록에 저장됩니다.
- 그런 방이 나중에 없어지면 캐릭터가 전기 연출과 함께 방장이 떠난 시간을 보여줍니다.
- 이 기기에서 존재했던 기록이 전혀 없는 코드는 흰 화면에서 캐릭터가 **“방이 없어요”**라고 말합니다.

> PeerJS 방식에는 전 세계 방 생성 이력을 보관하는 중앙 서버가 없어서, “있었다가 사라진 방” 판정은 이 앱/기기에서 실제로 확인했던 방 기록을 기준으로 합니다.
