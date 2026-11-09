"""Editor profiles describe fields, not recommended generation settings."""

PROFILES = {
    "SD 1.5": ("",),
    "SDXL": ("",),
    "Pony": ("",),
    "Illustrious": ("",),
    "NoobAI": ("",),
    "FLUX.1": ("", "Dev", "Schnell"),
    "FLUX.2": ("", "Dev", "Klein"),
    "Qwen-Image": ("", "Image", "Edit"),
    "Z-Image": ("", "Base", "Turbo"),
    "SD 3.5": ("", "Medium", "Large", "Large Turbo"),
    "MOSS-Image": ("", "Base", "SFT"),
    "Other / preserve original": ("",),
}
OTHER = "Other / preserve original"


def uses_distilled_guidance(family):
    return family in ("FLUX", "FLUX.1")


def detect_profile(fields):
    explicit = fields.get("Model family")
    if isinstance(explicit, str) and explicit.strip():
        return explicit, str(fields.get("Model variant", ""))
    resources = fields.get("Civitai resources", [])
    names = [str(fields.get("Model", ""))]
    if isinstance(resources, list):
        names.extend(str(r.get("baseModel", "")) + " " + str(r.get("modelName", ""))
                     for r in resources if isinstance(r, dict) and r.get("type") == "checkpoint")
    name = " ".join(names).lower().replace("_", "-")
    patterns = [("moss", "MOSS-Image"), ("qwen", "Qwen-Image"), ("z-image", "Z-Image"),
                ("zimage", "Z-Image"), ("noob", "NoobAI"), ("illustrious", "Illustrious"),
                ("pony", "Pony"), ("flux.2", "FLUX.2"), ("flux2", "FLUX.2"),
                ("flux-2", "FLUX.2"), ("flux", "FLUX.1"), ("sd3.5", "SD 3.5"),
                ("sd 3.5", "SD 3.5"), ("sdxl", "SDXL"), ("sd xl", "SDXL"),
                ("sd1.5", "SD 1.5"), ("sd 1.5", "SD 1.5")]
    family = next((family for pattern, family in patterns if pattern in name), OTHER)
    if family == OTHER and "Distilled CFG Scale" in fields:
        family = "FLUX.1"
    variant = str(fields.get("Model variant", "")) or next((v for v in reversed(PROFILES[family]) if v and v.lower() in name), "")
    return family, variant
