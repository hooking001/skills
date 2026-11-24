# ASAP7(7nm) 기반 RTL 합성과 검증

ASAP7은 이 스킬의 기본 공정이다. 사용자가 nangate45를 따로 요청하지 않았으면 ASAP7으로 진행한다고 먼저 알린다. 기본 Liberty는 ASAP7 7.5-track RVT typical(0.70V, 25°C)이다. 다른 공정·코너는 사용자가 제공한 Liberty를 `--liberty`로 명시적으로 선택한다. `<skill>`은 `synthesis/SKILL.md`가 있는 디렉터리다.

## 작업 선택

- **새 프로젝트**: `bash <skill>/scripts/setup_project.sh <name> [parent] [--top <module>] [--liberty <file>]`. `--pdk`를 생략하면 `asap7`이다. 이름과 top은 단순 Verilog 식별자여야 한다. 기존 경로를 덮어쓰지 않는다. 생성된 프로젝트는 라이브러리와 실행 코드를 복사하므로 스킬을 옮기거나 지운 뒤에도 독립적으로 동작한다.
- **기존 RTL 합성**: 사용자의 프로젝트 구조를 먼저 확인한다. 생성기가 기존 RTL을 덮어쓰게 하지 말고, 별도 작업 디렉터리를 만든 뒤 `script/rtl.f`와 `project.json`을 실제 설계에 맞춘다. 사용자가 선택한 top과 라이브러리를 보존한다.
- **예제 확인**: `bash <skill>/example/full_adder_4bit_asap7/run_all.sh`. Icarus로 512개 입력을 전수 검사한 뒤 Yosys 합성을 수행하며, 어느 단계든 실패하면 실패로 종료한다.

## 실행 계약

Python 3.8+, Bash, Yosys(ABC 포함), Icarus Verilog(`iverilog`, `vvp`)를 PATH에서 찾는다. curl은 라이브러리를 처음 내려받을 때 필요하다. 고정된 Homebrew 경로를 추가하거나 패키지를 자동 설치하지 않는다. 실행 파일 경로는 `YOSYS`, `IVERILOG`, `VVP` 환경변수로 지정할 수 있다.

생성 프로젝트의 `project.json`에는 다음 항목이 있다.

- `pdk`: `asap7`, `nangate45`, 또는 `--liberty`를 쓴 경우 `custom`. 기록용이며 실행기는 이 값을 읽지 않는다.
- `top`, `tb_top`
- `liberty`: 프로젝트 루트 기준 경로.
- `dont_use`: ASAP7 프로젝트에만 기록되는 선택 항목.

`script/rtl.f`와 `script/tb.f`에는 한 줄에 소스 파일 경로를 하나씩 적고, 상대 경로는 각 파일리스트의 위치를 기준으로 해석한다. 공백 경로, 빈 줄, CRLF, 전체 줄 `#`/`//` 주석을 지원한다. 옵션, glob, 중첩 파일리스트, 인라인 주석은 지원하지 않는다. 옵션이나 복잡한 SystemVerilog 기능이 필요한 설계는 기존 빌드 시스템을 사용하거나 실행기를 명시적으로 확장한다. `.sv`는 `read_verilog -sv`로 읽지만 Yosys 기본 프런트엔드의 SystemVerilog 지원은 제한적이다.

```bash
bash <project>/script/run_tb.sh                  # project.json의 tb_top
bash <project>/script/run_synth.sh               # project.json의 top과 liberty
bash <project>/script/run_synth.sh other_top --liberty lib/other_corner.lib
bash <project>/script/run_tb.sh other_top --tb-top other_top_tb
bash <project>/clean.sh
```

실행 위치는 자유롭다. 시뮬레이션 cwd는 `script/`이므로 테스트벤치 파형은 `../dump/<top>.vcd`에 기록한다. top을 바꾸면 테스트벤치도 함께 지정한다. `clean.sh`는 실행기가 기록한 출력만 지우며 임의의 파형 경로는 추적하지 않는다.

## ASAP7 셀 매핑

