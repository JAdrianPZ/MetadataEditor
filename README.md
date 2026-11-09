# Metadata Editor

This tool allows you to edit image metadata, such as checkpoints, LORAs. So far windows only, working on more options.
![Image of the UI](https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/dfe6ce9f-755d-461a-86fc-ca352174d9a2/width=525/dfe6ce9f-755d-461a-86fc-ca352174d9a2.jpeg) 

## Download Here
   [Windows V1.1](https://github.com/JAdrianPZ/MetadataEditor/releases/download/V1.1/main_ui.exe)
 

## Features

- **Model family profiles:** SD 1.5, SDXL, Pony, Illustrious, NoobAI, FLUX.1,
  FLUX.2, Qwen-Image, Z-Image, SD 3.5, MOSS-Image, and Other / preserve original.
  Variants are optional and editable. Switching profiles does not overwrite your
  steps, CFG, seed, sampler, or scheduler. Unknown models remain unclassified.
  MOSS JSON layout prompts remain structured when LoRAs are added.
- **Basic model controls:** The main model name, Civitai version reference and
  optional local file selection are all in Basic. Hash editing and LoRAs are in Advanced.
- **Hash activity:** Each main-model or LoRA hash calculation displays an animated
  progress bar and filename while the editor stays responsive. Bars clear on success
  or failure. Advanced groups explain sampling settings, model identification and LoRAs;
  Basic includes a shortcut to those settings.
- **Generation editor:** Select the family, edit the prompt and generation values,
  and review the exact text before exporting. FLUX guidance is separate from CFG.
- **Civitai resource references:** Enter a model or LoRA version ID (or a URL
  containing `modelVersionId`). A model page ID alone is not a version ID.
  Names and file-based hash calculation are optional; LoRA weights are editable.
- **Safe PNG copies:** Export to a different filename. Existing PNG text, EXIF,
  color profile and DPI are preserved when available. Original metadata is shown
  separately; recognized parameters populate the form automatically.

Run `python main_ui.py`, open an image, choose its model family and optional variant,
and edit the fields. Sampler, scheduler and resource references are under
**Advanced**. Use the values from your actual generation workflow;
FLUX variants can use different guidance settings. Save with **Save PNG copy**.
The exported `parameters` text uses A1111-style fields, including
`Distilled CFG Scale`, `Lora hashes` and `Civitai resources` when supplied.
Resource recognition must still be checked in Civitai's upload preview; local
tests do not verify the live service. Existing executables must be rebuilt.

The editor focuses on readable, editable generation text and resource references.
It does not import or reconstruct ComfyUI node workflows. If an external image
has no supported `parameters` or EXIF generation text, enter its prompt, settings,
main model and LoRAs manually. All LoRA rows include editable weight, version
reference and file hash. Names alone do not establish a Civitai resource match;
the resource notice indicates where identifiers are missing.

### Optional Civitai compatibility check

The desktop editor only requires Python. Developers can additionally use Node.js
20+ and Civitai's official `@civitai/generation-metadata` parser locally:

```powershell
npm ci --prefix tools --ignore-scripts
.\.venv\Scripts\python.exe tools/build_compatibility_fixtures.py
node tools/test-civitai.mjs
node tools/validate-civitai.mjs "C:\path\exported-image.png"
```

These checks read local files without uploading them or querying resource IDs.
The fixtures use synthetic identifiers to check encoding, not actual model matches.
Checks cover prompts, settings, model and LoRA references using IDs, hashes, or both.
The export uses A1111-compatible text, so a parser may label its format Automatic1111
regardless of which application originally generated the image.

- **Image Preview:** Load and preview images for metadata editing.
- **Metadata Extraction:** Extract existing metadata from PNG/JPG images.
- **LORA Management:** Add, remove, and edit multiple LORAs and their hashes for proper metadata formatting.
- **Civitai-Compatible Metadata:** Insert metadata in a format that Civitai recognizes, including prompts, samplers, and more.
- **Model Selection:** Select a model file, and the tool automatically extracts its hash and name.
- **Editable Metadata Preview:** See the full metadata structure and modify it if necessary.
- **Drag and Drop Support:** Drag and drop images into the interface for quick editing.


## Installation (For developers)

### Prerequisites
1. **Python 3.11+**: Required by Pillow 13. Use a maintained Python release.
2. **Tkinter**: Ensure that Tkinter is properly installed (comes preinstalled with Python).
3. **venv (optional)**: It's recommended to use a virtual environment to avoid conflicts with system-wide packages.

### Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/JAdrianPZ/MetadataEditor.git
   cd MetadataEditor
   ```
2.  **Create a venv (optional but recomended)**:
    ```bash
    python -m venv myenv
    ```
3. **Copy TCL**: Copy the "tcl" folder of your python installation into the venv like this: myenv\tlc

4. **Edit activate.bat**:
    *myenv\Scripts\activate.bat, Add this lines before the END and save*
   ```bash
    set TCL_LIBRARY=%VIRTUAL_ENV%\tcl\tcl8.6
    set TK_LIBRARY=%VIRTUAL_ENV%\tcl\tk8.6
   ```

4. **Activate venv**:
   ```bash
   myenv\Scripts\activate
   ```

5. **Install requirments**:
   ```bash
   pip install -r requirements.txt
   ```
6.  **RUN THE APP**:
    ```bash
    python main_ui.py
    ```
### Steps for compile a .exe

Rebuild the executable after dependency security updates. Existing executables
still contain the versions bundled when they were built.

1. **Install requirments**:
   ```bash
   pip install pyinstaller
   ```
2.**Compile**:
 ```bash
    pyinstaller --onefile --windowed --icon=meta.ico --collect-all tkinterdnd2 main_ui.py
```

## Dependency security checks

To inspect image metadata independently of the UI (without changing the image):

```powershell
.\.venv\Scripts\python.exe extract_metadata.py "C:\path\image.png"
```

The readable text output includes Pillow's image info and EXIF, including nested EXIF and
GPS tags. `parameters_found` indicates whether the field currently read by the UI
is present. Other metadata can exist even when that field is absent. This is a
Pillow-based diagnostic, not an exhaustive forensic metadata scanner.
Use `--json` for structured JSON output. Binary blocks are summarized by size,
and Unicode EXIF comments are decoded into text.

Install dependencies in a clean virtual environment, then run:

```bash
python -m pip install -r requirements.txt
python -m pip install pip-audit
python -m pip_audit -r requirements.txt
python -m unittest discover -s tests
```

Dependabot checks for dependency updates weekly. Review and test its pull requests
before merging. The executable uses the tkdnd library bundled with tkinterdnd2;
do not package the legacy tkdnd ZIP instead.
