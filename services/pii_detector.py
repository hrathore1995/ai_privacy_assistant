import os, re
import spacy
from dotenv import load_dotenv
from openai import OpenAI
from utils.regex_patterns import patterns
from config import settings

load_dotenv()
MODEL = os.getenv("SPACY_MODEL", "en_core_web_md")
nlp = spacy.load(MODEL)

# pass key explicitly
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class PIIDetector:
    def __init__(self, text: str, model: str = None):
        self.text = text
        self.model = model or settings.OPENAI_MODEL

    def _dedup(self, seq):
        seen, out = set(), []
        for x in seq:
            if x not in seen:
                seen.add(x); out.append(x)
        return out

    def via_regex(self):
        found = {}
        for key, pat in patterns.items():
            hits = re.findall(pat, self.text)
            if hits:
                found[key] = self._dedup(hits)
        return found

    def via_spacy(self):
        doc = nlp(self.text)
        ents = {}
        for ent in doc.ents:
            ents.setdefault(ent.label_, []).append(ent.text)
        for k, v in ents.items():
            ents[k] = self._dedup(v)
        return ents

    def via_llm(self):
        if not settings.USE_LLM or not settings.OPENAI_API_KEY:
            return "llm disabled"
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "you detect contextual pii"},
                {"role": "user", "content": (
                    "Identify sensitive info in this text. "
                    "Return a short list like: Name(s): ...; Location(s): ...; Emails: ...\n\n"
                    f"{self.text}"
                )},
            ],
            temperature=0,
        )
        return resp.choices[0].message.content

    def detect_all(self):
        return {
            "regex": self.via_regex(),
            "spacy": self.via_spacy(),
            "llm": self.via_llm(),
        }
