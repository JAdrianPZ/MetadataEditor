"""Create synthetic metadata exports for the optional official parser checks."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image
from metadata import build_parameters
from utils import save_sd_metadata_to_png


def build(directory):
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'source.png'
    Image.new('RGB', (32, 24), 'red').save(source)
    for mode in ('ids', 'hashes', 'both'):
        data = dict(prompt='A café beside a lake', negative='blur', family='SDXL', steps='28',
                    seed='123456789', cfg='6.5', sampler='Euler', scheduler='Normal', model='test.model',
                    model_id='12345' if mode != 'hashes' else '',
                    model_hash='abcdef1234' if mode != 'ids' else '')
        loras = [dict(name='test.style', weight='0.7', version_id='67890' if mode != 'hashes' else '',
                      hash='1234abcdef' if mode != 'ids' else '')]
        save_sd_metadata_to_png(source, directory / f'{mode}.png', build_parameters(data, (32, 24), loras), False)
    print(f'Created local parser fixtures in {directory}')


if __name__ == '__main__':
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '.venv/civitai-fixtures')
