# util

설치(Claude Code 2.1.275+):

```text
/plugin install util --marketplace hooking001/skills
```

일회성 유틸리티 모음입니다. Claude Code에서 `/util:util`, Codex에서 `$util`을 호출하면 사용할 수 있는 작업 목록이 나옵니다.

## ssh-connect

Python 3.8+와 OpenSSH가 필요합니다. 서버 목록은 `~/.ssh/ssh-connect/servers.json`에 저장하고 기존 SSH 설정은 수정하지 않습니다. 비밀번호·OTP는 저장하지 않습니다. macOS에서는 Terminal.app, Linux에서는 gnome-terminal·konsole·xterm을 지원합니다. GUI가 없으면 직접 로그인할 수 있는 명령을 대신 안내합니다.

```text
개발 서버로 id@a.b.c.d 등록해줘. 작업 경로는 /home/id/project야.
개발 서버에 연결해줘.
```

연결이 없으면 별도 터미널이 열립니다. 그 창에서 비밀번호·OTP를 직접 입력하고 로그인이 끝났다고 알려 주면, 에이전트가 연결을 확인한 뒤 원격 명령과 파일 전송을 이어 갑니다. 터미널을 열어 두는 동안에는 같은 연결을 재사용합니다.

```text
개발 서버에서 git 상태 확인해줘.
./input.txt를 개발 서버 /tmp/input.txt로 올려줘.
개발 서버 /tmp/result.txt를 현재 폴더로 내려받아줘.
개발 서버 연결 종료해줘.
```
