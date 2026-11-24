"""Synthesis regression over tests/cases for ASAP7, plus a Nangate45 smoke run.

Each case goes through a generated standalone project: RTL simulation, Yosys
synthesis, checks on the mapped netlist, and gate-level simulation of that
netlist with the same testbench and Verilog cell models that Yosys derives from
the same Liberty file.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = Path(__file__).resolve().parent / "cases"
sys.path.insert(0, str(ROOT / "scripts"))
from rtl_flow import quote  # noqa: E402

# case: (top, RTL files in the case directory, ASAP7 cell patterns that must appear)
CASES = {
    "alu8": ("alu8", ["alu8.v"], []),
    "mult8": ("mult8", ["mult8.v"], []),
    "ff_styles": ("ff_styles", ["ff_styles.v"], [r"DFFASRHQNx1", r"DFFHQNx\d", r"DFFLQNx\d"]),
    "latches": ("latches", ["latches.v"], [r"DHLx\d", r"DLLx\d"]),
    "fsm_seqdet": ("fsm_seqdet", ["fsm_seqdet.v"], [r"DFFASRHQNx1"]),
    "regfile8x8": ("regfile8x8", ["regfile8x8.v"], [r"DFFHQNx\d"]),
    "hier_generate": ("hier_generate", ["rca.v", "hier_generate.v"], [r"DFFASRHQNx1"]),
    "sv_fsm": ("sv_fsm", ["sv_fsm.sv"], [r"DFFASRHQNx1"]),
    "const_passthrough": ("const_passthrough", ["const_passthrough.v"], []),
}
PDKS = ("asap7", "nangate45")
INSTANCE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_$]*)\s+(?:\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\(", re.M)
ASAP7_DONT_USE = re.compile(r"DFF[HL]Qx4_ASAP7_75t_R")


@unittest.skipUnless(all(shutil.which(t) for t in ("yosys", "iverilog", "vvp")), "EDA tools not installed")
class SynthesisCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="synthesis cases ")
        cls.work = Path(cls.temp.name)
        cls.projects = {}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_tool(self, *args):
        result = subprocess.run([str(a) for a in args], cwd=str(self.work), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(result.returncode, 0, result.stdout[-6000:])
        return result.stdout

    def project(self, pdk):
        """One generated project per PDK, shared by its cases, and its cell models."""
        if pdk not in self.projects:
            self.run_tool(sys.executable, ROOT / "scripts/manage.py", "setup", pdk, self.work, "--pdk", pdk)
            project = self.work / pdk
            liberty = project / json.loads((project / "project.json").read_text())["liberty"]
            models = self.work / (pdk + "_cells.v")
            self.run_tool("yosys", "-q", "-p", "read_liberty -ignore_miss_func {}; write_verilog -noattr {}"
                          .format(quote(liberty), quote(models)))
            self.projects[pdk] = project, models
        return self.projects[pdk]

    def run_case(self, pdk, case):
        top, sources, required = CASES[case]
        project, models = self.project(pdk)
        script = project / "script"
        testbench = CASES_DIR / case / (top + "_tb.v")
        (script / (case + "_rtl.f")).write_text("".join(str(CASES_DIR / case / s) + "\n" for s in sources))
        (script / (case + "_tb.f")).write_text(str(testbench) + "\n")
        runner = [sys.executable, script / "rtl_flow.py", "--project", project]

        output = self.run_tool(*runner, "tb", top, "--tb-top", top + "_tb",
                               "--rtl-list", case + "_rtl.f", "--tb-list", case + "_tb.f")
        self.assertIn("PASS", output)

        self.run_tool(*runner, "synth", top, "--rtl-list", case + "_rtl.f")
        netlist = project / "synth" / (top + "_synth.v")
        cells = {m.group(1) for m in INSTANCE.finditer(netlist.read_text())} - {"module"}
        self.assertTrue(cells, "empty netlist")
        self.assertFalse([c for c in cells if c.startswith("$")], cells)
        report = (project / "synth" / (top + "_synth_report.txt")).read_text()
        self.assertGreater(float(re.findall(r"Chip area for (?:top )?module .*?: ([0-9.]+)", report)[-1]), 0)
        if pdk == "asap7":
            self.assertTrue(all(c.endswith("_ASAP7_75t_R") for c in cells), sorted(cells))
            self.assertFalse([c for c in cells if ASAP7_DONT_USE.fullmatch(c)], "dont_use ignored")
            for pattern in required:
                self.assertTrue(any(re.fullmatch(pattern + "_ASAP7_75t_R", c) for c in cells),
                                "{} not in {}".format(pattern, sorted(cells)))

        # The mapped netlist must pass the same self-checking testbench.
        binary = self.work / "{}_{}_gls.vvp".format(pdk, case)
        self.run_tool("iverilog", "-g2012", "-s", top + "_tb", "-o", binary, netlist, models, testbench)
        self.assertIn("PASS", self.run_tool("vvp", "-n", binary))


def _add_case(pdk, case):
    def test(self):
        self.run_case(pdk, case)
    test.__doc__ = "{} {}: RTL sim, synthesis, mapping checks, gate-level sim".format(pdk, case)
    setattr(SynthesisCaseTests, "test_{}_{}".format(pdk, case), test)


for _pdk in PDKS:
    for _case in CASES:
        _add_case(_pdk, _case)


if __name__ == "__main__":
    unittest.main()
