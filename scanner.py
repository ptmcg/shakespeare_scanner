import itertools
import littletable as lt
from pathlib import Path
import re

all_caps_re = re.compile(r"([A-Z ]+)\.")


def all_caps(s: str) -> str:
    if match := all_caps_re.match(s):
        return match[1]
    return ""


def scan_gutenberg_file(fname) -> lt.Table:
    play_file = Path(f"{fname}")
    raw_source = play_file.read_bytes()
    try:
        play_text = raw_source.decode("utf-8")
    except UnicodeDecodeError:
        play_text = raw_source.decode("cp1252")

    replacements = [
        ("-", "-"),
        ("—", "— "),
        ("[_", "["),
        ("_]", "]"),
    ]
    for from_, to in replacements:
        play_text = play_text.replace(from_, to)

    fname = play_file.name

    line_iter = iter(enumerate(play_text.splitlines()))

    # skip to first instance of ACT I
    line_iter = itertools.dropwhile(lambda s: s[1].lstrip().rstrip(".") != "ACT I", line_iter)

    # advance to next instance of ACT I - this is the actual start of the play
    next(line_iter)
    line_iter = itertools.dropwhile(lambda s: s[1].lstrip().rstrip(".") != "ACT I", line_iter)

    current_file = fname
    current_act = ""
    current_scene = ""
    current_scene_description = ""
    current_part = ""
    scene_line = 0
    last_is_blank = False
    last_is_stage_direction = False

    play = lt.Table()

    for lineno, line in line_iter:
        if line.strip() and line.startswith(" ") and not line.startswith("  "):
            if last_is_stage_direction:
                play[-1].line = f"{play[-1].line.rstrip()} {line.lstrip()}"
            else:
                play.insert(
                    {
                        "act": current_act,
                        "scene": current_scene,
                        "scene_line": scene_line,
                        "role": "---",
                        "file_name": current_file,
                        "file_lineno": lineno,
                        "line": line.lstrip(),
                    }
            )
            last_is_stage_direction = True
            continue
        else:
            last_is_stage_direction = False

        if not line.strip():
            last_is_blank = True
            last_is_stage_direction = False
            continue

        if line.startswith("ACT"):
            current_act = line.split()[-1].rstrip(".")
            continue

        if line.startswith("SCENE"):
            scene_label, _, scene_description = line.partition(". ")
            current_scene = scene_label.split()[-1].rstrip(".")
            current_scene_description = scene_description
            scene_line = 0
            current_part = ""
            continue

        if role := all_caps(line):
            current_part = role
            continue

        if line.startswith("*** END OF THE PROJECT GUTENBERG EBOOK"):
            break

        # assume this is a spoken line
        scene_line += 1
        play.insert(
            {
                "act": current_act,
                "scene": current_scene,
                "scene_line": scene_line,
                "role": current_part,
                "file_name": current_file,
                "file_lineno": lineno,
                "line": line.lstrip(),
            }
        )

    return play


if __name__ == '__main__':
    for source_path in Path("gutenberg").glob("*.txt"):
        source_fname = source_path.name
        print(source_fname)
        scanned = scan_gutenberg_file(source_path)
        scanned.csv_export(f"csvs/{source_fname}.csv")

    # source_fname = "gutenberg/pg1539.txt"
    # scanned = scan_gutenberg_file(source_fname)
    # scanned.csv_export(f"csvs/{source_fname}.csv")