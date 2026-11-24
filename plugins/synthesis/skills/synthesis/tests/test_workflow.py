"""Behavior checks; actual EDA integration runs when tools are installed."""
import contextlib
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import manage
import rtl_flow

ASAP7_LIB = "asap7sc7p5t_28_RVT_TT.lib"
ASAP7_LEFS = ("asap7_tech_1x_201209.lef", "asap7sc7p5t_28_R_1x_220121a.lef")
NANGATE_FILES = ("NangateOpenCellLibrary_typical.lib", "NangateOpenCellLibrary.tech.lef",
                 "NangateOpenCellLibrary.macro.mod.lef")


def liberty(name, template, cells, extra=""):
    """A tiny single-library Liberty text shaped like the ASAP7 category files."""
    groups = "".join('  cell (%s) {\n    area : 1;\n    pin (A) {\n      direction : input;\n    }\n  }\n'
                     % cell for cell in cells)
    return ("/*\nlicense\n*/\n\nlibrary (%s) {\n  time_unit : \"1ps\";\n"
            "  lu_table_template (%s) {\n    variable_1 : input_net_transition;\n"
            "    index_1 (\"5, 10\");\n  }\n%s%s}\n" % (name, template, extra, groups))


def setUpModule():
    # Bundled libraries live in a download cache, not in git; fetch them once.
    with contextlib.redirect_stdout(io.StringIO()):
        manage.download(manage.lib_dir())


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rtl flow test ")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def cli(self, *args, ok=True, env=None):
        result = subprocess.run([str(a) for a in args], cwd=str(self.work),
                                env=env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout[-6000:])
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def project(self, *extra, name="design"):
        self.cli(sys.executable, ROOT / "scripts/manage.py", "setup", name,
                 self.work, "--top", "counter_top", *extra)
        return self.work / name

    def execute(self, project, script, *args, **kwargs):
        return self.cli("bash", project / script, *args, **kwargs)

    def test_shell_syntax(self):
        for script in ROOT.rglob("*.sh"):
            self.cli("/bin/bash", "-n", script)

    def test_existing_project_preserved(self):
        project = self.project()
        rtl = project / "rtl/counter_top.v"
        rtl.write_text("user RTL\n")
        self.cli(sys.executable, ROOT / "scripts/manage.py", "setup", "design",
                 self.work, ok=False)
        self.assertEqual(rtl.read_text(), "user RTL\n")

    def test_invalid_identifiers_rejected_without_creation(self):
        for name in ("../escape", "a-b", "a;write", "1bad"):
            self.cli(sys.executable, ROOT / "scripts/manage.py", "setup", name,
                     self.work, ok=False)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_default_project_is_asap7(self):
        project = self.project()
        config = json.loads((project / "project.json").read_text())
        self.assertEqual(config["pdk"], "asap7")
        self.assertEqual(config["liberty"], "lib/" + ASAP7_LIB)
        self.assertEqual(config["dont_use"], ["DFFHQx4_ASAP7_75t_R", "DFFLQx4_ASAP7_75t_R"])
        for name in (ASAP7_LIB, "ASAP7-LICENSE") + ASAP7_LEFS:
            self.assertTrue((project / "lib" / name).is_file(), name)
        self.assertFalse(any((project / "lib").glob("Nangate*")))

    def test_nangate45_project_on_request(self):
        project = self.project("--pdk", "nangate45")
        config = json.loads((project / "project.json").read_text())
        self.assertEqual(config["pdk"], "nangate45")
        self.assertEqual(config["liberty"], "lib/NangateOpenCellLibrary_typical.lib")
        self.assertNotIn("dont_use", config)
        for name in NANGATE_FILES + ("NANGATE-LICENSE",):
            self.assertTrue((project / "lib" / name).is_file(), name)
        self.assertFalse(any((project / "lib").glob("asap7*")))

    def test_custom_liberty_copied_and_project_relocatable(self):
        liberty_file = self.work / "custom corner.lib"
        liberty_file.write_text("custom library contents")
        project = self.project("--liberty", liberty_file)
        liberty_file.unlink()
        moved = self.work / "moved project"
        project.rename(moved)
        config = json.loads((moved / "project.json").read_text())
        self.assertEqual(config["pdk"], "custom")
        self.assertNotIn("dont_use", config)
        self.assertEqual(sorted(p.name for p in (moved / "lib").iterdir()), ["custom corner.lib"])
        self.assertEqual((moved / config["liberty"]).read_text(), "custom library contents")
        self.assertTrue((moved / "script/rtl_flow.py").is_file())
        self.assertFalse(any(p.is_symlink() for p in moved.rglob("*")))
        self.execute(moved, "clean.sh")

    def test_invalid_dont_use_rejected_before_synthesis(self):
        project = self.project()
        config_path = project / "project.json"
        config = json.loads(config_path.read_text())
        for bad in (["DFF; write_verilog /tmp/x"], "DFFHQx4_ASAP7_75t_R", [1]):
            config["dont_use"] = bad
            config_path.write_text(json.dumps(config))
            result = self.execute(project, "script/run_synth.sh", ok=False)
            self.assertIn("dont_use", result.stdout)
        self.assertFalse((project / "synth/counter_top_synth.v").exists())

    def test_filelists_spaces_comments_crlf_and_no_final_newline(self):
        source = self.work / "source file.sv"
        source.write_text("module a; endmodule\n")
        listing = self.work / "rtl.f"
        listing.write_bytes(b'# comment\r\n// comment\r\n\r\n"source file.sv"')
        self.assertEqual(rtl_flow.filelist(listing), [source.resolve()])
        listing.write_text("-f other.f\n")
        with self.assertRaises(ValueError):
            rtl_flow.filelist(listing)

    def test_bundled_assets_match_manifests(self):
        with contextlib.redirect_stdout(io.StringIO()):
            manage.download(manage.lib_dir())

    def test_asap7_merge_defines_every_template_and_keeps_all_cells(self):
        parts = []
        for i, (name, template, cells) in enumerate((("SIMPLE", "delay_x1", ["AND2x2"]),
                                                     ("SEQ", "delay", ["DFFHQNx1", "DHLx1"]),
                                                     ("AO", "delay_x1", ["AO21x1"]))):
            path = self.work / ("part%d.lib" % i + (".gz" if i != 1 else ""))
            text = liberty(name, template, cells).encode("ascii")
            path.write_bytes(gzip.compress(text) if path.name.endswith(".gz") else text)
            parts.append(path)
        merged = manage.merge_asap7_liberties(parts).decode("ascii")
        self.assertIn("library (asap7sc7p5t_28_RVT_TT) {", merged)
        self.assertEqual(merged.count("library ("), 1)
        self.assertEqual(merged.count("lu_table_template (delay_x1)"), 1)
        self.assertEqual(merged.count("lu_table_template (delay)"), 1)
        self.assertLess(merged.index("lu_table_template (delay)"), merged.index("cell (AND2x2)"))
        self.assertEqual(manage.CELL_NAME.findall(merged), ["AND2x2", "DFFHQNx1", "DHLx1", "AO21x1"])
        self.assertTrue(merged.endswith("  }\n}\n"))
        self.assertEqual(merged.count("{"), merged.count("}"))
        self.assertEqual(manage.merge_asap7_liberties(parts).decode("ascii"), merged)

        conflict = self.work / "conflict.lib"
        conflict.write_text(liberty("OA", "delay_x1", ["OA21x2"]).replace('"5, 10"', '"5, 20"'))
        with self.assertRaisesRegex(ValueError, "Conflicting Liberty template"):
            manage.merge_asap7_liberties([parts[0], conflict])
        duplicate = self.work / "duplicate.lib"
        duplicate.write_text(liberty("OA", "delay_x1", ["AND2x2"]))
        with self.assertRaisesRegex(ValueError, "Duplicate Liberty cell"):
            manage.merge_asap7_liberties([parts[0], duplicate])

    def synthetic_asap7(self):
        """A manifest and an upstream mirror built from tiny ASAP7-shaped files."""
        mirror = self.work / "mirror"
        mirror.mkdir()
        files = {"lib/NLDM/a.lib.gz": gzip.compress(liberty("A", "t1", ["INVx1"]).encode()),
                 "lib/NLDM/b.lib": liberty("B", "t2", ["DFFHQNx1"]).encode(),
                 "lef/cells.lef": b"MACRO INVx1\nEND INVx1\n"}
        for path, data in files.items():
            (mirror / Path(path).name).write_bytes(data)
        parts = [mirror / "a.lib.gz", mirror / "b.lib"]
        merged = hashlib.sha256(manage.merge_asap7_liberties(parts)).hexdigest()
        data = {"base_url": "https://example.invalid", "revision": "0",
                "files": [{"path": p, "sha256": hashlib.sha256(d).hexdigest()} for p, d in files.items()],
                "merged": {"filename": "merged.lib", "sha256": merged}}
        fetched = []

        def fetch(command, **kwargs):
            fetched.append(command[-3])
            shutil.copyfile(str(mirror / command[-3].rsplit("/", 1)[1]), command[-1])
        return data, fetch, fetched

    def test_asap7_download_merges_and_publishes_after_verification(self):
        data, fetch, fetched = self.synthetic_asap7()
        lib = self.work / "lib"
        with mock.patch.object(manage.subprocess, "run", side_effect=fetch), \
                contextlib.redirect_stdout(io.StringIO()):
            manage.download_asap7(lib, data)
            self.assertEqual(sorted(p.name for p in lib.iterdir()), ["cells.lef", "merged.lib"])
            self.assertEqual(manage.digest(lib / "merged.lib"), data["merged"]["sha256"])
            # Only the missing LEF is fetched again; the merged library is kept.
            (lib / "cells.lef").unlink()
            fetched.clear()
            manage.download_asap7(lib, data)
        self.assertEqual([url.rsplit("/", 1)[1] for url in fetched], ["cells.lef"])

    def test_asap7_download_failure_leaves_no_partial_file(self):
        data, fetch, _ = self.synthetic_asap7()
        data["merged"]["sha256"] = "0" * 64
        lib = self.work / "lib"
        with mock.patch.object(manage.subprocess, "run", side_effect=fetch):
            with self.assertRaisesRegex(ValueError, "Checksum mismatch for assembled"):
                manage.download_asap7(lib, data)
        # The verified LEF was staged too, but nothing is published on failure.
        self.assertEqual(list(lib.iterdir()), [])

    def test_checksum_mismatch_preserves_file(self):
        for pdk, name in (("nangate45", NANGATE_FILES[0]), ("asap7", ASAP7_LIB)):
            lib = self.work / pdk
            lib.mkdir()
            damaged = lib / name
            damaged.write_text("corrupt")
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"), \
                    contextlib.redirect_stdout(io.StringIO()):
                manage.download(lib, pdk=pdk)
            self.assertEqual(damaged.read_text(), "corrupt")

    def test_download_validates_before_publishing(self):
        manifest = json.loads((ROOT / "resources/library.json").read_text())

        def fetch(command, **kwargs):
            target = Path(command[-1])
            shutil.copyfile(str(manage.lib_dir() / target.name), str(target))

        with mock.patch.object(manage.subprocess, "run", side_effect=fetch), contextlib.redirect_stdout(io.StringIO()):
            manage.download(self.work, pdk="nangate45")
        for item in manifest["files"]:
            self.assertEqual(manage.digest(self.work / Path(item["path"]).name), item["sha256"])

    def test_download_failure_leaves_no_partial_file(self):
        def corrupt(command, **kwargs):
            Path(command[-1]).write_text("HTML instead of library")

        with mock.patch.object(manage.subprocess, "run", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                manage.download(self.work, pdk="nangate45")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_nangate45_download_script_ignores_asap7(self):
        lib = self.work / "lib"
        lib.mkdir()
        for name in NANGATE_FILES:
            shutil.copyfile(str(manage.lib_dir() / name), str(lib / name))
        result = self.cli("bash", ROOT / "scripts/download_nangate45.sh", lib)
        self.assertEqual(result.stdout.count("Verified"), 3)
        self.assertNotIn("asap7", result.stdout)
        self.assertEqual(sorted(p.name for p in lib.iterdir()), sorted(NANGATE_FILES))

    @unittest.skipUnless(os.environ.get("SYNTHESIS_NETWORK_TESTS") == "1", "set SYNTHESIS_NETWORK_TESTS=1")
    def test_network_asap7_download_reproduces_bundle(self):
        lib = self.work / "lib"
        with contextlib.redirect_stdout(io.StringIO()):
            manage.download(lib, pdk="asap7")
        for name in (ASAP7_LIB,) + ASAP7_LEFS:
            self.assertEqual(manage.digest(lib / name), manage.digest(manage.lib_dir() / name))

    def test_clean_only_owned_outputs_and_rejects_escape(self):
        project = self.project()
        notes = project / "synth/notes.txt"
        notes.write_text("keep")
        owned = project / "synth/test_synth.v"
        owned.write_text("generated")
        rtl_flow.reserve(project, [owned])
        self.execute(project, "clean.sh")
        self.assertEqual(notes.read_text(), "keep")
        self.assertFalse(owned.exists())
        (project / ".rtl-flow-outputs.json").write_text('["../outside.txt"]')
        self.execute(project, "clean.sh", ok=False)

    def test_symlinked_output_rejected(self):
        project = self.project()
        external = self.work / "external"
        external.write_text("keep")
        link = project / "synth/counter_top_synth.v"
        link.symlink_to(external)
        with self.assertRaises(ValueError):
            rtl_flow.reserve(project, [link])
        self.assertEqual(external.read_text(), "keep")

    def test_install_is_explicit_and_non_destructive(self):
        destination = self.work / "skills"
        self.cli("bash", ROOT / "install.sh", "--destination", destination)
        installed = destination / "synthesis"
        self.assertTrue((installed / "SKILL.md").is_file())
        self.assertTrue((installed / "references/nangate45.md").is_file())
        self.assertTrue((installed / "references/asap7.md").is_file())
        self.assertFalse((installed / ".git").exists())
        self.assertFalse((installed / ".serena").exists())
        self.assertFalse(any(p.is_symlink() for p in installed.rglob("*")))
        self.cli("bash", ROOT / "install.sh", "--destination", destination, ok=False)
        self.cli("bash", installed / "scripts/setup_project.sh", "installed_project", self.work)
        config = json.loads((self.work / "installed_project/project.json").read_text())
        self.assertEqual(config["pdk"], "asap7")

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"), "Icarus not installed")
    def test_real_simulation_and_failure_exit(self):
        project = self.project()
        result = self.execute(project, "script/run_tb.sh")
        self.assertIn("PASS:", result.stdout)
        tb = project / "tb/counter_top_tb.v"
        tb.write_text(tb.read_text().replace("((i + 1) & 15)", "((i + 2) & 15)"))
        self.execute(project, "script/run_tb.sh", ok=False)

    @unittest.skipUnless(shutil.which("yosys"), "Yosys not installed")
    def test_real_sequential_mapping_in_space_path_and_failed_rerun(self):
        for pdk, cell in (("asap7", "DFFASRHQNx1_ASAP7_75t_R"), ("nangate45", "DFFR_X1")):
            with self.subTest(pdk=pdk):
                project = self.project("--pdk", pdk, name="design_" + pdk)
                self.execute(project, "script/run_synth.sh")
                netlist = project / "synth/counter_top_synth.v"
                self.assertIn(cell, netlist.read_text())
                report = (project / "synth/counter_top_synth_report.txt").read_text()
                self.assertIn("Chip area", report)
                script = (project / "synth/synth_counter_top.ys").read_text()
                self.assertEqual("-dont_use DFFHQx4_ASAP7_75t_R" in script, pdk == "asap7")
                rtl = project / "rtl/counter_top.v"
                rtl.write_text("invalid Verilog")
                self.execute(project, "script/run_synth.sh", ok=False)
                self.assertFalse(netlist.exists())

    def run_example(self, name, cell):
        project = self.work / (name + " copy")
        shutil.copytree(str(ROOT / "example" / name), str(project), symlinks=False,
                        ignore=shutil.ignore_patterns("synth", "dump", "lib", ".rtl-flow-outputs.json"))
        # Examples keep lib/ out of git; run_all.sh downloads it, the test copies it from the cache.
        (project / "lib").mkdir()
        pdk = json.loads((project / "project.json").read_text())["pdk"]
        for filename in manage.pdk_assets(pdk)[0]:
            shutil.copy2(str(manage.lib_dir() / filename), str(project / "lib" / filename))
        # Reuse the canonical runner with this independent example copy.
        for command in ("tb", "synth"):
            result = self.cli(sys.executable, ROOT / "scripts/rtl_flow.py", "--project", project, command)
            if command == "tb":
                self.assertIn("All 512 test cases PASSED", result.stdout)
        self.assertIn(cell, (project / "synth/full_adder_4bit_synth.v").read_text())

    @unittest.skipUnless(all(shutil.which(t) for t in ("yosys", "iverilog", "vvp")), "EDA tools not installed")
    def test_real_adder_example(self):
        self.run_example("full_adder_4bit", "_X1")

    @unittest.skipUnless(all(shutil.which(t) for t in ("yosys", "iverilog", "vvp")), "EDA tools not installed")
    def test_real_asap7_adder_example(self):
        self.run_example("full_adder_4bit_asap7", "_ASAP7_75t_R")


if __name__ == "__main__":
    unittest.main()
