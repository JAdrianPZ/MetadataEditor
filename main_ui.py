import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
from PIL import Image, ImageTk
import os, sys
import threading
from tkinterdnd2 import DND_FILES, TkinterDnD
from utils import (
    load_existing_metadata,
    save_sd_metadata_to_png,
    select_model,
    get_model_hash_and_name
)

# Functions for managing LORAs
def add_lora():
    lora_frame = tk.Frame(loras_frame, bg="#f0f0f0")
    lora_frame.pack(fill=tk.X, pady=5)

    lora_path = tk.StringVar()
    lora_hash = tk.StringVar()

    def select_lora_file():
        file_path = filedialog.askopenfilename(
            title="Select LORA File",
            filetypes=[("LORA Files", "*.ckpt *.safetensors")]
        )
        if file_path:
            lora_name = os.path.basename(file_path).split('.')[0]  # Extract the file name without extension
            lora_path.set(lora_name)
            hash_val, _ = get_model_hash_and_name(file_path)
            lora_hash.set(hash_val)
            update_metadata_preview()

    lora_button = tk.Button(lora_frame, text="Select LORA", command=select_lora_file, bg="#d0eaff", fg="#333", activebackground="#b0d4f1")
    lora_button.pack(side=tk.LEFT, padx=5)

    lora_display = tk.Label(lora_frame, textvariable=lora_path, bg="#f0f0f0")
    lora_display.pack(side=tk.LEFT, padx=5)

    lora_hash_label = tk.Label(lora_frame, text="Hash:", bg="#f0f0f0")
    lora_hash_label.pack(side=tk.LEFT, padx=5)

    lora_hash_display = tk.Label(lora_frame, textvariable=lora_hash, bg="#f0f0f0")
    lora_hash_display.pack(side=tk.LEFT, padx=5)

    remove_button = tk.Button(lora_frame, text="Remove", command=lambda: remove_lora(lora_frame), bg="#ffdddd", fg="#333", activebackground="#f5b5b5")
    remove_button.pack(side=tk.RIGHT, padx=5)

    loras.append((lora_path, lora_hash))
    update_metadata_preview()

def remove_lora(lora_frame):
    lora_name = lora_frame.winfo_children()[1].cget("text")
    matching_lora = None
    for entry in loras:
        if entry[0].get() == lora_name:
            matching_lora = entry
            break

    if matching_lora:
        loras.remove(matching_lora)

    lora_frame.destroy()
    update_metadata_preview()

def select_image(file_path=None):
    if not file_path:
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")]
        )
    if file_path:
        selected_image_path.set(file_path)
        load_image_preview(file_path, image_preview_label)
        file_name_label.config(text=f"Selected File: {file_path}")
        existing_metadata = load_existing_metadata(file_path)
        existing_metadata_box.config(state=tk.NORMAL)
        existing_metadata_box.delete('1.0', tk.END)
        existing_metadata_box.insert(tk.END, existing_metadata)
        existing_metadata_box.config(state=tk.DISABLED)
        metadata_preview_box.delete('1.0', tk.END)  # Clear metadata preview when a new image is loaded
        update_metadata_preview()

def select_model_file():
    file_path = filedialog.askopenfilename(
        title="Select Model File",
        filetypes=[("Model Files", "*.ckpt *.safetensors")]
    )
    if file_path:
        loading_label.config(text="Loading model, please wait...")
        progress_bar.pack(pady=5, fill=tk.X)
        root.update_idletasks()
        threading.Thread(target=process_model, args=(file_path,)).start()

def process_model(file_path):
    root.after(100, progress_bar.start)
    model_hash, model_name = select_model(file_path)
    root.after(0, progress_bar.stop)
    root.after(0, progress_bar.pack_forget)
    model_path.set(file_path)
    model_hash_var.set(model_hash)
    model_name_var.set(model_name)
    loading_label.config(text="Model loaded successfully.")
    update_metadata_preview()

def save_metadata():
    image_path = selected_image_path.get()
    overwrite = overwrite_var.get()
    
    if overwrite:
        output_path = image_path
    else:
        output_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")]
        )
    
    if image_path and (overwrite or output_path):
        # Use the metadata preview box content directly
        new_metadata = metadata_preview_box.get('1.0', tk.END).strip()

        print(f"New Metadata: {new_metadata}")
        save_sd_metadata_to_png(image_path, output_path, new_metadata, overwrite)

        messagebox.showinfo("Save Successful", "The image has been saved with the new metadata.")

