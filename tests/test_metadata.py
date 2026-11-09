import unittest

from metadata import build_parameters, parse_parameters, version_id, normalize_metadata, resource_readiness
from model_profiles import PROFILES, detect_profile, OTHER
import json


class MetadataTests(unittest.TestCase):
    def test_resource_names_and_hashes_survive_editable_export(self):
        data = self.data()
        data.update(model='Main model', model_hash='abcdef1234')
        loras = [dict(name='Style', weight='0.4', version_id='67890', hash='1234abcdef')]
        fields = normalize_metadata(parse_parameters(build_parameters(data, (64, 64), loras)))['fields']
        self.assertEqual(fields['Model'], 'Main model')
        self.assertEqual(fields['Civitai resources'][1]['modelName'], 'Style')
        self.assertEqual(fields['Lora hashes'], 'Style: 1234abcdef')
        self.assertEqual(fields['Civitai resources'][1]['weight'], 0.4)
        self.assertIn('Names only', resource_readiness({'model': 'Unknown'}, []))
        self.assertIn('Resource identifiers supplied', resource_readiness(data, loras))

    def test_civitai_values_populate_missing_form_fields(self):
        parsed = {"prompt": "original", "negative": "", "fields": {
            "Civitai resources": [{"type": "checkpoint", "modelName": "Krea 2 Turbo",
                                   "modelVersionName": "v1.0", "modelVersionId": 3072332}],
            "Civitai metadata": {"ecosystem": "Krea2", "steps": 8, "cfgScale": 0,
                                 "seed": 0, "negativePrompt": "blur"}}}
        result = normalize_metadata(parsed)
        fields = result['fields']
        self.assertEqual(fields['Model'], 'Krea 2 Turbo')
        self.assertEqual(fields['Model version ID'], 3072332)
        self.assertEqual(detect_profile(fields), ('Krea2', 'v1.0'))
        self.assertEqual(fields['Steps'], 8)
        self.assertEqual(fields['CFG scale'], 0)
        self.assertEqual(fields['Seed'], 0)
        self.assertEqual(result['negative'], 'blur')
        self.assertNotIn('Model', parsed['fields'])
        parsed['fields'].update({'Model': 'explicit', 'Steps': 24, 'Seed': 123})
        fields = normalize_metadata(parsed)['fields']
        self.assertEqual(fields['Model'], 'explicit')
        self.assertEqual(fields['Steps'], 24)
        self.assertEqual(fields['Seed'], 123)

    def test_all_profiles_roundtrip_without_changing_settings(self):
        for family, variants in PROFILES.items():
            for variant in variants:
                with self.subTest(family=family, variant=variant):
                    data = self.data()
                    data.update(family=family, variant=variant)
                    fields = parse_parameters(build_parameters(data, (64, 64)))['fields']
                    self.assertEqual(detect_profile(fields), (family, variant))
                    self.assertEqual(fields['Steps'], 24)
                    self.assertEqual(fields['CFG scale'], 1)
                    self.assertEqual('Distilled CFG Scale' in fields, family == 'FLUX.1')

    def test_detection_is_conservative(self):
        self.assertEqual(detect_profile({'Model': 'unknown-checkpoint'})[0], OTHER)
        self.assertEqual(detect_profile({'Model': 'flux2-klein'}) , ('FLUX.2', 'Klein'))
        self.assertEqual(detect_profile({'Model': 'MOSS-Image-SFT'}) , ('MOSS-Image', 'SFT'))

    def test_moss_layout_prompt_stays_valid_json(self):
        data = self.data()
        prompt = '{"objects": [{"text": "Hello, world", "x": 10}]} '
        data.update(family='MOSS-Image', variant='SFT', prompt=prompt)
        text = build_parameters(data, (64, 64), [{'name': 'style', 'weight': '0.7'}])
        parsed = parse_parameters(text)
        self.assertEqual(json.loads(parsed['prompt']), json.loads(prompt))
        self.assertEqual(parsed['fields']['Lora names'], [{'name': 'style', 'weight': 0.7}])

    def data(self, **changes):
        return dict(prompt="Café portrait", negative="", family="FLUX", steps="24", seed="123",
                    cfg="1", flux_guidance="3.5", sampler="Euler", scheduler="Simple",
                    model="flux1-dev", model_hash="", model_id="12345", **changes)

    def test_flux_roundtrip_and_resource_ids(self):
        data = self.data()
        loras = [{"name": "style.v2", "weight": "0.8", "version_id": "67890", "hash": "abcdef1234"}]
        text = build_parameters(data, (832, 1248), loras)
        parsed = parse_parameters(text)
        self.assertIn("<lora:style.v2:0.8>", parsed["prompt"])
        self.assertEqual(parsed["fields"]["Distilled CFG Scale"], 3.5)
        self.assertEqual(parsed["fields"]["CFG scale"], 1)
        self.assertEqual(parsed["fields"]["Size"], "832x1248")
        self.assertEqual(parsed["fields"]["Civitai resources"][1]["modelVersionId"], 67890)
        self.assertNotIn("Karras", text)
        self.assertNotIn("Negative prompt:", text)

    def test_sd_omits_flux_guidance_and_empty_fields(self):
        data = self.data()
        data.update(family="Stable Diffusion", model_id="", seed="", model="", negative="blur")
        text = build_parameters(data, (64, 64))
        self.assertNotIn("Distilled CFG Scale", text)
        self.assertNotIn("Model:", text)
        self.assertNotIn("Seed:", text)
        self.assertIn("Negative prompt: blur", text)

    def test_quoted_values_json_and_unknown_fields_survive(self):
        data = self.data()
        data["model"] = 'name, special: "v2"'
        text = build_parameters(data, (64, 64), [dict(name="style", hash="aaa", weight="1"),
                                                dict(name="other", hash="bbb", weight="1")],
                                {"Clip skip": 2, "Civitai metadata": {"prompt": "text, Seed: 10"}})
        fields = parse_parameters(text)["fields"]
        self.assertEqual(fields["Model"], data["model"])
        self.assertEqual(fields["Lora hashes"], "style: aaa, other: bbb")
        self.assertEqual(fields["Civitai metadata"]["prompt"], "text, Seed: 10")
        self.assertEqual(fields["Clip skip"], 2)

    def test_validation(self):
        self.assertEqual(version_id("https://civitai.com/models/99?modelVersionId=123"), 123)
        with self.assertRaises(ValueError):
            version_id("https://civitai.com/models/99")
        for key, value in [("steps", ""), ("steps", "0"), ("seed", "abc"), ("cfg", "nan"), ("flux_guidance", "inf")]:
            data = self.data()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                build_parameters(data, (64, 64))


if __name__ == "__main__":
    unittest.main()
