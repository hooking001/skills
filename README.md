# hooking001 skills

Claude Code와 Codex에서 함께 쓰는 공개 스킬 모음입니다(marketplace `hk`).

| 플러그인 | 기능 | 호출(Claude Code / Codex) | 문서 |
| --- | --- | --- | --- |
| `synthesis` | RTL 프로젝트 생성, Icarus 검증, ASAP7(기본)·Nangate45·사용자 Liberty로 Yosys 합성 | `/synthesis:asap7`, `/synthesis:nangate45` / `$synthesis asap7`, `$synthesis nangate45` | [README](plugins/synthesis/skills/synthesis/README.md) |
| `arm-style-trm-typst` | ARM 형식 기술 매뉴얼(Typst)을 작성하고 `doc/`에 PDF 생성 | `/arm-style-trm-typst:arm-style-manual` / `$arm-style-manual` | [README](plugins/arm-style-trm-typst/README.md) |

MIT License. 서드파티 자산은 각 위치의 라이선스를 따릅니다.
