# renpy-rpt

renpy-rpt is a Python tool to generate dialogues from Ren'Py before version 6.15.

This tool allows to create template translation from any languages or your language.

Created by Martin Eesmaa (2025)

## To work this:

You need Python and copy `rpt.py` file to your game project and run the command:

For example:

```
python rpt.py
```

This will use default values to scan game directory, outputs to translations.rpt file and empty pre-translated texts.

## Help usage:

```
usage: rpt.py [-h] [-i INPUT_DIR] [-o OUTPUT_FILE] [-f]

Generate a Ren’Py .rpt translation template from dialogues used before 6.15.
(C) 2025 Martin Eesmaa (MIT licensed)

options:
  -h, --help            show this help message and exit
  -i INPUT_DIR, --input-dir INPUT_DIR
                        Root directory containing .rpy files (default: game)
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Output .rpt file (default: translations.rpt)
  -f, --fill-template   Copy source text into translation lines (default: False)
```

- Martin Eesmaa