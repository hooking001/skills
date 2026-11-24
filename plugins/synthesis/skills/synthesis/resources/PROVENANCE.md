# Asset provenance

## Nangate45

세 Liberty/LEF 파일은 The OpenROAD Project의 [OpenROAD-flow-scripts Nangate45 플랫폼](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/tree/d0e5b3c13e4bb9bdbd33493d5e87656dcae66384/flow/platforms/nangate45)과 바이트 단위로 일치합니다. 커밋과 SHA-256은 [library.json](library.json)에 기록되어 있습니다. 커밋 갱신 시 원본 세 파일을 다시 확인하고 이 목록도 함께 갱신하세요.

상위 플랫폼의 원본 `LICENSE`를 [NANGATE-LICENSE](NANGATE-LICENSE)에 그대로 보존했습니다. 자산 내부의 저작권·상표 고지도 유지합니다. 새 Nangate45 프로젝트에는 이 라이선스를 라이브러리와 함께 복사합니다. 사용자 지정 Liberty의 라이선스는 해당 라이브러리의 조건을 따릅니다.

## ASAP7

ASAP7 7.5-track 표준 셀 라이브러리(RVT, TT, NLDM) 자산은 같은 커밋의 [OpenROAD-flow-scripts ASAP7 플랫폼](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/tree/d0e5b3c13e4bb9bdbd33493d5e87656dcae66384/flow/platforms/asap7)에서 가져옵니다. 원본 7개 파일의 경로와 SHA-256, 그리고 병합 결과의 SHA-256은 [library_asap7.json](library_asap7.json)에 기록되어 있습니다.

- `asap7_tech_1x_201209.lef`, `asap7sc7p5t_28_R_1x_220121a.lef`: 원본과 바이트 단위로 일치합니다.
- `asap7sc7p5t_28_RVT_TT.lib`: 원본 Liberty 5개를 결정적으로 병합한 파생 파일입니다. 원본 카테고리는 `SIMPLE`, `INVBUF`, `SEQ`, `AO`, `OA`이며, 앞의 4개는 `.lib.gz`입니다.
  - 병합하는 이유: Yosys `dfflibmap`·`abc`·`stat`에 Liberty 하나만 넘기기 위해서입니다.
  - 헤더: 첫 파일(`SIMPLE`)의 라이선스 주석과 library 속성을 쓰고, library 이름은 `asap7sc7p5t_28_RVT_TT`로 바꿉니다.
  - 템플릿: 다른 파일에만 정의된 `lu_table_template`·`power_lut_template`를 덧붙입니다. 예를 들어 `SEQ`의 `delay_template_7x7`, `power_template_7x7`, `passive_power_template_7x1`이 해당하며, 덕분에 모든 셀의 템플릿 참조가 해석됩니다.
  - 셀: 모든 셀 그룹을 manifest 순서대로 원문 그대로 이어 붙입니다.
  - 충돌: 같은 이름의 템플릿 본문이 다르거나 셀 이름이 중복되면 실패합니다.
  - 차이: 각 파일 헤더의 `default_max_transition` 차이(`SIMPLE` 4000ps, 나머지 320ps)는 첫 파일 값을 따릅니다. 셀 핀의 `max_transition`은 원본 그대로입니다.
  - 재현: `scripts/download_asap7.sh <새 디렉터리>`는 원본을 받아 같은 병합을 수행하고 결과 해시를 검증합니다. 2026-11-24에 이 방식으로 번들 파일과의 일치를 확인했습니다.

ASAP7 자산은 Lawrence T. Clark, Vinay Vashishtha, Arizona State University의 BSD 3-Clause License를 따릅니다. 해당 플랫폼 디렉터리에는 별도 `LICENSE` 파일이 없습니다. [ASAP7-LICENSE](ASAP7-LICENSE)는 원본 Liberty 파일의 머리 주석에 있는 라이선스 원문(Copyright 2020)과 같습니다. 셀 LEF의 머리 주석(Copyright 2022)과 병합 Liberty의 머리 주석도 그대로 유지합니다. 새 ASAP7 프로젝트에는 이 라이선스를 라이브러리와 함께 복사합니다.

합성 순서와 검사 명령 참고: [Yosys technology mapping](https://yosyshq.readthedocs.io/projects/yosys/en/latest/using_yosys/synthesis/techmap_synth.html), [check](https://yosyshq.readthedocs.io/projects/yosys/en/latest/cmd/check.html).
