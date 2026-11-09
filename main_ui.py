import os
import json
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES, TkinterDnD
from metadata import build_parameters, resource_readiness
from model_profiles import PROFILES, OTHER, detect_profile, uses_distilled_guidance
from utils import get_model_hash_and_name, read_image_generation, save_sd_metadata_to_png


class MetadataEditor:
    def __init__(self, root):
        self.root, self.path, self.size = root, None, (0, 0)
        self.extra, self.loras, self.vars = {}, [], {}
        self.loading = False
        self.jobs = queue.Queue()
        self.hash_tasks = {}
        self.latest_hash_task = {}
        root.title('Metadata Editor · Civitai')
        root.geometry('1100x850')
        root.minsize(850, 700)
        bar = ttk.Frame(root, padding=10)
        bar.pack(fill='x')
        ttk.Button(bar, text='Open image…', command=self.open_image).pack(side='left')
        self.filename = ttk.Label(bar, text='You can also drag an image here')
        self.filename.pack(side='left', padx=10)
        ttk.Button(bar, text='Save PNG copy…', command=self.save).pack(side='right')
        self.import_notice = ttk.Label(root, text='', padding=(10, 0), wraplength=1000)
        self.import_notice.pack(fill='x')
        panes = ttk.Panedwindow(root, orient='horizontal')
        panes.pack(fill='both', expand=True, padx=10)
        left, right = ttk.Frame(panes), ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=2)
        self.photo_label = ttk.Label(left, anchor='center')
        self.photo_label.pack(fill='x')
        ttk.Label(left, text='Original metadata').pack(anchor='w', pady=8)
        self.original = scrolledtext.ScrolledText(left, width=35, height=20, wrap='word', state='disabled')
        self.original.pack(fill='both', expand=True)
        tabs = ttk.Notebook(right)
        tabs.pack(fill='both', expand=True)
        basic_page, advanced_page = ttk.Frame(tabs), ttk.Frame(tabs)
        tabs.add(basic_page, text='Basic')
        tabs.add(advanced_page, text='Advanced')
        basic = self.scrollable(basic_page)
        advanced = self.scrollable(advanced_page)
        self.basic_tab = basic
        self.advanced_tab = advanced
        ttk.Label(basic, text='Advanced includes sampler, scheduler, model hash, and LoRA settings.',
                  wraplength=500).pack(anchor='w', pady=(0, 4))
        ttk.Button(basic, text='Open Advanced settings',
                   command=lambda: tabs.select(advanced_page)).pack(anchor='w', pady=(0, 8))
        self.family_widget = self.field(basic, 'Model family', 'family', OTHER, tuple(PROFILES))
        self.variant_widget = self.field(basic, 'Variant / model version (optional; editable)', 'variant', '', ('',))
        self.vars['family'].trace_add('write', self.family_changed)
        self.field(basic, 'Main model name (optional)', 'model')
        self.field(basic, 'Main model: Civitai version ID or link (optional)', 'model_id')
        ttk.Button(basic, text='Select main model file… (optional)', command=self.select_model).pack(anchor='w', pady=5)
        ttk.Label(basic, text='Prompt').pack(anchor='w')
        self.prompt = scrolledtext.ScrolledText(basic, height=4, wrap='word')
        self.prompt.pack(fill='x', pady=4)
        ttk.Label(basic, text='Negative prompt (optional)').pack(anchor='w')
        self.negative = scrolledtext.ScrolledText(basic, height=2, wrap='word')
        self.negative.pack(fill='x', pady=4)
        for label, key, value in [('Steps', 'steps', '20'), ('Seed (optional)', 'seed', ''), ('CFG scale', 'cfg', '7')]:
            self.field(basic, label, key, value)
        self.flux_frame = ttk.Frame(basic)
        self.field(self.flux_frame, 'Flux guidance (Distilled CFG Scale)', 'flux_guidance')
        self.hint = ttk.Label(basic, text='Enter the settings used to generate the image.', wraplength=500)
        self.hint.pack(anchor='w', pady=6)
        ttk.Label(advanced, text='Optional settings for reproducing your image and identifying resources in Civitai.',
                  wraplength=500).pack(anchor='w', pady=(0, 10))
        sampling = ttk.LabelFrame(advanced, text='Sampling settings', padding=8)
        sampling.pack(fill='x', pady=5)
        ttk.Label(sampling, text='Copy the sampler and scheduler from your generation workflow.',
                  wraplength=480).pack(anchor='w', pady=(0, 6))
        self.field(sampling, 'Sampler', 'sampler', 'Euler', ('Euler', 'Euler a', 'DPM++ 2M', 'DPM++ SDE'))
        self.field(sampling, 'Scheduler (optional)', 'scheduler', '', ('', 'Simple', 'Normal', 'Karras', 'Beta'))
        identity = ttk.LabelFrame(advanced, text='Main model identification', padding=8)
        identity.pack(fill='x', pady=5)
        ttk.Label(identity, text='Calculated from the file selected in Basic, or entered manually. Helps identify the exact model file.',
                  wraplength=480).pack(anchor='w', pady=(0, 6))
        self.field(identity, 'Main model hash (optional)', 'model_hash')
        lora_section = ttk.LabelFrame(advanced, text='LoRA resources', padding=8)
        lora_section.pack(fill='x', pady=5)
        ttk.Label(lora_section, text='Add the LoRAs used in your image. Weight is their strength; the version ID or link identifies the Civitai resource.',
                  wraplength=480).pack(anchor='w', pady=(0, 6))
        ttk.Label(lora_section, text='Name | Weight | Civitai version ID or link').pack(anchor='w')
        self.lora_frame = ttk.Frame(lora_section)
        self.lora_frame.pack(fill='x')
        ttk.Button(lora_section, text='Add LoRA', command=self.add_lora).pack(anchor='w', pady=5)
        ttk.Label(advanced, text='Names document resources. A version ID or hash helps Civitai identify them.', wraplength=500).pack(anchor='w', pady=8)
        self.resource_notice = ttk.Label(right, text='', wraplength=650, padding=(0, 6))
        self.resource_notice.pack(fill='x')
        ttk.Label(right, text='Preview · text to be saved').pack(anchor='w', pady=8)
        self.preview = scrolledtext.ScrolledText(right, height=7, wrap='word', state='disabled')
        self.preview.pack(fill='both', expand=True)
        self.hash_progress_frame = ttk.Frame(root, padding=(10, 0))
        self.hash_progress_frame.pack(fill='x')
        self.status = ttk.Label(root, text='Save a PNG copy while keeping your original image.', padding=8)
        self.status.pack(fill='x')
        for widget in (self.prompt, self.negative):
            widget.bind('<<Modified>>', self.text_changed)
        for var in self.vars.values():
            var.trace_add('write', self.refresh)
        root.drop_target_register(DND_FILES)
        root.dnd_bind('<<Drop>>', self.drop)
        root.bind('<Map>', self.attach_form_scrolling, add='+')
        root.after(100, self.poll_jobs)

    @staticmethod
    def scrollable(parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        advanced = ttk.Frame(canvas, padding=10)
        advanced.scroll_canvas = canvas
        canvas.scroll_canvas = canvas
        tag = f'FormScroll:{canvas}'
        canvas.form_scroll_tag = tag

        def scroll(event):
            if getattr(event, 'num', None) in (4, 5):
                units = -3 if event.num == 4 else 3
            else:
                delta = event.delta
                if not delta:
                    return
                units = -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
            canvas.yview_scroll(units, 'units')
            return 'break'

        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            canvas.bind_class(tag, sequence, scroll)
        advanced_window = canvas.create_window((0, 0), window=advanced, anchor='nw')
        advanced.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(advanced_window, width=event.width))
        return advanced

    @staticmethod
    def attach_form_scrolling(event):
        widget = event.widget
        # Keep text editors and scrollbars using their own native wheel behavior.
        if widget.winfo_class() in ('Text', 'Scrollbar', 'TScrollbar'):
            return
        ancestor = widget
        while ancestor is not None:
            canvas = getattr(ancestor, 'scroll_canvas', None)
            if canvas is not None:
                tag = canvas.form_scroll_tag
                if tag not in widget.bindtags():
                    # Before class bindings so scrolling a combobox cannot change its value.
                    widget.bindtags((tag, *widget.bindtags()))
                return
            ancestor = getattr(ancestor, 'master', None)

    def field(self, parent, label, name, value='', choices=None):
        ttk.Label(parent, text=label).pack(anchor='w')
        var = self.vars[name] = tk.StringVar(value=value)
        widget = ttk.Entry(parent, textvariable=var) if choices is None else ttk.Combobox(parent, textvariable=var, values=choices)
        if name == 'family':
            widget.configure(state='readonly')
        widget.pack(fill='x', pady=(2, 6))
        return widget

    def family_changed(self, *_):
        family = self.vars['family'].get()
        self.family_widget.configure(values=tuple(PROFILES) + ((family,) if family not in PROFILES else ()))
        self.variant_widget.configure(values=PROFILES.get(family, ('',)))
        if not self.loading:
            self.vars['variant'].set('')
        if uses_distilled_guidance(family):
            self.flux_frame.pack(fill='x', before=self.hint)
            hint = 'FLUX.1: CFG and distilled guidance are separate. Enter your actual workflow values; guidance may not apply to Schnell.'
        else:
            self.flux_frame.pack_forget()
            hint = {
                'MOSS-Image': 'MOSS-Image supports text and JSON layout prompts. Structured prompts are preserved as JSON.',
                'Qwen-Image': 'Use the CFG and step values from your Qwen workflow. Edit workflows may also require source images.',
                'Z-Image': 'Base and Turbo use different generation settings. Enter the values from your workflow.',
                'FLUX.2': 'FLUX.2 has its own variants. FLUX.1 distilled guidance is not added automatically.',
                OTHER: 'Unknown family: keep your original values and select a family only when known.',
            }.get(family, 'Enter the settings used to generate the image. No generation values are changed automatically.')
        self.hint.configure(text=hint)
        self.refresh()

    def text_changed(self, event):
        if event.widget.edit_modified():
            event.widget.edit_modified(False)
            self.refresh()

    def data(self):
        return {**{k: v.get() for k, v in self.vars.items()}, 'prompt': self.prompt.get('1.0', 'end-1c'), 'negative': self.negative.get('1.0', 'end-1c')}

    def lora_data(self):
        return [{k: v.get() for k, v in row.items()} for _, row in self.loras]

    @staticmethod
    def set_text(widget, text):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.configure(state='disabled')

    def refresh(self, *_):
        if self.loading:
            return
        try:
            text = build_parameters(self.data(), self.size, self.lora_data(), self.extra) if self.path else 'Open an image to get started.'
            self.resource_notice.configure(text=resource_readiness(self.data(), self.lora_data()))
        except ValueError as error:
            text = str(error)
            self.resource_notice.configure(text=str(error))
        self.set_text(self.preview, text)

    def add_lora(self, values=None):
        values = values or {}
        frame, row = ttk.LabelFrame(self.lora_frame, text='LoRA', padding=6), {}
        frame.pack(fill='x', pady=3)
        for column, (key, label, default, width) in enumerate([
                ('name', 'Name / filename', '', 18), ('weight', 'Weight', '1', 6),
                ('version_id', 'Civitai version ID / link', '', 20)]):
            row[key] = tk.StringVar(value=values.get(key, default))
            ttk.Label(frame, text=label).grid(row=0, column=column, sticky='w', padx=2)
            ttk.Entry(frame, textvariable=row[key], width=width).grid(row=1, column=column, sticky='ew', padx=2)
            frame.columnconfigure(column, weight=0 if key == 'weight' else 1)
        row['hash'] = tk.StringVar(value=values.get('hash', ''))
        ttk.Label(frame, text='File hash (optional; editable)').grid(row=2, column=0, columnspan=3, sticky='w', pady=(6, 0))
        ttk.Entry(frame, textvariable=row['hash']).grid(row=3, column=0, columnspan=3, sticky='ew', padx=2)
        actions = ttk.Frame(frame)
        actions.grid(row=4, column=0, columnspan=3, sticky='w', pady=(6, 0))
        ttk.Button(actions, text='Calculate hash from file…', command=lambda: self.select_model(row)).pack(side='left')
        ttk.Button(actions, text='Remove LoRA', command=lambda: self.remove_lora(frame)).pack(side='left', padx=6)
        self.loras.append((frame, row))
        for var in row.values():
            var.trace_add('write', self.refresh)
        self.refresh()

    def remove_lora(self, frame):
        self.loras = [(w, row) for w, row in self.loras if w is not frame]
        frame.destroy()
        self.refresh()

    def open_image(self, path=None):
        path = path or filedialog.askopenfilename(filetypes=[('Images', '*.png *.jpg *.jpeg')])
        if not path:
            return
        try:
            with Image.open(path) as image:
                image.load()
                size = image.size
                image.thumbnail((250, 180))
                photo = ImageTk.PhotoImage(image)
            parsed = read_image_generation(path)
            original = parsed['original']
        except Exception as error:
            messagebox.showerror('Could not open image', str(error))
            return
        self.loading = True
        try:
            self.path, self.size = path, size
            self.import_notice.configure(text=f"Import: {parsed['source']}. " + ' '.join(parsed['warnings']))
            self.photo_label.configure(image=photo)
            self.photo_label.image = photo
            self.filename.configure(text=f'{os.path.basename(path)} · {size[0]} × {size[1]}')
            self.set_text(self.original, original)
            self.extra = fields = parsed['fields']
            for widget, text in [(self.prompt, parsed['prompt']), (self.negative, parsed['negative'])]:
                widget.delete('1.0', 'end')
                widget.insert('1.0', text)
            for frame, _ in list(self.loras):
                self.remove_lora(frame)
            family, variant = detect_profile(fields)
            self.vars['family'].set(family)
            self.vars['variant'].set(variant)
            for key, name in [('Steps', 'steps'), ('Seed', 'seed'), ('CFG scale', 'cfg'), ('Distilled CFG Scale', 'flux_guidance'), ('Sampler', 'sampler'), ('Schedule type', 'scheduler'), ('Model', 'model'), ('Model hash', 'model_hash')]:
                self.vars[name].set(str(fields.get(key, '')))
            self.vars['model_id'].set(str(fields.get('Model version ID', '')))
            hashes = {}
            for item in str(fields.get('Lora hashes', '')).split(','):
                if ':' in item:
                    name, hash_value = item.rsplit(':', 1)
                    hashes[name.strip()] = hash_value.strip()
            resources = fields.get('Civitai resources', [])
            if isinstance(resources, list):
                for resource in resources:
                    if not isinstance(resource, dict):
                        continue
                    if str(resource.get('type', '')).lower() == 'checkpoint':
                        self.vars['model_id'].set(str(resource.get('modelVersionId', '')))
                    elif str(resource.get('type', '')).lower() == 'lora':
                        name = resource.get('modelName', '')
                        self.add_lora({'name': name, 'weight': str(resource.get('weight', 1)), 'version_id': str(resource.get('modelVersionId', '')), 'hash': hashes.pop(name, '')})
            for name, hash_value in hashes.items():
                self.add_lora({'name': name, 'hash': hash_value})
            for entry in fields.get('Lora names', []) if isinstance(fields.get('Lora names'), list) else []:
                if isinstance(entry, dict) and not any(row['name'].get() == entry.get('name') for _, row in self.loras):
                    self.add_lora({'name': entry.get('name', ''), 'weight': str(entry.get('weight', 1))})
            # Structured layout prompts must not be rewritten as plain text.
            try:
                structured = isinstance(json.loads(parsed['prompt']), (dict, list))
            except ValueError:
                structured = False
            tags = [] if structured else re.findall(r'<lora:([^:>]+):([^>]+)>', parsed['prompt'])
            for name, weight in tags:
                row = next((row for _, row in self.loras if row['name'].get() == name), None)
                if row is None:
                    self.add_lora({'name': name, 'weight': weight})
                else:
                    row['weight'].set(weight)
            clean_prompt = parsed['prompt'] if structured else re.sub(r'<lora:[^:>]+:[^>]+>', '', parsed['prompt']).strip()
            self.prompt.delete('1.0', 'end')
            self.prompt.insert('1.0', clean_prompt)
        finally:
            self.loading = False
        self.refresh()

    def select_model(self, row=None):
        path = filedialog.askopenfilename(filetypes=[('Models', '*.safetensors *.ckpt')])
        if path:
            token = object()
            target = id(row) if row is not None else None
            self.latest_hash_task[target] = token
            frame = ttk.Frame(self.hash_progress_frame)
            frame.pack(fill='x', pady=3)
            kind = 'Main model' if row is None else 'LoRA'
            label = ttk.Label(frame, text=f'{kind}: calculating hash for {os.path.basename(path)}…')
            label.pack(anchor='w')
            progress = ttk.Progressbar(frame, mode='indeterminate')
            progress.pack(fill='x', pady=(2, 0))
            progress.start(15)
            self.hash_tasks[token] = (frame, progress)
            self.status.configure(text='Calculating hash… You can keep using the editor.')
            def work():
                try:
                    result = get_model_hash_and_name(path)
                except Exception:
                    result = ('Error', 'Unknown')
                self.jobs.put((token, target, row, *result))
            threading.Thread(target=work, daemon=True).start()

    def poll_jobs(self):
        try:
            while True:
                token, target, row, hash_value, name = self.jobs.get_nowait()
                frame, progress = self.hash_tasks.pop(token)
                progress.stop()
                frame.destroy()
                if self.latest_hash_task.get(target) is not token:
                    continue
                del self.latest_hash_task[target]
                if hash_value == 'Error':
                    self.status.configure(text='Could not read the model file.')
                elif row is None:
                    self.vars['model'].set(name)
                    self.vars['model_hash'].set(hash_value)
                    self.status.configure(text='Model name and hash loaded.')
                elif any(existing is row for _, existing in self.loras):
                    row['name'].set(name)
                    row['hash'].set(hash_value)
                    self.status.configure(text='LoRA name and hash loaded.')
                else:
                    self.status.configure(text='Hash calculation finished; the LoRA was removed.')
        except queue.Empty:
            pass
        self.root.after(100, self.poll_jobs)

    def drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        if paths:
            self.open_image(paths[0])

    def save(self):
        if not self.path:
            messagebox.showinfo('Select an image', 'Open an image before saving.')
            return
        try:
            metadata = build_parameters(self.data(), self.size, self.lora_data(), self.extra)
        except ValueError as error:
            messagebox.showerror('Check the fields', str(error))
            return
        path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG', '*.png')], initialfile=os.path.splitext(os.path.basename(self.path))[0] + '_metadata.png')
        if not path:
            return
        try:
            if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(self.path)):
                raise ValueError('Choose a different name to preserve the original image.')
            if not path.lower().endswith('.png'):
                raise ValueError('The copy must have a .png extension.')
            save_sd_metadata_to_png(self.path, path, metadata, False)
        except Exception as error:
            messagebox.showerror('Could not save image', str(error))
            return
        self.status.configure(text=f'Copy saved: {path}')
        messagebox.showinfo('Copy saved', 'PNG saved with metadata. Check the resources in the Civitai upload preview.')


def main():
    root = TkinterDnD.Tk()
    MetadataEditor(root)
    root.mainloop()


if __name__ == '__main__':
    main()
