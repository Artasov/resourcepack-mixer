# mixing_map.py
import os
import pickle
from pathlib import Path
from typing import Dict, List, Tuple


def build_texture_map(mix_dir: Path) -> Dict[str, List[Tuple[str, Path]]]:
    texture_map: Dict[str, List[Tuple[str, Path]]] = {}
    if not mix_dir.is_dir():
        return texture_map
    for pack_dir in sorted(mix_dir.iterdir()):
        if not pack_dir.is_dir():
            continue
        pack_name = pack_dir.name
        for root, _, files in os.walk(pack_dir):
            root_path = Path(root)
            if "assets" not in root_path.parts or "textures" not in root_path.parts:
                continue
            for fname in files:
                if not fname.lower().endswith(".png"):
                    continue
                full = root_path / fname
                rel = full.relative_to(pack_dir)
                rel_str = str(rel).replace("\\", "/")
                texture_map.setdefault(rel_str, []).append((pack_name, full))
    return texture_map


def load_texture_map(mix_dir: Path, pkl_path: Path) -> Dict[str, List[Tuple[str, Path]]]:
    if pkl_path.exists():
        with open(pkl_path, "rb") as f:
            return pickle.load(f)
    texture_map = build_texture_map(mix_dir)
    with open(pkl_path, "wb") as f:
        pickle.dump(texture_map, f)
    return texture_map