- `dont_use` 기본값은 `["DFFHQx4_ASAP7_75t_R", "DFFLQx4_ASAP7_75t_R"]`이다. 이 값이 없으면 Yosys가 모든 레지스터를 큰 Q 출력 x4 플롭으로 매핑한다. 이 값을 두면 QN 출력 x1 플롭과 인버터로 매핑되어 셀 면적 합계가 4~13% 줄어든다. 목록은 `dfflibmap`과 `abc`에 `-dont_use`로 전달된다. 항목은 셀 이름이나 `*`·`?` glob이며, 빈 목록 `[]`로 바꾸면 Yosys 기본 선택으로 돌아간다.
- 매핑되는 순차 셀:
  - 일반 플롭: `DFFHQNx1`(rising edge), `DFFLQNx1`(falling edge)
  - 비동기 리셋·셋: `DFFASRHQNx1`. 사용하지 않는 셋/리셋 입력은 상수로 묶인다.
  - 래치: `DHLx1`(high transparent), `DLLx1`(low transparent)
  - 동기 리셋과 enable: 플롭 앞의 조합 논리로 구현된다.
  - 메모리 배열: 매크로가 없으므로 플롭과 mux로 풀린다.
- ICG(클록 게이팅)와 SDF(스캔) 셀은 자동으로 쓰지 않는다.
- Yosys 0.71에서 검증했다. QN 출력 플롭을 다루지 못하는 오래된 Yosys에서는 매핑이 `check -mapped -assert`에서 실패로 보고된다.

## 합성 결과 판단

실행기는 다음 순서로 매핑과 구조 검사를 수행한다.

1. `synth -flatten -noabc`
2. `delete t:$scopeinfo`
3. `dfflibmap`
4. `abc`
5. 라이브러리 셀 로드
6. `check -mapped -assert`
7. `stat -liberty`

미매핑 내부 셀이나 잘못된 연결은 성공으로 보고하지 않는다. 실패한 재실행에서는 이전 넷리스트를 제거한다.

- `synth/<top>_synth.v`: `*_ASAP7_75t_R` 표준 셀로 매핑된 넷리스트
- `synth/<top>_synth_report.txt`: 전체 도구 로그와 최종 셀 통계
- `synth/synth_<top>.ys`: 재현 가능한 Yosys 명령

보고할 때 도구 버전, top, 소스 목록, 사용한 Liberty·코너, `dont_use`를 확인한다. 로그 중간의 일반 합성 통계가 아니라 **마지막 Liberty 기반 통계**를 사용한다. 셀 수는 논리 게이트 환산치가 아니다. 면적은 Liberty 셀 면적의 합계이며 ASAP7 1x 스케일 기준 µm²다. 이 결과로 타이밍 충족, 실제 배치 면적, 전력, RTL-넷리스트 등가성을 단정하지 않는다. 게이트 시뮬레이션에는 Liberty가 아닌 별도 Verilog 셀 모델이 필요하다. 스킬 테스트는 `read_liberty -ignore_miss_func`로 셀 모델을 만들어 넷리스트를 검증한다(README의 검증 항목 참조).

## 라이브러리 복구 및 상세 안내

라이브러리는 git에 넣지 않는다. `setup_project.sh`가 처음 실행될 때 사용자 캐시(`$SYNTHESIS_LIB_DIR`, 기본 `~/.cache/synthesis/lib`)에 한 번 내려받고, 이후에는 캐시를 검증해 사용한다. 첫 실행에는 네트워크가 필요하다. `bash <skill>/scripts/download_asap7.sh [directory]`의 동작은 다음과 같다.

- [고정 커밋·SHA-256 목록](../resources/library_asap7.json)으로 캐시(또는 지정 디렉터리)의 병합 Liberty와 LEF 2개를 검증한다.
- 빠진 파일만 고정 커밋에서 받는다. 병합 Liberty가 없으면 원본 카테고리 Liberty 5개를 받아 결정적으로 병합한다.
- 모든 해시가 맞은 뒤에만 파일을 배치한다.
- 기존 파일의 해시가 다르면 그 파일을 보존하고 실패한다. 원인을 확인한 뒤 별도 디렉터리로 복구한다.

플랫폼 준비, 설치, 지원 범위와 검증 방법은 필요할 때 [README.md](../README.md)를 참조한다. 자산 출처와 원본 라이선스는 [resources/PROVENANCE.md](../resources/PROVENANCE.md)와 [resources/ASAP7-LICENSE](../resources/ASAP7-LICENSE)에 보존되어 있다.
