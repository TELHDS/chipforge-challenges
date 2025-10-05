#!/usr/bin/env python3
import argparse
import json
import subprocess
import re
import sys
from pathlib import Path

# Regex for extracting functionality score from simulator output
FUNC_RE = re.compile(r'FUNC_SCORE:\s*([0-9]*\.?[0-9]+)')

def run_cmd(cmd, cwd):
    """Run shell command and capture output"""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr

def extract_func_score(output: str):
    """Parse FUNC_SCORE=X.X from simulator output"""
    m = FUNC_RE.search(output)
    if m:
        try:
            val = float(m.group(1))
            return max(0.0, min(1.0, val))  # clamp 0..1
        except Exception:
            return None
    return None

def main():
    parser = argparse.ArgumentParser(description="Evaluator: run Verilator simulation and compute functionality score")
    parser.add_argument("--design", required=True, help="Path to extracted design directory")
    parser.add_argument("--resources", required=True, help="Path to evaluator bundle (with tb_files.f, top_module.txt)")
    args = parser.parse_args()

    design_dir = Path(args.design)
    resources  = Path(args.resources)

    # ---------------------------
    # Get top module name
    # ---------------------------
    top_file = resources / "top_module.txt"
    if not top_file.exists():
        print(json.dumps({
            "success": False,
            "error_message": f"top_module.txt not found in resources"
        }))
        sys.exit(1)

    top_module = top_file.read_text().strip()

    # ---------------------------
    # Locate rtl.f
    # ---------------------------
    filelist = design_dir / "rtl.f"
    if not filelist.exists():
        print(json.dumps({
            "success": False,
            "error_message": f"rtl.f not found in design directory"
        }))
        sys.exit(1)

    # ---------------------------
    # Collect testbench files
    # ---------------------------
    tb_list = resources / "tb_files.f"
    if not tb_list.exists():
        print(json.dumps({
            "success": False,
            "error_message": f"tb_files.f not found in resources"
        }))
        sys.exit(1)

    tb_files = []
    for line in tb_list.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        tb_files.append(str((resources / s).resolve()))

    # ---------------------------
    # Step 1: Verilator compile
    # ---------------------------
    verilator_cmd = [
        "verilator",
        "--timing", "--binary", "-Wall",
        "--Wno-fatal",
        "--top-module", top_module,
        "--cc", "--exe",
        "-CFLAGS", "-std=c++17",
        "-f", str(filelist),
    ] + tb_files + ["--trace"]

    rc, out_compile = run_cmd(verilator_cmd, cwd=design_dir)
    if rc != 0:
        print(json.dumps({
            "success": False,
            "error_message": "Verilator compile failed",
            "verilator_log": out_compile
        }))
        sys.exit(1)

    # ---------------------------
    # Step 2: Make build
    # ---------------------------
    makefile = f"V{top_module}.mk"
    rc, out_make = run_cmd(["make", "-C", "obj_dir", "-j", "-f", makefile], cwd=design_dir)
    if rc != 0:
        print(json.dumps({
            "success": False,
            "error_message": "Make failed when building simulation",
            "verilator_log": out_make
        }))
        sys.exit(1)

    # ---------------------------
    # Step 3: Run simulation
    # ---------------------------
    exe = design_dir / f"obj_dir/V{top_module}"
    rc, sim_out = run_cmd([str(exe)], cwd=design_dir)
    if rc != 0:
        print(json.dumps({
            "success": False,
            "error_message": "Simulation failed",
            "verilator_log": sim_out
        }))
        sys.exit(1)

    # ---------------------------
    # Extract functionality score
    # ---------------------------
    func_score = extract_func_score(sim_out)

    result = {
        "success": True,
        "functionality_score": func_score if func_score is not None else 0.0,
        "details": {
            "note": "Evaluator ran simple Verilator simulation",
            "design": str(design_dir),
            "top_module": top_module,
            "tb_files": tb_files,
        },
        "simulation_output": sim_out
    }

    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
