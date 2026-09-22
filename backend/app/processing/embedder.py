import open_clip
import torch
from PIL import Image

_model, _preprocess, _tokenizer = None, None, None


def _load():
    global _model, _preprocess, _tokenizer
    if _model is None:
        _model, _, _preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="openai")
        _tokenizer = open_clip.get_tokenizer("ViT-B-32")
        _model.eval()
    return _model, _preprocess, _tokenizer


def embed_image(image_path: str) -> list[float]:
    model, preprocess, _ = _load()
    image = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        features = model.encode_image(image)
        features /= features.norm(dim=-1, keepdim=True)
    return features[0].tolist()


def embed_text(text: str) -> list[float]:
    model, _, tokenizer = _load()
    tokens = tokenizer([text])
    with torch.no_grad():
        features = model.encode_text(tokens)
        features /= features.norm(dim=-1, keepdim=True)
    return features[0].tolist()