def load_image_preview(image_path, preview_label):
    image = Image.open(image_path)
    image.thumbnail((200, 200))
    img = ImageTk.PhotoImage(image)
    preview_label.config(image=img)
    preview_label.image = img

def update_metadata_preview():
    prompt = prompt_entry.get('1.0', tk.END).strip()
    negative_prompt = negative_prompt_entry.get('1.0', tk.END).strip()
    steps = steps_entry.get().strip()
    sampler = sampler_var.get().strip()
    seed = seed_entry.get().strip()
    guidance = guidance_entry.get().strip()
    model_hash = model_hash_var.get().strip()
    model_name = model_name_var.get().strip()

    lora_details = ", ".join([f"{lora_path.get()}: {lora_hash.get()}" for lora_path, lora_hash in loras])
    lora_details = f'"{lora_details}"'

    preview_metadata = (
        f"{prompt}\n"
        f"Negative prompt: {negative_prompt}\n"
        f"Steps: {steps}, Sampler: {sampler}, Schedule type: Karras, CFG scale: {guidance}, Seed: {seed}, "
        f"Model hash: {model_hash}, Model: {model_name}, "
        f"Lora hashes: {lora_details}"
    )

    metadata_preview_box.config(state=tk.NORMAL)
    metadata_preview_box.delete('1.0', tk.END)
    metadata_preview_box.insert(tk.END, preview_metadata)

def validate_integer_input(event, var_name):
    widget = event.widget
    new_value = widget.get()
    if not new_value.isdigit():
        widget.delete(0, tk.END)
        widget.insert(0, "0")

def drop(event):
    file_path = event.data.strip('{}')
    if os.path.isfile(file_path):
        select_image(file_path)

root = TkinterDnD.Tk()
root.title("Metadata Inserter")
root.configure(bg="#e6f2ff")

selected_image_path = tk.StringVar()
overwrite_var = tk.BooleanVar()
sampler_var = tk.StringVar(value="DPM++ 2M Karras")
model_path = tk.StringVar()
model_hash_var = tk.StringVar(value="")
model_name_var = tk.StringVar(value="")

sampler_options = [
    "Euler A", "Euler", "LMS", "Heun", "DPM2", "DPM2 A", "DPM++ 2M", "DPM++ 2M Karras",
    "DPM++ SDE", "DPM++ SDE Karras", "DPM fast", "DPM adaptive", "LMS Karras", 
    "Euler A", "DPM++ 2M Karras"
]

main_frame = tk.Frame(root, bg="#e6f2ff")
main_frame.pack(fill=tk.BOTH, expand=True)

left_frame = tk.Frame(main_frame, bg="#e6f2ff")
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

middle_frame = tk.Frame(main_frame, bg="#e6f2ff")
middle_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

right_frame = tk.Frame(main_frame, bg="#e6f2ff")
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

existing_metadata_label = tk.Label(left_frame, text="Existing Metadata:", bg="#e6f2ff", font=("Arial", 12))
existing_metadata_label.pack(pady=5, anchor="w")

existing_metadata_box = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, width=40, height=30, bg="#f8f8ff")
existing_metadata_box.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
existing_metadata_box.config(state=tk.DISABLED)

file_name_label = tk.Label(middle_frame, text="Drag and Drop or Select an Image", font=("Arial", 14), bg="#e6f2ff")
file_name_label.pack(pady=15)

select_button = tk.Button(middle_frame, text="Select Image", command=select_image, bg="#b0e5fc", fg="#333", activebackground="#99d0f1")
select_button.pack(pady=10)

image_preview_label = tk.Label(middle_frame, bg="#e6f2ff")
image_preview_label.pack(pady=5)

metadata_preview_label = tk.Label(middle_frame, text="Metadata Preview:", bg="#e6f2ff", font=("Arial", 12))
metadata_preview_label.pack(pady=5, anchor="w")
warning_label = tk.Label(middle_frame, text="Modify this data on your own may cause errors", bg="#ffe6e6", fg="#ff0000")
warning_label.pack(pady=5, anchor="w")
metadata_preview_box = scrolledtext.ScrolledText(middle_frame, wrap=tk.WORD, width=50, height=10, bg="#f8f8ff")
metadata_preview_box.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

overwrite_checkbox = tk.Checkbutton(middle_frame, text="Overwrite existing file", variable=overwrite_var, bg="#e6f2ff")
overwrite_checkbox.pack(pady=5)

save_button = tk.Button(middle_frame, text="Save Image with Metadata", command=save_metadata, bg="#b0e5fc", fg="#333", activebackground="#99d0f1")
save_button.pack(pady=10)

