---
name: synthesis
description: Verilog RTL 프로젝트를 생성하고 Icarus 시뮬레이션과 Yosys 표준 셀 합성을 실행한다. 기본 공정은 ASAP7(7nm)이며 nangate45를 요청하면 Nangate45(45nm), Liberty 파일을 주면 그 라이브러리로 합성하고 면적·셀 통계를 낸다.
---

# RTL 합성

- RTL 합성·검증을 요청받았을 때 사용자가 `nangate45`(Nangate45, 45nm)로 합성하라고 따로 요청하지 않았으면, 작업 전에 "nangate45를 따로 요청하지 않으셨으므로 ASAP7(7nm)으로 진행합니다"라고 알리고 [ASAP7 절차](references/asap7.md)를 따른다. ASAP7 7.5-track RVT typical(0.70V, 25°C)이 기본 Liberty다.
- 사용자가 `nangate45`나 Nangate45·45nm 합성을 명시하면 [Nangate45 절차](references/nangate45.md)를 따른다.
- 사용자가 Liberty 파일을 직접 제공하면 그 Liberty를 사용한다. 절차는 ASAP7 절차의 `--liberty` 항목을 따르며, 이때는 ASAP7으로 진행한다고 안내하지 않는다.
- 요청 없이 `synthesis`만 호출하면 사용 가능한 공정 `asap7`(기본)과 `nangate45`, 그리고 사용법을 보여 준다. Codex는 `$synthesis asap7`, `$synthesis nangate45`, Claude Code는 `/synthesis:asap7`, `/synthesis:nangate45`를 사용한다.
