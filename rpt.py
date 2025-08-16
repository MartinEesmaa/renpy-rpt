#!/usr/bin/env python3
import os
import re
import sys
import argparse
from glob import glob

# Match either '$ name = Character(' or 'define name = Character('
DEFINE_RE = re.compile(
    r'^\s*(?:\$|define)\s+(?P<short>\w+)\s*=\s*Character\(',
    re.MULTILINE
)

def quote(s: str) -> str:
    """
    Escape backslashes and newlines for .rpt format.
    """
    s = s.replace("\\", "\\\\")
    s = s.replace("\n", "\\n")
    return s

def gather_char_names(rpy_files):
    """
    Scan the given .rpy files for character definitions.
    Returns a list of unique short names.
    """
    names = []
    for path in rpy_files:
        text = open(path, encoding="utf-8").read()
        for m in DEFINE_RE.finditer(text):
            short = m.group("short")
            if short not in names:
                names.append(short)
    return names

def build_patterns(char_names):
    """
    Build regexes for single- and multi-line dialogues using the provided names.
    """
    pattern = "|".join(re.escape(n) for n in char_names)
    single_re = re.compile(
        rf'^\s*(?P<char>{pattern})\s+"(?P<text>(?:[^"\\]|\\.)*)"',
        re.MULTILINE
    )
    multi_re = re.compile(
        rf'^\s*(?P<char>{pattern})\s+"""\s*\n(?P<text>.*?)\s*"""',
        re.MULTILINE | re.DOTALL
    )
    return single_re, multi_re

def extract_dialogues(rpy_path, single_re, multi_re):
    """
    Extract raw dialogue strings and menu choices from one .rpy file using the given regexes.
    """
    content = open(rpy_path, encoding="utf-8").read()
    dialogues = []

    for m in single_re.finditer(content):
        raw = m.group("text").encode("utf-8").decode("unicode_escape")
        dialogues.append(raw.strip())

    for m in multi_re.finditer(content):
        raw = m.group("text")
        lines = [ln.rstrip() for ln in raw.splitlines()]
        dialogues.append("\n".join(lines).strip())

    menu_choice_re = re.compile(r'^\s*"([^"]+)"\s*:', re.MULTILINE)
    for m in menu_choice_re.finditer(content):
        choice = m.group(1).strip()
        dialogues.append(choice)

    return dialogues

def extract_screen_texts(screens_path):
    """
    Extracts all label and textbutton texts wrapped in _() from screens.rpy.
    Returns a list of strings.
    """
    with open(screens_path, encoding="utf-8") as f:
        content = f.read()
    # Match label _("...") and textbutton _("...") with double quotes
    pattern = re.compile(r'(label|textbutton)\s+_\("([^"]+)"\)')
    return [m.group(2) for m in pattern.finditer(content)]

def deduplicate_rpt(filepath):
    """
    Deduplicate < ... > blocks in the .rpt file, keeping only the first occurrence of each source line.
    """
    seen = set()
    output_lines = []
    with open(filepath, encoding="utf-8") as fin:
        lines = fin.readlines()

    i = 0
    while i < len(lines):
        if lines[i].startswith("< "):
            src = lines[i][2:].rstrip()
            if src not in seen:
                seen.add(src)
                output_lines.append(lines[i].replace('\n', '\r\n'))  # Ensure set CRLF default
                # Expect the next line to be the translation line
                if i + 1 < len(lines) and lines[i+1].startswith(">"):
                    output_lines.append(lines[i+1].replace('\n', '\r\n'))
                    i += 2
                else:
                    i += 1
                # Add any blank lines after
                while i < len(lines) and lines[i].strip() == "":
                    output_lines.append(lines[i].replace('\n', '\r\n'))
                    i += 1
            else:
                # Skip this block (source + translation + blank lines)
                i += 1
                while i < len(lines) and (lines[i].startswith(">") or lines[i].strip() == ""):
                    i += 1
        else:
            output_lines.append(lines[i].replace('\n', '\r\n'))
            i += 1

    with open(filepath, "w", encoding="utf-8", newline="") as fout:
        fout.writelines(output_lines)

