#!/usr/bin/env python3
"""
Process raw Quran data from alquran.cloud API into the required format.

Creates quran.json with 3 text forms:
- text_uthmani: Original with diacritics (for display)
- text_normalized: Diacritics removed, alef normalized (for comparison)
- text_tokens: Tokenized normalized text (for alignment)
"""

import json
import re
from pathlib import Path


# Diacritics (tashkeel) to remove - Unicode range \u064B-\u065F and \u0670
DIACRITICS_PATTERN = re.compile(r'[\u064B-\u065F\u0670]')

# Alef variants to normalize: أ إ آ ٱ → ا
ALEF_VARIANTS_PATTERN = re.compile(r'[أإآٱ]')

# BOM character that appears at start of some texts
BOM = '\ufeff'


def normalize_arabic(text: str) -> str:
    """
    Normalize Arabic text for comparison.

    - Remove diacritics (tashkeel)
    - Normalize alef variants to bare alef
    - Do NOT normalize ta marbuta (ة) to ha (ه) - keep distinct
    """
    # Remove BOM if present
    text = text.replace(BOM, '')

    # Remove diacritics
    text = DIACRITICS_PATTERN.sub('', text)

    # Normalize alef variants
    text = ALEF_VARIANTS_PATTERN.sub('ا', text)

    return text


def tokenize(text: str) -> list[str]:
    """Split normalized text into tokens (words)."""
    return [word for word in text.split() if word]


def generate_audio_url(surah: int, ayah: int) -> str:
    """Generate audio URL for Ghamadi recitation from everyayah.com."""
    return f"https://everyayah.com/data/Ghamadi_40kbps/{surah:03d}{ayah:03d}.mp3"


def process_quran_data(raw_data: dict) -> list[dict]:
    """Process raw API data into list of ayah objects with 3 text forms."""
    processed = []

    for surah in raw_data['data']['surahs']:
        surah_num = surah['number']

        for ayah in surah['ayahs']:
            text_uthmani = ayah['text'].replace(BOM, '')
            text_normalized = normalize_arabic(ayah['text'])
            text_tokens = tokenize(text_normalized)

            processed.append({
                'surah': surah_num,
                'ayah': ayah['numberInSurah'],
                'juz': ayah['juz'],
                'text_uthmani': text_uthmani,
                'text_normalized': text_normalized,
                'text_tokens': text_tokens,
                'audio_url': generate_audio_url(surah_num, ayah['numberInSurah'])
            })

    return processed


def main():
    """Main processing function."""
    script_dir = Path(__file__).parent
    raw_path = script_dir / 'quran_raw.json'
    output_path = script_dir / 'quran.json'

    print(f"Loading raw data from {raw_path}...")
    with open(raw_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    print("Processing data...")
    processed = process_quran_data(raw_data)

    print(f"Writing {len(processed)} ayahs to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

    # Print sample
    print("\nSample output (first ayah):")
    print(json.dumps(processed[0], ensure_ascii=False, indent=2))

    print(f"\nTotal ayahs processed: {len(processed)}")
    print("Done!")


if __name__ == '__main__':
    main()
