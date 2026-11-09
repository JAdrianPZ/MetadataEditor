// Reads files locally; no upload or Civitai API lookup.
import { readFile } from 'node:fs/promises';
import { readCivitaiMetadata } from '@civitai/generation-metadata/civitai';

if (!process.argv[2]) {
  console.error('Usage: node tools/validate-civitai.mjs IMAGE.png');
  process.exitCode = 1;
} else {
  const md = await readCivitaiMetadata(new Uint8Array(await readFile(process.argv[2])));
  console.log(JSON.stringify({ generator: md.generator, generation: md.civitai.generation }, null, 2));
  if (!md.generator) process.exitCode = 1;
}
