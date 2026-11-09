"""Generation text shared by the form and PNG export."""
import json
import math
import re
from urllib.parse import urlparse, parse_qs
from model_profiles import uses_distilled_guidance


def version_id(value):
    value = str(value or "").strip()
    if not value:
        return None
    if value.isdecimal() and int(value) > 0:
        return int(value)
    parsed = urlparse(value)
    if parsed.hostname in ("civitai.com", "www.civitai.com"):
        candidate = parse_qs(parsed.query).get("modelVersionId", [""])[0]
        if candidate.isdecimal() and int(candidate) > 0:
            return int(candidate)
    raise ValueError("Enter a version ID or a link containing modelVersionId; a model ID is not a version ID.")


def resource_readiness(data, loras):
    """Describe supplied identifiers; this does not claim a live Civitai match."""
    resources = [('Main model', data.get('model', ''), data.get('model_id', ''), data.get('model_hash', ''))]
    resources.extend((f'LoRA {index}', row.get('name', ''), row.get('version_id', ''), row.get('hash', ''))
                     for index, row in enumerate(loras, 1))
    identified, missing = [], []
    for label, name, reference, hash_value in resources:
        if not any(str(value).strip() for value in (name, reference, hash_value)):
            continue
        if version_id(reference) or str(hash_value).strip():
            identified.append(label)
        else:
            missing.append(label)
    if missing:
        return 'Names only: ' + ', '.join(missing) + '. Add a Civitai version ID/link or file hash for resource identification.'
    if identified:
        return f'Resource identifiers supplied for {len(identified)} item(s). Confirm matches in the Civitai upload preview.'
    return 'Add the main model and LoRAs used. A version ID/link or file hash helps Civitai identify each resource.'


def parse_parameters(text):
    match = list(re.finditer(r"^Steps: ", text, re.MULTILINE))
    if not match:
        return {"prompt": text.strip(), "negative": "", "fields": {}}
    start = match[-1].start()
    prompts = text[:start].strip().split("\nNegative prompt:", 1)
    line = text[start:].strip()
    # Split only outside quoted strings and JSON arrays/objects.
    parts, start, depth, quoted, escaped = [], 0, 0, False, False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\" and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            if char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append(line[start:index].strip())
                start = index + 1
    parts.append(line[start:].strip())
    fields = {}
    for part in parts:
        if ": " not in part:
            continue
        key, value = part.split(": ", 1)
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            pass
        fields[key] = value
    return {"prompt": prompts[0], "negative": prompts[1].strip() if len(prompts) > 1 else "",
            "fields": fields}


def normalize_metadata(parsed):
    """Fill missing form values from Civitai without overriding explicit values."""
    fields = dict(parsed["fields"])
    details = fields.get("Civitai metadata", {})
    details = details if isinstance(details, dict) else {}

    def fallback(key, value):
        if fields.get(key) in (None, "") and value not in (None, ""):
            fields[key] = value

    for key, source in (("Steps", "steps"), ("Seed", "seed"), ("CFG scale", "cfgScale"),
                        ("Sampler", "sampler"), ("Schedule type", "scheduler")):
        fallback(key, details.get(source))
    resources = fields.get("Civitai resources")
    if not isinstance(resources, list):
        legacy_resources = details.get("resources", [])
        legacy_resources = legacy_resources if isinstance(legacy_resources, list) else []
        resources = [dict(item, type=str(item.get("type", "")).lower(),
                          weight=item.get("weight", item.get("strength", 1)))
                     for item in legacy_resources if isinstance(item, dict)]
        fields["Civitai resources"] = resources
    checkpoint = next((r for r in resources if isinstance(r, dict) and
                       str(r.get("type", "")).lower() == "checkpoint"), {})
    fallback("Model", checkpoint.get("modelName"))
    fallback("Model version ID", checkpoint.get("modelVersionId"))
    fallback("Model variant", checkpoint.get("modelVersionName"))
    fallback("Model family", details.get("ecosystem"))
    hashes = checkpoint.get("hashes", {})
    hashes = hashes if isinstance(hashes, dict) else {}
    fallback("Model hash", checkpoint.get("hash") or hashes.get("AutoV2") or hashes.get("SHA256"))
    return {"prompt": parsed["prompt"] or details.get("prompt", ""),
            "negative": parsed["negative"] or details.get("negativePrompt", ""),
            "fields": fields}


