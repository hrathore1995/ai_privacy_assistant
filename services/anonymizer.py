import re
from typing import Dict, List, Tuple
from faker import Faker

# which spaCy labels to treat as PII
PII_ENTITY_LABELS = {"PERSON", "ORG", "GPE", "LOC", "NORP"}

class Anonymizer:
    def __init__(self, mode: str = "mask"):
        self.mode = mode  # "mask" | "redact" | "pseudo"
        self.faker = Faker()
        self.map: Dict[str, str] = {}   # original -> replacement
        self.counts: Dict[str, int] = {}  # category -> count

    def _tag(self, cat: str, idx: int) -> str:
        return f"<{cat}_{idx}>"

    def _redact(self, s: str) -> str:
        return "█" * max(6, min(len(s), 24))

    def _pseudo_for(self, cat: str) -> str:
        if cat == "email": return self.faker.email()
        if cat == "phone": return self.faker.phone_number()
        if cat == "ssn":   return self.faker.ssn()
        if cat == "credit_card": return self.faker.credit_card_number()
        if cat == "PERSON": return self.faker.name()
        if cat in {"ORG"}: return self.faker.company()
        if cat in {"GPE","LOC"}: return self.faker.city()
        if cat == "NORP": return "Group"
        return "REDACTED"

    def _make_replacement(self, cat: str, original: str, idx: int) -> str:
        if self.mode == "mask":
            return self._tag(cat, idx)
        if self.mode == "redact":
            return self._redact(original)
        # pseudonymize
        return self._pseudo_for(cat)

    def _collect_targets(self, detections: dict) -> List[Tuple[str, str]]:
        """
        Build (original, category) pairs from regex + spacy detections.
        """
        pairs: List[Tuple[str,str]] = []

        # regex
        for cat, vals in (detections.get("regex") or {}).items():
            for v in vals:
                pairs.append((v, cat))

        # spacy
        for label, vals in (detections.get("spacy") or {}).items():
            if label in PII_ENTITY_LABELS:
                for v in vals:
                    pairs.append((v, label))

        # dedup by (text, cat), prefer longer strings first
        pairs = list({(p[0], p[1]) for p in pairs})
        pairs.sort(key=lambda x: len(x[0]), reverse=True)
        return pairs

    def build_replacements(self, detections: dict):
        idx_tracker: Dict[str, int] = {}
        for original, cat in self._collect_targets(detections):
            key = original
            if key in self.map:
                continue
            idx_tracker[cat] = idx_tracker.get(cat, 0) + 1
            repl = self._make_replacement(cat, original, idx_tracker[cat])
            self.map[key] = repl
            self.counts[cat] = self.counts.get(cat, 0) + 1

    def apply(self, text: str) -> str:
        """apply replacements safely"""
        out = text
        for original, repl in self.map.items():
            out = re.sub(re.escape(original), repl, out)
        return out

    def anonymize_pages(self, pages_text: list[str], detections: dict):
        """returns (sanitized_pages, mapping, stats)"""
        self.build_replacements(detections)
        sanitized = [self.apply(t) for t in pages_text]
        return sanitized, self.map, self.counts
