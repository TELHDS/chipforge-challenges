#!/usr/bin/env python3
import argparse, json, re, shutil, subprocess
from pathlib import Path

def read_txt(p: Path) -> str:
    try:
        return p.read_text(errors="ignore")
    except Exception:
        return ""

def patch_config_from_rtl_f(config_json: Path, rtl_f: Path, sdc_file: Path):
    cfg = json.loads(config_json.read_text())
    files = []
    if rtl_f.exists():
        for line in read_txt(rtl_f).splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            files.append(f"dir::{s}")
    if files:
        cfg["VERILOG_FILES"] = files
    cfg["BASE_SDC_FILE"] = f"dir::{sdc_file.name}"
    config_json.write_text(json.dumps(cfg, indent=2))

def parse_period_from_sdc(sdc: Path):
    txt = read_txt(sdc)
    m = re.search(r"-period\s+([\d.]+)", txt)
    return float(m.group(1)) if m else None

def parse_area(stat_file: Path):
    txt = read_txt(stat_file)
    for line in txt.splitlines():
        if "Chip area for module" in line:
            nums = re.findall(r"([\d.]+)", line)
            if nums:
                return float(nums[-1])
    return None

def parse_wns(sta_file: Path):
    txt = read_txt(sta_file)
    for line in txt.splitlines():
        if "slack" in line:
            for tok in line.replace("(", " ").replace(")", " ").split():
                try:
                    return float(tok)
                except ValueError:
                    continue
            break
    return None

def run_flow(flow_tcl: Path, design_dir: Path, config_json: Path):
    cmd = ["tclsh", str(flow_tcl), "-design", str(design_dir), "-config", str(config_json)]
    run = subprocess.run(cmd, cwd=design_dir, capture_output=True, text=True)
    if run.returncode != 0:
        raise RuntimeError(f"flow.tcl failed:\nSTDOUT:\n{run.stdout}\n\nSTDERR:\n{run.stderr}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", required=True, help="path to extracted design dir")
    ap.add_argument("--out", required=True, help="output dir (API will zip this)")
    args = ap.parse_args()

    design_dir = Path(args.design).resolve()
    out_dir    = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # evaluator dir is the folder containing run.py
    eval_dir = Path(__file__).resolve().parent

    # --- OpenLane root + designs dir ---
    openlane_root = Path("/openlane")
    designs_root  = openlane_root / "designs"
    design_name   = design_dir.name
    design_target = designs_root / design_name

    if design_target.exists():
        shutil.rmtree(design_target)
    shutil.copytree(design_dir, design_target)

    # Copy evaluator resources
    flow_tcl = eval_dir / "flow.tcl"
    config_json_template = eval_dir / "config.json"
    constraints_sdc = eval_dir / "constraints.sdc"

    shutil.copy(flow_tcl, openlane_root / "flow.tcl")
    shutil.copy(config_json_template, design_target / "config.json")
    shutil.copy(constraints_sdc, design_target / "constraints.sdc")

    # Patch config.json with RTL
    patch_config_from_rtl_f(design_target / "config.json",
                            design_target / "rtl.f",
                            design_target / "constraints.sdc")

    # Run flow
    run_flow(openlane_root / "flow.tcl", design_target, design_target / "config.json")

    # Locate latest run
    runs_root = design_target / "runs"
    latest = None
    if runs_root.exists():
        candidates = [p for p in runs_root.glob("*") if p.is_dir()]
        latest = max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None
    if latest is None:
        raise RuntimeError("No OpenLane runs found under design/runs")

    syn_stat = latest / "reports" / "synthesis" / "1-synthesis.DELAY_3.stat.rpt"
    syn_sta  = latest / "reports" / "synthesis" / "2-syn_sta.max.rpt"

    area_um2 = parse_area(syn_stat)
    period_ns = parse_period_from_sdc(design_target / "constraints.sdc")
    wns_ns = parse_wns(syn_sta)

    fmax_mhz = None
    if period_ns is not None and wns_ns is not None:
        ach = period_ns - wns_ns
        if ach > 0:
            fmax_mhz = 1000.0 / ach

    # Save reports into output dir
    rep_src = latest / "reports"
    rep_dst = out_dir / "reports"
    if rep_src.exists():
        if rep_dst.exists():
            shutil.rmtree(rep_dst)
        shutil.copytree(rep_src, rep_dst)

    result = {
        "area_um2": area_um2,
        "sdc_period_ns": period_ns,
        "wns_ns": wns_ns,
        "fmax_mhz": fmax_mhz,
        "run_dir": str(latest)
    }

    (out_dir / "results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))  # stdout JSON

if __name__ == "__main__":
    main()
