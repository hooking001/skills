# hooking001 skills

Claude Code와 Codex에서 함께 쓰는 공개 스킬 모음입니다.

| 플러그인 | 기능 | 문서 |
| --- | --- | --- |
| `synthesis` | RTL 프로젝트 생성, Icarus 검증, ASAP7(기본)·Nangate45·사용자 Liberty로 Yosys 합성 | [README](plugins/synthesis/skills/synthesis/README.md) |
| `arm-style-trm-typst` | ARM 형식 기술 매뉴얼(Typst)을 작성하고 `doc/`에 PDF 생성 | [README](plugins/arm-style-trm-typst/README.md) |
| `util` | 일회성 유틸리티. `ssh-connect`로 서버 등록·접속·원격 명령·파일 전송 | [README](plugins/util/README.md) |

## 설치

Claude Code:

```text
/plugin marketplace add hooking001/skills
/plugin install synthesis@hk
# 또는 한 번에(2.1.275+): /plugin install synthesis --marketplace hooking001/skills
```

Codex:

```text
codex plugin marketplace add https://github.com/hooking001/skills.git --ref main
codex plugin add synthesis@hk
```

새 세션에서 다음 명령으로 실행합니다.

| Claude Code | Codex |
| --- | --- |
| `/synthesis:asap7`, `/synthesis:nangate45` | `$synthesis asap7`, `$synthesis nangate45` |
| `/arm-style-trm-typst:arm-style-manual` | `$arm-style-manual` |
| `/util:util`, `/util:ssh-connect` | `$util`, `$util ssh-connect` |

## 구조와 기여

```text
.claude-plugin/marketplace.json   # 플러그인 목록과 버전(버전은 여기서만 관리)
plugins/<plugin>/
  commands/                       # /플러그인:명령 으로 직접 호출하는 항목(선택)
  skills/<skill>/SKILL.md         # 스킬 지침
  skills/<skill>/references/      # 필요할 때 읽는 절차
scripts/check.sh                  # 매니페스트 검증과 전체 테스트
```

변경 후 `scripts/check.sh`를 실행하고, 바뀐 플러그인의 `version`을 올립니다. `interface`는 Codex 전용 필드라서 `claude plugin validate`에서 경고가 나올 수 있지만 무시해도 됩니다.

MIT License. 서드파티 자산은 각 위치의 라이선스를 따릅니다.