prompt_label = tk.Label(right_frame, text="Prompt:", bg="#e6f2ff", font=("Arial", 12))
prompt_label.pack(pady=5, anchor="w")
prompt_entry = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, width=50, height=3, bg="#f8f8ff")
prompt_entry.pack(padx=10, pady=5, fill=tk.X)
prompt_entry.bind("<KeyRelease>", lambda event: update_metadata_preview())

negative_prompt_label = tk.Label(right_frame, text="Negative Prompt:", bg="#e6f2ff", font=("Arial", 12))
negative_prompt_label.pack(pady=5, anchor="w")
negative_prompt_entry = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, width=50, height=3, bg="#f8f8ff")
negative_prompt_entry.pack(padx=10, pady=5, fill=tk.X)
negative_prompt_entry.bind("<KeyRelease>", lambda event: update_metadata_preview())

steps_label = tk.Label(right_frame, text="Steps:", bg="#e6f2ff", font=("Arial", 12))
steps_label.pack(pady=5, anchor="w")
steps_entry = tk.Entry(right_frame, width=50, bg="#f8f8ff")
steps_entry.insert(0, "20")
steps_entry.pack(padx=10, pady=5, fill=tk.X)
steps_entry.bind("<KeyRelease>", lambda event: update_metadata_preview())
steps_entry.bind("<KeyRelease>", lambda event: validate_integer_input(event, "Steps"))

sampler_label = tk.Label(right_frame, text="Sampler:", bg="#e6f2ff", font=("Arial", 12))
sampler_label.pack(pady=5, anchor="w")
sampler_dropdown = tk.OptionMenu(right_frame, sampler_var, *sampler_options)
sampler_dropdown.config(bg="#b0e5fc", fg="#333", activebackground="#99d0f1")
sampler_dropdown.pack(padx=10, pady=5, fill=tk.X)
sampler_var.trace_add("write", lambda *args: update_metadata_preview())

seed_label = tk.Label(right_frame, text="Seed:", bg="#e6f2ff", font=("Arial", 12))
seed_label.pack(pady=5, anchor="w")
seed_entry = tk.Entry(right_frame, width=50, bg="#f8f8ff")
seed_entry.pack(padx=10, pady=5, fill=tk.X)
seed_entry.bind("<KeyRelease>", lambda event: update_metadata_preview())
seed_entry.bind("<KeyRelease>", lambda event: validate_integer_input(event, "Seed"))

guidance_label = tk.Label(right_frame, text="Guidance:", bg="#e6f2ff", font=("Arial", 12))
guidance_label.pack(pady=5, anchor="w")
guidance_entry = tk.Entry(right_frame, width=50, bg="#f8f8ff")
guidance_entry.insert(0, "2")
guidance_entry.pack(padx=10, pady=5, fill=tk.X)
guidance_entry.bind("<KeyRelease>", lambda event: update_metadata_preview())

model_label = tk.Label(right_frame, text="Model:", bg="#e6f2ff", font=("Arial", 12))
model_label.pack(pady=5, anchor="w")
model_button = tk.Button(right_frame, text="Select Model", command=select_model_file, bg="#b0e5fc", fg="#333", activebackground="#99d0f1")
model_button.pack(pady=5, fill=tk.X)

model_display = tk.Label(right_frame, textvariable=model_path, bg="#e6f2ff")
model_display.pack(pady=5, anchor="w")

model_hash_label = tk.Label(right_frame, text="Model Hash:", bg="#e6f2ff", font=("Arial", 12))
model_hash_label.pack(pady=5, anchor="w")
model_hash_display = tk.Label(right_frame, textvariable=model_hash_var, bg="#e6f2ff")
model_hash_display.pack(pady=5, anchor="w")

model_name_label = tk.Label(right_frame, text="Model Name:", bg="#e6f2ff", font=("Arial", 12))
model_name_label.pack(pady=5, anchor="w")
model_name_display = tk.Label(right_frame, textvariable=model_name_var, bg="#e6f2ff")
model_name_display.pack(pady=5, anchor="w")

loras_frame = tk.Frame(right_frame, bg="#e6f2ff")
loras_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

add_lora_button = tk.Button(right_frame, text="Add LORA", command=add_lora, bg="#b0e5fc", fg="#333", activebackground="#99d0f1")
add_lora_button.pack(pady=5, fill=tk.X)

loras = []

loading_label = tk.Label(right_frame, text="", fg="red", bg="#e6f2ff")
loading_label.pack(pady=5, anchor="w")

progress_bar = ttk.Progressbar(right_frame, mode='indeterminate')
progress_bar.pack_forget()

root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', drop)

root.mainloop()
