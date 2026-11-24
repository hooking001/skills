# synthesis · ASAP7 / Nangate45 / Liberty RTL

Linux·macOS에서 RTL 시뮬레이션, Yosys 표준 셀 매핑, 면적·셀 통계 산출과 독립 프로젝트 생성을 지원합니다. 기본 공정은 ASAP7 7.5-track RVT typical(7nm, 0.70V, 25°C)입니다. 요청하면 Nangate45 typical(45nm)이나 사용자가 준 Liberty도 쓸 수 있습니다. PnR, STA, 전력 분석은 제공하지 않습니다.

## 준비

- Python **3.8 이상**, Bash (macOS 기본 Bash 3.2 포함)
- 합성: ABC를 포함한 Yosys (ASAP7 매핑은 Yosys 0.71에서 검증)
- 시뮬레이션: Icarus Verilog (`iverilog`, `vvp`)
- 누락 라이브러리 다운로드: curl

도구는 PATH 또는 `YOSYS`, `IVERILOG`, `VVP`에 지정한 **실행 파일 경로**에서 찾습니다. 환경변수에 옵션을 함께 넣지 마세요. GNU 전용 sed/readlink/sha256sum, 고정 Homebrew 경로, 시스템 설정 변경을 요구하지 않습니다. Python은 macOS 기본 제공을 가정하지 않습니다.

Yosys와 Icarus는 Linux·macOS용 [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build)를 사용할 수 있습니다. 배포판 패키지를 사용하는 경우 해당 패키지에서 ABC도 제공하는지 확인하세요. ASAP7 플롭은 대부분 QN 출력만 있으므로 오래된 Yosys에서는 매핑이 실패할 수 있습니다. 이 경우 `check -mapped -assert`에서 실패로 보고되며, 성공으로 처리되지 않습니다.

## 사용

이 문서의 명령은 스킬 루트에서 실행합니다. 경로에 공백이 있으면 인용하세요.

```bash
# 기본 ASAP7 프로젝트. 출력 경로가 이미 존재하면 실패합니다.
bash scripts/setup_project.sh counter /path/to/work

# Nangate45 프로젝트
bash scripts/setup_project.sh counter /path/to/work --pdk nangate45

# 다른 공정·코너 및 프로젝트명과 다른 top을 선택합니다.
bash scripts/setup_project.sh counter /path/to/work --top counter_top --liberty /path/to/corner.lib

bash /path/to/work/counter/script/run_tb.sh
bash /path/to/work/counter/script/run_synth.sh
bash /path/to/work/counter/clean.sh

# 포함된 가산기: 512개 입력 검사와 합성
bash example/full_adder_4bit_asap7/run_all.sh    # ASAP7
bash example/full_adder_4bit/run_all.sh          # Nangate45
bash example/full_adder_4bit_asap7/clean.sh
```

프로젝트는 `rtl/`, `tb/`, `script/`, `lib/`, `synth/`, `dump/`, `project.json`으로 구성됩니다. 기본 RTL은 비동기 리셋을 갖는 4비트 증가기이며, 생성된 TB가 16개 입력과 리셋을 검사합니다. 생성 프로젝트에 라이브러리와 실행기를 복사하므로 원본 스킬에 의존하지 않습니다. 이 때문에 ASAP7 프로젝트는 병합 Liberty 44MB를 포함합니다. 포함된 가산기 예제는 스킬 내부의 공통 실행기를 사용하고, `run_all.sh`가 예제의 `lib/`에 라이브러리를 내려받습니다.

`project.json`의 `top`, `tb_top`, `liberty`, `dont_use`를 수정하고 `script/rtl.f`, `script/tb.f`에 소스 경로를 한 줄에 하나씩 지정합니다. `pdk`(`asap7`·`nangate45`·`custom`)는 기록용입니다. 상대 소스 경로는 해당 파일리스트 기준, 상대 Liberty 경로는 프로젝트 루트 기준입니다. 파일리스트는 공백 경로, 선택적인 바깥 인용부호, CRLF, 빈 줄, 전체 줄 `#`/`//` 주석을 허용합니다. `+incdir`, `-D`, `-f`, glob, 인라인 주석은 지원하지 않습니다. `.sv`는 Yosys `read_verilog -sv`로 읽지만 완전한 SystemVerilog 지원을 보장하지 않습니다.

ASAP7 프로젝트의 `dont_use` 기본값은 `["DFFHQx4_ASAP7_75t_R", "DFFLQx4_ASAP7_75t_R"]`입니다. 이 값을 두면 레지스터가 큰 Q 출력 x4 플롭 대신 QN 출력 x1 플롭과 인버터로 매핑되어 셀 면적 합계가 4~13% 줄어듭니다. 목록은 `dfflibmap`과 `abc`에 `-dont_use`로 전달되며, 셀 이름과 `*`·`?` glob을 받습니다. `[]`로 비우면 Yosys 기본 선택을 따릅니다.

```bash
bash /path/to/work/counter/script/run_synth.sh other_top --liberty lib/other.lib
bash /path/to/work/counter/script/run_tb.sh other_top --tb-top other_top_tb
```

