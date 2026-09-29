import re
import unicodedata
from urllib.parse import urlparse

ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
ARABIC_TRANSLATION = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
        "ـ": "",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)

LEGAL_FORM_PATTERNS = {
    "SARL": (
        r"\bs\s*\.?\s*a\s*\.?\s*r\s*\.?\s*l\b",
        r"\bsociete\s+a\s+responsabilite\s+limitee\b",
    ),
    "EURL": (
        r"\be\s*\.?\s*u\s*\.?\s*r\s*\.?\s*l\b",
        r"\bentreprise\s+unipersonnelle\s+a\s+responsabilite\s+limitee\b",
    ),
    "SPA": (r"\bs\s*\.?\s*p\s*\.?\s*a\b", r"\bsociete\s+par\s+actions\b"),
    "SNC": (r"\bs\s*\.?\s*n\s*\.?\s*c\b", r"\bsociete\s+en\s+nom\s+collectif\b"),
    "SCS": (r"\bs\s*\.?\s*c\s*\.?\s*s\b", r"\bsociete\s+en\s+commandite\s+simple\b"),
}

WILAYAS = [
    "Adrar", "Chlef", "Laghouat", "Oum El Bouaghi", "Batna", "Bejaia", "Biskra",
    "Bechar", "Blida", "Bouira", "Tamanrasset", "Tebessa", "Tlemcen", "Tiaret",
    "Tizi Ouzou", "Alger", "Djelfa", "Jijel", "Setif", "Saida", "Skikda",
    "Sidi Bel Abbes", "Annaba", "Guelma", "Constantine", "Medea", "Mostaganem",
    "Msila", "Mascara", "Ouargla", "Oran", "El Bayadh", "Illizi", "Bordj Bou Arreridj",
    "Boumerdes", "El Tarf", "Tindouf", "Tissemsilt", "El Oued", "Khenchela",
    "Souk Ahras", "Tipaza", "Mila", "Ain Defla", "Naama", "Ain Temouchent",
    "Ghardaia", "Relizane", "Timimoun", "Bordj Badji Mokhtar", "Ouled Djellal",
    "Beni Abbes", "In Salah", "In Guezzam", "Touggourt", "Djanet", "El Meghaier",
    "El Meniaa",
]

WILAYAS_AR = [
    "أدرار", "الشلف", "الأغواط", "أم البواقي", "باتنة", "بجاية", "بسكرة",
    "بشار", "البليدة", "البويرة", "تمنراست", "تبسة", "تلمسان", "تيارت",
    "تيزي وزو", "الجزائر", "الجلفة", "جيجل", "سطيف", "سعيدة", "سكيكدة",
    "سيدي بلعباس", "عنابة", "قالمة", "قسنطينة", "المدية", "مستغانم",
    "المسيلة", "معسكر", "ورقلة", "وهران", "البيض", "إليزي", "برج بوعريريج",
    "بومرداس", "الطارف", "تندوف", "تيسمسيلت", "الوادي", "خنشلة", "سوق أهراس",
    "تيبازة", "ميلة", "عين الدفلى", "النعامة", "عين تموشنت", "غرداية",
    "غليزان", "تيميمون", "برج باجي مختار", "أولاد جلال", "بني عباس",
    "عين صالح", "عين قزام", "تقرت", "جانت", "المغير", "المنيعة",
]

ARABIC_LATIN = {
    "ا": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "dj", "ح": "h",
    "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s",
    "ش": "ch", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a",
    "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m",
    "ن": "n", "ه": "h", "و": "ou", "ي": "i", "ة": "a", "ء": "",
}


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_arabic(value: str | None) -> str | None:
    if not value:
        return None
    value = ARABIC_DIACRITICS.sub("", value.translate(ARABIC_TRANSLATION))
    value = re.sub(r"[^\w\u0600-\u06FF]+", " ", value, flags=re.UNICODE)
    return _collapse(value).lower()


def normalize_latin(value: str | None) -> str | None:
    if not value:
        return None
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9\u0600-\u06FF]+", " ", value)
    return _collapse(value)


def normalize_identifier(value: str | None) -> str | None:
    if not value:
        return None
    value = value.translate(ARABIC_TRANSLATION).upper()
    return re.sub(r"[^A-Z0-9]", "", value)


def normalize_legal_form(value: str | None) -> str | None:
    text = normalize_latin(value)
    if not text:
        return None
    for legal_form, patterns in LEGAL_FORM_PATTERNS.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            return legal_form
    compact = re.sub(r"[^A-Z]", "", value.upper())
    return next((form for form in LEGAL_FORM_PATTERNS if form in compact), None)


def transliterate_arabic(value: str | None) -> str | None:
    text = normalize_arabic(value)
    if not text:
        return None
    return _collapse("".join(ARABIC_LATIN.get(char, char) for char in text))


def normalize_company_name(value: str | None, *, strip_legal_form: bool = True) -> str | None:
    text = normalize_arabic(value) if value and re.search(r"[\u0600-\u06FF]", value) else normalize_latin(value)
    if not text:
        return None
    if strip_legal_form:
        for patterns in LEGAL_FORM_PATTERNS.values():
            for pattern in patterns:
                text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
        text = _collapse(text)
    return text


def normalize_wilaya(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_latin(value)
    if normalized and normalized.isdigit():
        code = int(normalized)
        if 1 <= code <= len(WILAYAS):
            return WILAYAS[code - 1]
    aliases = {normalize_latin(name): name for name in WILAYAS}
    arabic_aliases = {normalize_arabic(name): canonical for name, canonical in zip(WILAYAS_AR, WILAYAS, strict=True)}
    aliases.update(
        {
            "algiers": "Alger",
            "oran wilaya": "Oran",
            "sidi bel abbes": "Sidi Bel Abbes",
            "bejaia": "Bejaia",
            "bedjaia": "Bejaia",
        }
    )
    if re.search(r"[\u0600-\u06FF]", value):
        return arabic_aliases.get(normalize_arabic(value), value.strip())
    return aliases.get(normalized, value.strip())


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value.translate(ARABIC_TRANSLATION))
    if digits.startswith("00213"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 10:
        digits = "213" + digits[1:]
    return f"+{digits}" if digits.startswith("213") else digits


def normalize_domain(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value if "://" in value else f"https://{value}"
    host = (urlparse(candidate).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host or None


def normalize_address(value: str | None) -> str | None:
    return normalize_latin(value)
