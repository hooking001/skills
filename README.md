# hooking001 skills

Claude Code와 Codex에서 함께 쓰는 공개 스킬 모음입니다(marketplace `hk`).

| 플러그인 | 기능 | 호출(Claude Code / Codex) | 문서 |
| --- | --- | --- | --- |
| `synthesis` | RTL 프로젝트 생성, Icarus 검증, ASAP7(기본)·Nangate45·사용자 Liberty로 Yosys 합성 | `/synthesis:asap7`, `/synthesis:nangate45` / `$synthesis asap7`, `$synthesis nangate45` | [README](plugins/synthesis/skills/synthesis/README.md) |
| `arm-style-trm-typst` | ARM 형식 기술 매뉴얼(Typst)을 작성하고 `doc/`에 PDF 생성 | `/arm-style-trm-typst:arm-style-manual` / `$arm-style-manual` | [README](plugins/arm-style-trm-typst/README.md) |
| `util` | 일회성 유틸리티 모음(아래 목록) | `/util:util` / `$util` | [README](plugins/util/README.md) |

## util 목록

`/util:util`(Codex `$util`)을 인자 없이 호출하면 이 목록을 보여 줍니다. 항목을 바로 고르려면 Claude Code는 `/util:<이름>`, Codex는 `$util <이름>`을 씁니다.

| 유틸리티 | 하는 일 | 호출 | 절차 |
| --- | --- | --- | --- |
| `ssh-connect` | SSH 서버 등록, 별도 터미널에서 사용자가 직접 비밀번호·OTP 인증, 같은 연결로 원격 명령 실행, 파일 업로드·다운로드, 연결 종료 | `/util:ssh-connect` / `$util ssh-connect` | [ssh-connect](plugins/util/skills/util/references/ssh-connect.md) |

MIT License. 서드파티 자산은 각 위치의 라이선스를 따릅니다.