def main():
    parser = argparse.ArgumentParser(
        description="""Generate a Ren’Py .rpt translation template from dialogues used before 6.15.
(C) 2025 Martin Eesmaa (MIT licensed)""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-i","--input-dir",
        default="game",
        help="Root directory containing .rpy files (default: game)"
    )
    parser.add_argument(
        "-o","--output-file",
        default="translations.rpt",
        help="Output .rpt file (default: translations.rpt)"
    )
    parser.add_argument(
        "-f","--fill-template",
        action="store_true",
        help="Copy source text into translation lines (default: False)"
    )
    args = parser.parse_args()

    # 1. Read .rpy files
    pattern = os.path.join(args.input_dir, "**", "*.rpy")
    rpy_files = glob(pattern, recursive=True)
    if not rpy_files:
        sys.exit("Error: No .rpy files found under '{}'.".format(args.input_dir))

    # Check for screens.rpy first
    screens_path = os.path.join(args.input_dir, "screens.rpy")
    if os.path.isfile(screens_path):
        print("Processing label & button texts from screens.rpy...")
        label_texts = extract_screen_texts(screens_path)
        with open(args.output_file, "w", encoding="utf-8", newline="\n") as fout:
            # Write screens.rpy texts
            if not label_texts:
                print("Warning: No label or button texts are found in screens.rpy.")
            else:
                for orig in label_texts:
                    q_orig  = quote(orig)
                    q_trans = quote(orig) if args.fill_template else ""
                    fout.write(f"< {q_orig}\n")
                    fout.write(f"> {q_trans}\n\n")
                print(f"Extracted {len(label_texts)} texts → {args.output_file}")
            # Add empty slots from Load screen
            for i in range(1, 10):
                orig = f" {i}. Empty Slot."
                q_orig  = quote(orig)
                q_trans = quote(orig) if args.fill_template else ""
                fout.write(f"< {q_orig}\n")
                fout.write(f"> {q_trans}\n\n")
            # Add quit confirm message for exit window during in the game or menus.
            orig = "Are you sure you want to quit?"
            q_orig  = quote(orig)
            q_trans = quote(orig) if args.fill_template else ""
            fout.write(f"< {q_orig}\n")
            fout.write(f"> {q_trans}\n\n")
            # Add joystick configuration section
            joystick_lines = [
                "Joystick Configuration",
                "Left - Axis 0.0 Negative",
                "Right - Axis 0.0 Positive",
                "Up - Axis 0.1 Negative",
                "Down - Axis 0.1 Positive",
                "Select/Dismiss - Button 0.0",
                "Rollback - Not Assigned",
                "Hold to Skip - Not Assigned",
                "Toggle Skip - Not Assigned",
                "Hide Text - Not Assigned",
                "Menu - Button 0.7",
                "Joystick Mapping - Left",
                "Joystick Mapping - Right",
                "Joystick Mapping - Up",
                "Joystick Mapping - Down",
                "Joystick Mapping - Select/Dismiss",
                "Joystick Mapping - Rollback",
                "Joystick Mapping - Hold to Skip",
                "Joystick Mapping - Toggle Skip",
                "Joystick Mapping - Hide Text",
                "Joystick Mapping - Menu",
                "Move the joystick or press a joystick button to create the mapping. Click the mouse to remove the mapping."
            ]
            for orig in joystick_lines:
                q_orig  = quote(orig)
                q_trans = quote(orig) if args.fill_template else ""
                fout.write(f"< {q_orig}\n")
                fout.write(f"> {q_trans}\n\n")
    else:
        print("Warning: screens.rpy not found, moving to script.rpy and other files.")
        # If screens.rpy is missing, still create/clear the output file
        open(args.output_file, "w", encoding="utf-8").close()

    # 2. Read script.rpy
    script_path = os.path.join(args.input_dir, "script.rpy")
    if script_path in rpy_files:
        rpy_files.remove(script_path)
        rpy_files.insert(0, script_path)

    # 3. Discover character names from definitions
    char_names = gather_char_names(rpy_files)
    if not char_names:
        sys.exit("Error: No character definitions ('$' or 'define') found in any .rpy files.")

    # 4. Build dialogue extraction patterns
    single_re, multi_re = build_patterns(char_names)

    # 5. Extract dialogues
    all_texts = []
    for path in rpy_files:
        all_texts.extend(extract_dialogues(path, single_re, multi_re))

    # 6. Deduplicate and validate
    seen = set()
    unique_texts = []
    for t in all_texts:
        if t and t not in seen:
            seen.add(t)
            unique_texts.append(t)
    if not unique_texts:
        sys.exit("Error: No dialogue lines are found from .rpy files.")

    # 7. Write .rpt
    # Append script dialogues after screens.rpy and extra lines
    with open(args.output_file, "a", encoding="utf-8", newline="") as fout:
        for orig in unique_texts:
            q_orig  = quote(orig)
            q_trans = quote(orig) if args.fill_template else ""
            fout.write(f"< {q_orig}\r\n")
            fout.write(f"> {q_trans}\r\n\r\n")

    # Deduplicate the .rpt file after writing everything
    deduplicate_rpt(args.output_file)

    print(f"Detected characters: {', '.join(char_names)}")
    print(f"Extracted {len(unique_texts)} lines → {args.output_file}")

if __name__ == "__main__":
    main()