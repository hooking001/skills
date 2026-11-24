# arm-style-trm-typst

설치(Claude Code 2.1.275+):

```text
/plugin install arm-style-trm-typst --marketplace hooking001/skills
```

`arm-style-manual` 스킬로 ARM 참조 매뉴얼 형식의 한영 기술 문서를 Typst로 작성하고, 프로젝트의 `doc/`에 PDF를 만듭니다. Typst가 필요합니다. 폰트(Pretendard Regular·Medium·Bold)는 번들로 포함되어 있습니다.

편집용 파일은 매뉴얼별 하위 디렉터리에 둡니다.

```text
doc/
  uart_manual.pdf
  uart_manual/
    main.typ
    build.sh
    template/
    fonts/
```

템플릿 회귀 검사는 `python3 skills/arm-style-manual/assets/scripts/manual.py test`로 실행합니다.
