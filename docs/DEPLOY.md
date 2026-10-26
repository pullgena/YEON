# YEON MODS 무료 배포 사이트

이 폴더는 **기존 YEON 메신저 앱과 별개**인 마인크래프트 모드 소개 및 무료 배포 사이트입니다.

## GitHub Pages 켜기 (관리자 최초 1회)

1. GitHub 저장소 https://github.com/pullgena/YEON 의 **Settings → Pages**로 이동합니다.
2. **Build and deployment → Source**를 **Deploy from a branch**로 설정합니다.
3. **Branch**를 `main`, 폴더를 `/docs`로 고르고 **Save**를 누릅니다.
4. 게시가 완료되면 GitHub Pages의 Visit site 링크에서 열 수 있습니다.
   일반적인 프로젝트 사이트 URL은 `https://pullgena.github.io/YEON/`입니다. 이 주소는 Pages 설정 및 배포 완료 전까지 동작하지 않을 수 있습니다.

## 등록된 저장소

- https://github.com/pullgena/phone-mod (Fabric 26.3)
- https://github.com/pullgena/mod-of-mod (Fabric 26.3)
- https://github.com/pullgena/op-mod (Fabric 26.2)
- https://github.com/pullgena/EasyCraft-Launcher-mod (Fabric 26.2)

사이트는 각 저장소의 **최신 공개 정식 GitHub Release**를 GitHub REST API로 조회합니다.
배포용 `.jar` 파일이 등록된 릴리스만 다운로드 버튼이 나타납니다.
GitHub API 조회에 실패한 경우 릴리스 페이지 링크를 제공합니다.

**중요:** GitHub Actions Artifacts는 GitHub Release 파일과 다릅니다. 사용자가 로그인 없이 다운로드하도록 배포하려면, 모드 저장소의 GitHub Releases에 실제 JAR 자산을 공개 등록해야 합니다.

사이트 코드: `docs/index.html` (서버/외부 JavaScript 라이브러리 필요 없음)
