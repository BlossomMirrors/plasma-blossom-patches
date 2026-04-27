#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
UPSTREAM    = SCRIPT_DIR / "upstream"
PATCHES_DIR = SCRIPT_DIR / "patches"
BUILD_ROOT  = SCRIPT_DIR / "build"
OUT_DIR     = BUILD_ROOT / "out"

TARGETS = {
    "plasma-workspace": {
        "src":    UPSTREAM / "plasma-workspace",
        "patches": PATCHES_DIR / "plasma-workspace",
        "outputs": [
            {
                "cmake_target": "org.kde.plasma.systemtray",
                "glob": "*systemtray*.so",
                "out_name": "org.kde.plasma.systemtray.so",
            },
            {
                "cmake_target": "plasmashell",
                "glob": "bin/plasmashell",
                "out_name": "plasmashell",
            },
        ],
    },
    "powerdevil": {
        "src":    UPSTREAM / "powerdevil",
        "patches": PATCHES_DIR / "powerdevil",
        "outputs": [
            {
                "cmake_target": "org.kde.plasma.battery",
                "glob": "*battery*.so",
                "out_name": "org.kde.plasma.battery.so",
            },
        ],
    },
}

COPY_TARGETS = {
    "plasma-desktop": {
        "patches": PATCHES_DIR / "plasma-desktop",
        "files": {
            "PanelConfiguration.qml": Path("/usr/share/plasma/shells/org.kde.plasma.desktop/contents/configuration/PanelConfiguration.qml"),
            "DesktopEditMode.qml":    Path("/usr/share/plasma/shells/org.kde.plasma.desktop/contents/views/DesktopEditMode.qml"),
        },
    },
    "blossom": {
        "patches": PATCHES_DIR / "blossom",
        "files": {
            "patch_config.py": Path("/usr/lib/plasma-patches-blossom/patch_config.py"),
        },
    },
}


def run(cmd, **kw):
    kw.setdefault("check", True)
    return subprocess.run(cmd, **kw)


def check_submodules():
    for name, t in TARGETS.items():
        if not (t["src"] / "CMakeLists.txt").is_file():
            sys.exit(
                f"Submodule upstream/{name} not initialised.\n"
                f"Run: git submodule update --init --depth 1 upstream/{name}"
            )


def apply_patches(src_copy: Path, patches_dir: Path):
    patches = sorted(patches_dir.glob("*.patch"))
    for p in patches:
        print(f"  applying {p.name}")
        run(["patch", "-p1", "--no-backup-if-mismatch", "-i", str(p)], cwd=src_copy)


def build_target(name: str, t: dict, force: bool):
    outputs = t["outputs"]
    out_files = [OUT_DIR / o["out_name"] for o in outputs]

    if all(f.is_file() for f in out_files) and not force:
        print(f"[{name}] already built — skipping (use --force to rebuild)")
        return

    work_src   = BUILD_ROOT / f"{name}-src"
    work_build = BUILD_ROOT / f"{name}-build"

    print(f"[{name}] copying source …")
    if work_src.exists():
        shutil.rmtree(work_src)
    shutil.copytree(t["src"], work_src, symlinks=True)

    print(f"[{name}] applying patches …")
    apply_patches(work_src, t["patches"])

    print(f"[{name}] configuring …")
    work_build.mkdir(parents=True, exist_ok=True)
    run([
        "cmake", str(work_src),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_TESTING=OFF",
        "-DCMAKE_SKIP_INSTALL_RULES=ON",
    ], cwd=work_build)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for output in outputs:
        out_file = OUT_DIR / output["out_name"]
        if out_file.is_file() and not force:
            print(f"[{name}] {output['out_name']} already built — skipping")
            continue
        print(f"[{name}] building {output['cmake_target']} …")
        run([
            "cmake", "--build", ".",
            "--target", output["cmake_target"],
            "-j", str(os.cpu_count() or 4),
        ], cwd=work_build)
        built = next(BUILD_ROOT.rglob(output["glob"]), None)
        if built is None:
            sys.exit(f"[{name}] {output['out_name']} not found after build")
        shutil.copy2(built, out_file)
        if shutil.which("chrpath"):
            subprocess.run(["chrpath", "-d", str(out_file)], capture_output=True)
        print(f"[{name}] → {out_file}")


def build_copy_target(name: str, t: dict, force: bool):
    for fname in t["files"]:
        out = OUT_DIR / fname
        if out.is_file() and not force:
            print(f"[{name}] {fname} already staged — skipping (use --force to restage)")
            continue
        src = t["patches"] / fname
        if not src.is_file():
            sys.exit(f"[{name}] source file not found: {src}")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        print(f"[{name}] → {out}")


def main():
    force = "--force" in sys.argv
    all_targets = {**TARGETS, **COPY_TARGETS}
    targets = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not targets:
        targets = list(all_targets.keys())

    cmake_targets = [t for t in targets if t in TARGETS]
    copy_targets  = [t for t in targets if t in COPY_TARGETS]
    unknown       = [t for t in targets if t not in all_targets]
    if unknown:
        sys.exit(f"Unknown target(s): {', '.join(unknown)}. Available: {', '.join(all_targets)}")

    if cmake_targets:
        check_submodules()
        for name in cmake_targets:
            build_target(name, TARGETS[name], force)

    for name in copy_targets:
        build_copy_target(name, COPY_TARGETS[name], force)

    print("Build complete. Artifacts in", OUT_DIR)


if __name__ == "__main__":
    main()
