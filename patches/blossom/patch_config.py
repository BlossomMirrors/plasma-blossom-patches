#!/usr/bin/env python3
import re
from pathlib import Path

PLASMA_CFG = Path.home() / ".config/plasma-org.kde.plasma.desktop-appletsrc"


def patch_plasma_config():
    if not PLASMA_CFG.is_file():
        return
    lines = PLASMA_CFG.read_text().splitlines(keepends=True)

    sections = []
    for i, line in enumerate(lines):
        s = line.rstrip("\n")
        if s and s[0] == "[" and s[-1] == "]":
            if sections:
                sections[-1] = (sections[-1][0], sections[-1][1], i)
            sections.append((s, i, len(lines)))

    def get_kv(header):
        for h, start, end in sections:
            if h != header:
                continue
            kv = {}
            for ln in lines[start + 1:end]:
                l = ln.rstrip("\n")
                if "=" in l and not l.startswith("#"):
                    k, _, v = l.partition("=")
                    kv[k.strip()] = v.strip()
            return kv
        return {}

    C = T = None
    for h, _, _ in sections:
        m = re.match(r"\[Containments\]\[(\d+)\]\[Applets\]\[(\d+)\]$", h)
        if m and get_kv(h).get("plugin") == "org.kde.plasma.systemtray":
            C, T = m.group(1), m.group(2)
            break
    if not C:
        return

    tray_gen     = f"[Containments][{C}][Applets][{T}][General]"
    tray_cfg_gen = f"[Containments][{C}][Applets][{T}][Configuration][General]"
    panel_gen    = f"[Containments][{C}][General]"

    standalone_ids = {
        m.group(1) for h, _, _ in sections
        for m in [re.match(rf"\[Containments\]\[{C}\]\[Applets\]\[(\d+)\]$", h)]
        if m and m.group(1) != T and get_kv(h).get("plugin") == "org.kde.plasma.battery"
    }
    max_id = max(
        (int(g) for h, _, _ in sections
         for pat in [r"\[Containments\]\[(\d+)\]\[Applets\]\[(\d+)\]", r"\[Containments\]\[(\d+)\]$"]
         for mm in [re.match(pat, h)] if mm for g in mm.groups()),
        default=0,
    )
    new_bat_id = None if standalone_ids else str(max_id + 1)
    bat_id_to_place = next(iter(standalone_ids), None) or new_bat_id

    clock_id = next(
        (mm.group(1) for h2, _, _ in sections
         for mm in [re.match(rf"\[Containments\]\[{C}\]\[Applets\]\[(\d+)\]$", h2)]
         if mm and get_kv(h2).get("plugin") == "org.kde.plasma.digitalclock"),
        None,
    )

    result = []
    for header, start, end in sections:
        for i in range(start, end):
            line = lines[i]
            s = line.rstrip("\n")
            if header in (tray_gen, tray_cfg_gen):
                for key in ("extraItems", "knownItems"):
                    if s.startswith(key + "="):
                        items = [x for x in s[len(key) + 1:].split(",")
                                 if x.strip() not in ("org.kde.plasma.battery", "")]
                        line = key + "=" + ",".join(items) + "\n"
                        break
                if s.startswith("shownItems="):
                    line = "shownItems=\n"
            if header == panel_gen and s.startswith("AppletOrder="):
                order = [x for x in s[len("AppletOrder="):].split(";") if x]
                if bat_id_to_place:
                    if bat_id_to_place in order:
                        order.remove(bat_id_to_place)
                    if clock_id and clock_id in order:
                        order.insert(order.index(clock_id), bat_id_to_place)
                    else:
                        order.append(bat_id_to_place)
                line = "AppletOrder=" + ";".join(order) + "\n"
            result.append(line)

    if new_bat_id:
        insert_idx = next(
            (i + 1 for i, l in enumerate(result)
             if re.match(rf"\[Containments\]\[{C}\]\[Applets\]\[", l.rstrip("\n"))),
            len(result),
        )
        result[insert_idx:insert_idx] = [
            f"\n[Containments][{C}][Applets][{new_bat_id}]\n",
            "plugin=org.kde.plasma.battery\n",
        ]

    PLASMA_CFG.write_text("".join(result))


if __name__ == "__main__":
    patch_plasma_config()
