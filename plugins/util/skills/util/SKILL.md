---
name: util
description: 일회성 유틸리티 목록을 보여 주거나 선택한 작업을 한 번 실행한다. util:ssh-connect, SSH 서버 등록·접속·원격 명령·파일 전송 요청에 사용한다.
---

# 일회성 유틸리티

인자나 작업 요청 없이 `util`을 호출하면 아래 목록과 호출 방법을 보여 준다. 선택한 작업이 있으면 연결된 절차를 읽고 이번 요청에 적용한다.

| 유틸리티 | 작업 | 절차 |
| --- | --- | --- |
| `ssh-connect` | 서버 등록, 사용자 직접 인증, 원격 명령, 파일 전송 | [SSH 절차](references/ssh-connect.md) |

Codex는 `$util ssh-connect`, Claude Code는 `/util:ssh-connect`로 항목을 직접 선택할 수 있다.