실행 디렉터리는 자유롭습니다. 시뮬레이션은 `script/`에서 실행되며 기본 TB는 `../dump/<top>.vcd`를 기록합니다. 실행기는 `.rtl-flow-outputs.json`에 기록된 파일만 정리합니다. 커스텀 TB의 다른 파형 경로는 직접 관리하세요.

## 라이브러리 검증과 결과 해석

```bash
bash scripts/download_asap7.sh                       # 캐시에 ASAP7 다운로드·병합·검증
bash scripts/download_asap7.sh /path/to/new/lib      # 지정 디렉터리에 다운로드·병합·검증
bash scripts/download_nangate45.sh                   # 캐시에 Nangate45 다운로드·검증
bash scripts/download_nangate45.sh /path/to/new/lib  # 지정 디렉터리에 다운로드·검증
```

라이브러리(ASAP7 병합 Liberty 44MB 등)는 git에 포함하지 않습니다. 새 프로젝트를 만들 때 사용자 캐시(`$SYNTHESIS_LIB_DIR`, 기본 `~/.cache/synthesis/lib`)에 한 번 내려받아 플러그인 버전이 바뀌어도 다시 받지 않습니다. 첫 실행에는 `raw.githubusercontent.com` 접근이 필요합니다.

해시가 다른 기존 파일은 덮어쓰지 않습니다. 빠진 파일만 받고, 모든 해시를 확인한 뒤에만 배치합니다. 다운로드 실패나 해시 오류가 생기면 임시 파일을 폐기합니다. ASAP7 원본은 Liberty 5개 카테고리로 나뉘어 배포됩니다. 스크립트는 이를 단일 Liberty로 결정적으로 병합하고 병합 결과의 해시까지 검증합니다. 출처, 커밋, 병합 방식, 원본 라이선스는 [resources/PROVENANCE.md](resources/PROVENANCE.md)에 있습니다.

넷리스트, 전체 로그와 최종 통계, 재현 명령은 `synth/`에 저장합니다. 미매핑 셀이나 연결 오류가 있으면 실패하며, 이전 넷리스트가 성공 결과로 남지 않게 합니다. 면적은 선택한 Liberty의 셀 면적 합계입니다. ASAP7과 Nangate45에서는 µm²입니다. 이 값은 배치 면적, STA 결과, 등가성 증명이 아닙니다. 셀 수와 NAND2 환산 게이트 수를 구분하세요. 정확한 수치는 도구 버전과 최적화에 따라 달라집니다.

## 설치

마켓플레이스에서는 `synthesis` 플러그인을 설치합니다. Claude Code에서는 `/synthesis:asap7`(기본)이나 `/synthesis:nangate45`, Codex에서는 `$synthesis asap7`이나 `$synthesis nangate45`로 실행합니다. 공정을 지정하지 않고 합성을 요청하면 ASAP7으로 진행합니다. 독립 복사 설치가 필요하면 아래 명령으로 원하는 대상에 설치합니다. 기존 설치 경로는 보존합니다.

```bash
bash install.sh                                  # ${CODEX_HOME:-~/.codex}/skills/synthesis
bash install.sh --target claude                   # ~/.claude/skills/synthesis
bash install.sh --target antigravity              # ~/.gemini/config/skills/synthesis
bash install.sh --destination /path/to/skills     # /path/to/skills/synthesis
```

이전 `nangate45` 독립 설치는 새 설치를 확인한 뒤 정리할 수 있습니다. 독립 복사본에서는 `synthesis`를 호출하고 `asap7`이나 `nangate45`를 선택합니다.

## 검증

```bash
python3 -m unittest discover -s tests -v
SYNTHESIS_NETWORK_TESTS=1 python3 -m unittest discover -s tests -k network -v   # 선택: ORFS 재다운로드
```

로컬에서 다음을 검사합니다.

- 기본 동작: 생성, 이동, 덮어쓰기 거부, 체크섬, 설치, 정리, 실패 전달, 기본 PDK와 `dont_use` 기록
- ASAP7 병합: 템플릿 정의와 중복 셀 검사
- 다운로드: 검증 후 배치, 부분 파일 미잔류

EDA 도구가 있으면 다음도 실제로 실행합니다.

- 두 가산기 예제, 순차 RTL, 공백 경로, 테스트 실패와 합성 실패
- [tests/cases](tests/cases)의 회귀 케이스 9개: ALU, 8x8 곱셈기, 리셋·셋·enable·negedge 플롭, 래치, FSM, 레지스터 파일, 계층·generate, SystemVerilog, 상수 출력

각 케이스는 다음 단계를 모두 거칩니다.

1. RTL 시뮬레이션
2. ASAP7 합성
3. 최종 넷리스트 검사: 모든 셀이 ASAP7인지, 기대 순차 셀이 있는지, `dont_use`가 적용되었는지
4. 게이트 레벨 시뮬레이션: `read_liberty -ignore_miss_func`로 만든 셀 모델로 같은 자가 검사 TB를 돌린다.

같은 케이스를 Nangate45로도 합성하고 게이트 레벨 시뮬레이션합니다. 도구가 없으면 해당 통합 검사만 skip합니다. GitHub CI는 사용하지 않습니다.
