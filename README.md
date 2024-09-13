# Metadata Editor

This tool allows you to edit image metadata, such as checkpoints, LORAs. So far windows only, working on more options.
![Image of the UI](https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/dfe6ce9f-755d-461a-86fc-ca352174d9a2/width=525/dfe6ce9f-755d-461a-86fc-ca352174d9a2.jpeg) 

## Download Here
   [Windows V1.1](https://github.com/JAdrianPZ/MetadataEditor/releases/download/V1.1/main_ui.exe)
 

## Features

- **Image Preview:** Load and preview images for metadata editing.
- **Metadata Extraction:** Extract existing metadata from PNG/JPG images.
- **LORA Management:** Add, remove, and edit multiple LORAs and their hashes for proper metadata formatting.
- **Civitai-Compatible Metadata:** Insert metadata in a format that Civitai recognizes, including prompts, samplers, and more.
- **Model Selection:** Select a model file, and the tool automatically extracts its hash and name.
- **Editable Metadata Preview:** See the full metadata structure and modify it if necessary.
- **Drag and Drop Support:** Drag and drop images into the interface for quick editing.


## Installation (For developers)

### Prerequisites
1. **Python 3.10**: Ensure Python 3.10 or later is installed on your system.
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

1. **Install requirments**:
   ```bash
   pip install pyinstaller
   ```
2.**Compile**:
 ```bash
    pyinstaller --onefile --windowed --icon=meta.ico main_ui.py --add-binary "C:\{Path to the folder i include as a zip (tkdnd)}\;tkdnd2.9.2"
    #example: pyinstaller --onefile --windowed --icon=meta.ico main_ui.py --add-binary "C:\Users\user1\Documents\tkdnd2.9.2;tkdnd2.9.2"
```

 