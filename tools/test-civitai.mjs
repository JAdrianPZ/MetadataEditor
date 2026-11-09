import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { readCivitaiMetadata } from '@civitai/generation-metadata/civitai';

const directory = process.argv[2] ?? '.venv/civitai-fixtures';
for (const mode of ['ids', 'hashes', 'both']) {
  const md = await readCivitaiMetadata(new Uint8Array(await readFile(path.join(directory, `${mode}.png`))));
  const gen = md.civitai.generation;
  assert.equal(md.generator, 'automatic1111');
  assert.equal(gen.prompt, 'A café beside a lake');
  assert.equal(gen.negativePrompt, 'blur');
  assert.equal(gen.steps, 28);
  assert.equal(gen.cfgScale, 6.5);
  assert.equal(gen.seed, 123456789);
  assert.equal(gen.width, 32);
  assert.equal(gen.height, 24);
  const model = gen.resources.find(r => r.kind === 'checkpoint');
  const lora = gen.resources.find(r => r.kind === 'lora');
  assert.ok(model, `${mode}: missing model`);
  assert.ok(lora, `${mode}: missing LoRA`);
  assert.equal(lora.weight, 0.7);
  if (mode !== 'hashes') {
    assert.equal(model.modelVersionId, 12345);
    assert.equal(lora.modelVersionId, 67890);
  }
  if (mode !== 'ids') {
    assert.equal(model.hash, 'abcdef1234');
    assert.equal(lora.hash, '1234abcdef');
  }
  console.log(`PASS: ${mode} — prompt, settings, model and LoRA parsed by Civitai`);
}