def build_parameters(data, size, loras=(), extra=None):
    fields = dict(extra or {})
    controlled = ("Steps", "Sampler", "Schedule type", "CFG scale", "Distilled CFG Scale",
                  "Seed", "Size", "Model", "Model hash", "Lora hashes", "Civitai resources",
                  "Model family", "Model variant", "Model version ID", "Lora names")
    for key in controlled:
        fields.pop(key, None)
    if not data.get("prompt", "").strip():
        raise ValueError("Enter a prompt before saving.")
    if not str(data.get("steps", "")).strip():
        raise ValueError("Enter the number of steps used to generate the image.")
    for name, integer in (("steps", True), ("seed", True), ("cfg", False), ("flux_guidance", False)):
        value = str(data.get(name, "")).strip()
        if not value or (name == "flux_guidance" and not uses_distilled_guidance(data["family"])):
            continue
        try:
            number = int(value) if integer else float(value)
            if not math.isfinite(number) or number < 0 or (name == "steps" and number < 1):
                raise ValueError()
        except ValueError:
            raise ValueError(f"Invalid value for {name}.") from None
    ordered = {}
    for key, name in (("Steps", "steps"), ("Sampler", "sampler"), ("Schedule type", "scheduler"),
                      ("CFG scale", "cfg"), ("Seed", "seed")):
        value = str(data.get(name, "")).strip()
        if value:
            ordered[key] = value
    if uses_distilled_guidance(data["family"]) and str(data.get("flux_guidance", "")).strip():
        ordered["Distilled CFG Scale"] = str(data["flux_guidance"]).strip()
    ordered["Size"] = f"{size[0]}x{size[1]}"
    ordered["Model family"] = data["family"]
    if data.get("variant", "").strip():
        ordered["Model variant"] = data["variant"].strip()
    for key, name in (("Model", "model"), ("Model hash", "model_hash")):
        if data.get(name, "").strip():
            ordered[key] = data[name].strip()
    old_resources = (extra or {}).get("Civitai resources", [])
    old_resources = old_resources if isinstance(old_resources, list) else []
    resources = [r for r in old_resources if isinstance(r, dict) and r.get("type") not in ("checkpoint", "lora")]
    model_id = version_id(data.get("model_id"))
    if model_id:
        resources.append({"type": "checkpoint", "modelVersionId": model_id})
        if data.get('model', '').strip():
            resources[-1]['modelName'] = data['model'].strip()
    hashes, lora_tags = [], []
    for lora in loras:
        name = lora.get("name", "").strip()
        resource_id = version_id(lora.get("version_id"))
        if not name and not resource_id:
            continue
        try:
            weight = float(lora.get("weight") or 1)
            if not math.isfinite(weight):
                raise ValueError()
        except ValueError:
            raise ValueError("LoRA weight must be a finite number.") from None
        if resource_id:
            resources.append({"type": "lora", "modelVersionId": resource_id, "weight": weight})
            if name:
                resources[-1]['modelName'] = name
        if name:
            if any(char in name for char in "<>:\n\r"):
                raise ValueError("LoRA names cannot contain < > : or line breaks.")
            lora_tags.append((name, f"<lora:{name}:{weight:g}>"))
        if name and lora.get("hash"):
            hashes.append(f"{name}: {lora['hash']}")
    if hashes:
        ordered["Lora hashes"] = ", ".join(hashes)
    ordered.update(fields)
    if resources:
        for resource in resources:
            old = next((r for r in old_resources if isinstance(r, dict) and r.get("type") == resource["type"] and r.get("modelVersionId") == resource.get("modelVersionId")), {})
            for key, value in old.items():
                resource.setdefault(key, value)
        ordered["Civitai resources"] = resources
    def encode(key, value):
        if isinstance(value, (dict, list)) or key == "Lora hashes" or "," in str(value) or "\n" in str(value):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return str(value)
    prompt = data["prompt"].strip()
    try:
        structured = isinstance(json.loads(prompt), (dict, list))
    except ValueError:
        structured = False
    if structured and lora_tags:
        ordered["Lora names"] = [{"name": name, "weight": float(tag.rsplit(":", 1)[1][:-1])} for name, tag in lora_tags]
    for name, tag in lora_tags:
        if not structured and f"<lora:{name}:" not in prompt:
            prompt += " " + tag
    negative = data.get("negative", "").strip()
    if negative:
        prompt += "\nNegative prompt: " + negative
    return prompt + "\n" + ", ".join(f"{key}: {encode(key, value)}" for key, value in ordered.items())
