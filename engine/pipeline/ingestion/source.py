from dataclasses import dataclass

@dataclass
class Source:
    root_path: str     # local path (git clone handled outside)
