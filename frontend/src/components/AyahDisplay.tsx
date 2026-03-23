import type { AyahText, WordStatus } from '../types';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';

interface AyahDisplayProps {
  ayah: AyahText;
  confirmedWords?: WordStatus[];
  tentativeWords?: WordStatus[];
  showReference?: boolean;
  isPrompt?: boolean;
}

// Arabic surah names (1-114)
const SURAH_NAMES: Record<number, string> = {
  1: 'Al-Fatihah',
  2: 'Al-Baqarah',
  3: 'Ali Imran',
  4: 'An-Nisa',
  5: 'Al-Ma\'idah',
  6: 'Al-An\'am',
  7: 'Al-A\'raf',
  8: 'Al-Anfal',
  9: 'At-Tawbah',
  10: 'Yunus',
  11: 'Hud',
  12: 'Yusuf',
  13: 'Ar-Ra\'d',
  14: 'Ibrahim',
  15: 'Al-Hijr',
  16: 'An-Nahl',
  17: 'Al-Isra',
  18: 'Al-Kahf',
  19: 'Maryam',
  20: 'Ta-Ha',
  21: 'Al-Anbiya',
  22: 'Al-Hajj',
  23: 'Al-Mu\'minun',
  24: 'An-Nur',
  25: 'Al-Furqan',
  26: 'Ash-Shu\'ara',
  27: 'An-Naml',
  28: 'Al-Qasas',
  29: 'Al-Ankabut',
  30: 'Ar-Rum',
  31: 'Luqman',
  32: 'As-Sajdah',
  33: 'Al-Ahzab',
  34: 'Saba',
  35: 'Fatir',
  36: 'Ya-Sin',
  37: 'As-Saffat',
  38: 'Sad',
  39: 'Az-Zumar',
  40: 'Ghafir',
  41: 'Fussilat',
  42: 'Ash-Shura',
  43: 'Az-Zukhruf',
  44: 'Ad-Dukhan',
  45: 'Al-Jathiyah',
  46: 'Al-Ahqaf',
  47: 'Muhammad',
  48: 'Al-Fath',
  49: 'Al-Hujurat',
  50: 'Qaf',
  51: 'Adh-Dhariyat',
  52: 'At-Tur',
  53: 'An-Najm',
  54: 'Al-Qamar',
  55: 'Ar-Rahman',
  56: 'Al-Waqi\'ah',
  57: 'Al-Hadid',
  58: 'Al-Mujadilah',
  59: 'Al-Hashr',
  60: 'Al-Mumtahanah',
  61: 'As-Saff',
  62: 'Al-Jumu\'ah',
  63: 'Al-Munafiqun',
  64: 'At-Taghabun',
  65: 'At-Talaq',
  66: 'At-Tahrim',
  67: 'Al-Mulk',
  68: 'Al-Qalam',
  69: 'Al-Haqqah',
  70: 'Al-Ma\'arij',
  71: 'Nuh',
  72: 'Al-Jinn',
  73: 'Al-Muzzammil',
  74: 'Al-Muddaththir',
  75: 'Al-Qiyamah',
  76: 'Al-Insan',
  77: 'Al-Mursalat',
  78: 'An-Naba',
  79: 'An-Nazi\'at',
  80: 'Abasa',
  81: 'At-Takwir',
  82: 'Al-Infitar',
  83: 'Al-Mutaffifin',
  84: 'Al-Inshiqaq',
  85: 'Al-Buruj',
  86: 'At-Tariq',
  87: 'Al-A\'la',
  88: 'Al-Ghashiyah',
  89: 'Al-Fajr',
  90: 'Al-Balad',
  91: 'Ash-Shams',
  92: 'Al-Layl',
  93: 'Ad-Duhaa',
  94: 'Ash-Sharh',
  95: 'At-Tin',
  96: 'Al-Alaq',
  97: 'Al-Qadr',
  98: 'Al-Bayyinah',
  99: 'Az-Zalzalah',
  100: 'Al-Adiyat',
  101: 'Al-Qari\'ah',
  102: 'At-Takathur',
  103: 'Al-Asr',
  104: 'Al-Humazah',
  105: 'Al-Fil',
  106: 'Quraysh',
  107: 'Al-Ma\'un',
  108: 'Al-Kawthar',
  109: 'Al-Kafirun',
  110: 'An-Nasr',
  111: 'Al-Masad',
  112: 'Al-Ikhlas',
  113: 'Al-Falaq',
  114: 'An-Nas',
};

/**
 * AyahDisplay component shows the current ayah being recited
 * with word-level highlighting as the user speaks
 */
export function AyahDisplay({
  ayah,
  confirmedWords = [],
  tentativeWords = [],
  showReference = true,
  isPrompt = false,
}: AyahDisplayProps) {
  // Create a map of word indices to their status
  const wordStatusMap = new Map<number, 'correct' | 'incorrect' | 'tentative'>();

  confirmedWords.forEach((w) => {
    wordStatusMap.set(w.index, w.status);
  });

  tentativeWords.forEach((w) => {
    if (!wordStatusMap.has(w.index)) {
      wordStatusMap.set(w.index, 'tentative');
    }
  });

  // Split the ayah text into words for highlighting
  const words = ayah.text_uthmani.split(' ');

  const getWordClassName = (index: number): string => {
    const status = wordStatusMap.get(index);
    const baseClass = 'inline-block mx-1 transition-colors duration-200';

    if (!status) {
      return baseClass;
    }

    switch (status) {
      case 'correct':
        return `${baseClass} word-confirmed`;
      case 'incorrect':
        return `${baseClass} word-mistake`;
      case 'tentative':
        return `${baseClass} word-tentative`;
      default:
        return baseClass;
    }
  };

  const surahName = SURAH_NAMES[ayah.surah] || `Surah ${ayah.surah}`;

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        {/* Ayah Reference Header */}
        {showReference && (
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <div className="flex items-center gap-2">
              {isPrompt && (
                <Badge variant="secondary">Prompt</Badge>
              )}
              <span className="text-sm text-muted-foreground">
                {surahName} ({ayah.surah}:{ayah.ayah})
              </span>
            </div>
            <Badge variant="outline">Juz {ayah.juz}</Badge>
          </div>
        )}

        {/* Ayah Text - Preserved Arabic styling */}
        <div className="quran-text p-6 bg-white" dir="rtl">
          {words.map((word, index) => (
            <span key={index} className={getWordClassName(index)}>
              {word}
            </span>
          ))}
        </div>

        {/* Legend for highlighting (only show during recitation) */}
        {!isPrompt && (confirmedWords.length > 0 || tentativeWords.length > 0) && (
          <div className="flex items-center justify-center gap-6 px-6 py-3 bg-gray-50 border-t border-gray-100">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-green-600 rounded-full"></span>
              <span className="text-xs text-gray-600">Correct</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-gray-400 rounded-full"></span>
              <span className="text-xs text-gray-600">Processing</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-red-500 rounded-full"></span>
              <span className="text-xs text-gray-600">Mistake</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default AyahDisplay;
