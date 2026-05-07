"""
Fix script for the three NLP config files.
Issues addressed:
  1. Preserve/stopword CONFLICTS  → remove from stopwords if in preserve
  2. Slang dict DESTROYS entities → remove slang keys that are political entities
  3. Bad preserve entries         → remove generic adjectives that Sastrawi handles fine
  4. Overly-aggressive stopwords  → keep temporal/directional words (hari, bulan, malam, kiri, kanan…)
  5. Add missing but important entities to preserve
  6. Add more missing slang normalizations
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))

def load(fname):
    with open(os.path.join(BASE, fname)) as f:
        return json.load(f)

def save(fname, data, sort_keys=False):
    with open(os.path.join(BASE, fname), 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ─────────────────────────────────────────────
# 1. SLANG DICT: remove keys that are entities
# ─────────────────────────────────────────────
slang = load('slang_dict.json')

# These keys ARE entities; the slang mapping is wrong/misleading
entity_keys_to_delete = {
    'gibran',   # gibran → iran  (WRONG — Gibran is the VP)
    'isis',     # isis   → isi   (WRONG — ISIS is the militant group)
    'kpk',      # kpk    → kelompok (WRONG — KPK is the anti-graft body)
    'ma',       # ma     → sama  (WRONG — MA is Mahkamah Agung)
    'mk',       # mk     → maka  (WRONG — MK is Mahkamah Konstitusi)
    'pan',      # pan    → kapan (WRONG — PAN is a political party)
    'pks',      # pks    → pakistan (WRONG — PKS is a political party)
    'psi',      # psi    → opsi  (WRONG — PSI is a political party)
    'ras',      # ras    → rasa  (WRONG — ras means race/ethnicity)
    'sk',       # sk     → suka  (WRONG — SK is Surat Keputusan)
    'usa',      # usa    → usah  (WRONG — USA is United States)
    'bini',     # bini   → istri (debatable; bini is valid colloquial for wife,
                #                  but the real problem is it's in preserve too)
}

# Additional obviously-wrong mappings found in slang dict
bad_mappings_to_delete = {
    'aah',      # aah → arah   (aah is just an exclamation)
    'abah',     # abah → tambah (abah = father in Sundanese, not tambah)
    'aula',     # aula → daulat (aula = hall, not daulat)
    'aus',      # aus → us      (aus means worn-out/thirsty, not US)
    'amis',     # amis → kamis  (amis means fishy smell, not Thursday)
    'asap',     # asap → segera (asap means smoke, not immediately)
    'ati',      # ati → mati   (ati means liver/heart in Javanese, not mati)
    'avi',      # avi → aviv   (avi is a file format / name, not aviv)
    'aum',      # aum → kaum   (aum is the sound of a lion)
    'ampas',    # ampas → hamas (ampas means dregs/waste, NOT Hamas)
    'akta',     # akta → fakta  (akta means deed/certificate, not fakta)
    'alu',      # alu → aku    (alu is a pestle)
    'abah',     # already above
}

for key in entity_keys_to_delete | bad_mappings_to_delete:
    slang.pop(key, None)

# Fix: bini should map to istri (it IS a slang/colloquial for wife)
# but we also remove it from preserve (it's not an entity)
slang['bini'] = 'istri'

# Add genuinely missing slang mappings
new_slang = {
    # Internet / Gen-Z Indonesian slang
    'gaje':     'ga jelas',
    'alay':     'norak',
    'lebay':    'berlebihan',
    'jayus':    'tidak lucu',
    'gercep':   'gerak cepat',
    'kepo':     'ingin tahu',
    'baper':    'bawa perasaan',
    'julid':    'iri hati',
    'bully':    'intimidasi',
    'healing':  'pemulihan',
    'healing':  'refreshing',
    'ghosting': 'menghilang tiba-tiba',
    'flexing':  'pamer',
    'toxic':    'beracun',
    'receh':    'murahan',
    'gokil':    'gila',
    'woles':    'santai',
    'bokap':    'ayah',
    'nyokap':   'ibu',
    'cewe':     'cewek',
    'cowo':     'cowok',
    'gebetan':  'orang yang disukai',
    'pdkt':     'pendekatan',
    'jomblo':   'lajang',
    'lebay':    'berlebihan',
    'rempong':  'ribet',
    'curcol':   'curhat colongan',
    'curhat':   'mencurahkan hati',
    'bolos':    'membolos',
    'plong':    'lega',
    'ngasal':   'sembarangan',
    'ngaret':   'terlambat',
    'ngegas':   'marah-marah',
    'ngebully': 'mengintimidasi',
    'ngehalu':  'berimajinasi berlebihan',
    'ngeri':    'menakutkan',
    'kocak':    'lucu',
    'gelo':     'gila',
    'ga':       'tidak',
    'gaada':    'tidak ada',
    'gamau':    'tidak mau',
    'gabisa':   'tidak bisa',
    'gapaham':  'tidak paham',
    'gatau':    'tidak tahu',
    'gapapa':   'tidak apa-apa',
    'gaperlu':  'tidak perlu',
    'gapenting':'tidak penting',
    'gasuka':   'tidak suka',
    'gasalah':  'tidak salah',
    'gaseru':   'tidak seru',
    'gatep':    'tidak tepat',
    'cape':     'capek',
    'capek':    'lelah',
    'pengen':   'ingin',
    'pengin':   'ingin',
    'mampir':   'singgah',
    'kesel':    'kesal',
    'bete':     'bosan',
    'sebel':    'sebal',
    'gondok':   'kesal',
    'sewot':    'marah',
    'emosi':    'marah',
    'sebel':    'sebal',
    'sebel':    'sebal',
    'kzl':      'kesal',
    'smgt':     'semangat',
    'smangat':  'semangat',
    'smngt':    'semangat',
    'gaul':     'pergaulan',
    'hits':     'populer',
    'viral':    'viral',
    'trending': 'tren',
    'booming':  'meledak',
    # Geopolitical abbreviations / acronyms that are commonly typed
    'ri':       'republik indonesia',
    'nkri':     'negara kesatuan republik indonesia',
    'tni':      'tentara nasional indonesia',
    'polri':    'kepolisian republik indonesia',
    'dpr':      'dewan perwakilan rakyat',
    'dprd':     'dewan perwakilan rakyat daerah',
    'mpr':      'majelis permusyawaratan rakyat',
    'bpk':      'badan pemeriksa keuangan',
    'kpu':      'komisi pemilihan umum',
    'bawaslu':  'badan pengawas pemilihan umum',
    'mahkamah': 'mahkamah',
    # Common news abbreviations
    'wni':      'warga negara indonesia',
    'wna':      'warga negara asing',
    'ham':      'hak asasi manusia',
    'umr':      'upah minimum regional',
    'umk':      'upah minimum kota',
    'apbn':     'anggaran pendapatan belanja negara',
    'apbd':     'anggaran pendapatan belanja daerah',
    'rapbn':    'rancangan anggaran pendapatan belanja negara',
    'bumn':     'badan usaha milik negara',
    'bumd':     'badan usaha milik daerah',
    'ojk':      'otoritas jasa keuangan',
    'bi':       'bank indonesia',
    'bps':      'badan pusat statistik',
    'bpjs':     'badan penyelenggara jaminan sosial',
    'ktp':      'kartu tanda penduduk',
    'sim':      'surat izin mengemudi',
    'stnk':     'surat tanda nomor kendaraan',
    'sertif':   'sertifikat',
    'pns':      'pegawai negeri sipil',
    'asn':      'aparatur sipil negara',
    'ormas':    'organisasi masyarakat',
    'lsm':      'lembaga swadaya masyarakat',
    'ngo':      'lembaga swadaya masyarakat',
    'pers':     'media pers',
    'warteg':   'warung tegal',
    # Commonly mistyped/abbreviated political/event terms
    'pilkades': 'pemilihan kepala desa',
    'pemda':    'pemerintah daerah',
    'pemkot':   'pemerintah kota',
    'pemkab':   'pemerintah kabupaten',
    'pemprov':  'pemerintah provinsi',
    'kemenko':  'kementerian koordinator',
    'kemlu':    'kementerian luar negeri',
    'kemhan':   'kementerian pertahanan',
    'kemendagri':'kementerian dalam negeri',
    'kemenkes': 'kementerian kesehatan',
    'kemdikbud':'kementerian pendidikan kebudayaan',
    'kodam':    'komando daerah militer',
    'korem':    'komando resort militer',
    'kodim':    'komando distrik militer',
    'koramil':  'komando rayon militer',
    'babinsa':  'bintara pembina desa',
    'bhabinkamtibmas': 'bhayangkara pembina keamanan ketertiban masyarakat',
}

slang.update(new_slang)
slang = dict(sorted(slang.items()))
save('slang_dict.json', slang)
print(f"[OK] slang_dict.json: {len(slang)} entries")


# ─────────────────────────────────────────────
# 2. PRESERVE: remove generic words, fix real issues
# ─────────────────────────────────────────────
preserve = load('preserve.json')
preserve_set = set(preserve)

# Remove generic adjectives / function words — Sastrawi/stopword handles these
remove_from_preserve = {
    'baik',      # generic adjective
    'buruk',     # generic adjective
    'benar',     # generic adjective
    'salah',     # generic adjective
    'tidak',     # negation word — should be in stopwords or handled by Sastrawi
    'beda',      # generic adjective
    'pro',       # prefix / generic
    'bini',      # colloquial wife — already handled by slang dict (→ istri)
    'rt',        # RT = retweet → already in stopwords; conflicting
    'tengah',    # directional — too generic to preserve
    'buzzer',    # already in stopwords — conflict
    'online',    # too generic
    # Overly administrative / not useful as topic signals
    'perbup', 'pergub', 'perwali', 'perda', 'permen',  # regional regulations
    'edaran', 'instruksi', 'himbauan', 'seruan', 'maklumat', 'pesan',
    'nota', 'mou', 'kontrak',
    # Education terms not needed as topic signals
    'alumni', 'murid', 'siswa', 'pelajar', 'magister', 'doktor', 'profesor',
    'akademisi', 'sarjana', 'pelatihan', 'kursus', 'lokakarya', 'workshop',
    'simposium', 'seminar', 'konferensi', 'kolom', 'editorial', 'redaktur',
    'majalah', 'tabloid', 'blogger', 'podcaster', 'vlogger',
    # Too generic as signal
    'desa', 'kecamatan', 'kelurahan', 'kabupaten',
    'studi', 'jurusan', 'fakultas', 'akademi', 'politeknik', 'kampus', 'sekolah',
    'program', 'kursus',
    'pandangan', 'posisi', 'sikap', 'pendapat',
    'berimbang', 'objektif', 'subjektif', 'imparsial', 'netral',
    'jujur', 'adil', 'sepakat', 'setuju', 'tolak', 'dukung',
    'keputusan', 'aturan', 'peraturan',
    'arahan', 'fatwa', 'resolusi', 'deklarasi', 'perjanjian', 'kesepakatan',
    'kesepahaman', 'kerjasama', 'kemitraan', 'aliansi',
    'publik', 'masyarakat', 'rakyat', 'penduduk', 'pemilih', 'warga',
    'informasi', 'berita', 'opini', 'artikel',
    'merah', 'putih', 'garuda', 'ika', 'tunggal',
    'ikn',  # too short / ambiguous after stemming
    'rw',   # too short
    'sk',   # too short / already removed from slang
    'ma',   # too short — Mahkamah Agung but also overloaded
    'cpo',  # commodity abbreviation, niche
    'bbm',  # too generic now (could mean fuel or BBM messaging)
    'ntb', 'ntt',  # island provinces, too niche
    'uu', 'uud',   # abbreviations → handled fine by slang dict
    'boko',        # only meaningful together with "Haram"
    'qaeda',       # only meaningful together with "Al"
    'al',          # too short
    'mou',
    'perwali',
    'perppu', 'perpres',
}

preserve_set -= remove_from_preserve

# Add missing critical entities
add_to_preserve = {
    # Key Indonesian institutions
    'kpk', 'kpu', 'bawaslu', 'mk', 'ma', 'mahkamah',
    'dprd', 'bpk', 'ojk', 'bumn', 'bpjs',
    # Named political figures still active (2024-2025 era)
    'jokowi', 'prabowo', 'gibran', 'anies', 'ganjar', 'ahok', 'sby', 'megawati',
    'luhut', 'mahfud', 'habib', 'rizieq',
    # Active conflict / geopolitical entities
    'ceasefire', 'gencatan', 'senjata', 'serangan', 'invasi', 'pendudukan',
    'genosida', 'embargo', 'deportasi', 'pengungsi', 'pengungsi',
    # Indonesian legal / crime terms
    'koruptor', 'suap', 'gratifikasi', 'pencucian', 'uang', 'pemalsuan',
    'penggelapan', 'penipuan', 'pencurian', 'perampokan', 'penculikan',
    'pembunuhan', 'terorisme', 'radikalisme', 'ekstremisme',
    # Economy
    'inflasi', 'deflasi', 'resesi', 'stagflasi', 'devaluasi', 'revaluasi',
    'ekspor', 'impor', 'neraca', 'perdagangan', 'investasi',
    'saham', 'obligasi', 'kripto', 'bitcoin', 'ethereum',
    'subsidi', 'pajak', 'tarif', 'bea', 'cukai',
    # Health / pandemic-era (still relevant)
    'pandemi', 'vaksin', 'mpox', 'varian', 'klaster',
    # Environment
    'banjir', 'gempa', 'tsunami', 'gunung', 'api', 'erupsi', 'kekeringan',
    'kebakaran', 'hutan', 'deforestasi', 'polusi', 'limbah',
    # Social issues
    'kekerasan', 'pelecehan', 'perkosaan', 'femisida', 'kdrt',
    'stunting', 'kemiskinan', 'pengangguran',
    # Media / information
    'hoaks', 'disinformasi', 'misinformasi', 'propaganda', 'sensor',
    'kebebasan', 'pers', 'jurnalis', 'wartawan',
    # Countries still missing
    'ukraina', 'rusia', 'iran', 'israel', 'china', 'Amerika',
    'houthi', 'lebanon', 'suriah', 'yaman', 'sudan', 'ethiopia',
    'kongo', 'myanmar', 'taiwan', 'korea',
}

preserve_set |= add_to_preserve
preserve_list = sorted(preserve_set)
save('preserve.json', preserve_list)
print(f"[OK] preserve.json: {len(preserve_list)} entries")


# ─────────────────────────────────────────────
# 3. STOPWORDS: fix conflicts & over-aggressive entries
# ─────────────────────────────────────────────
stopwords = load('stopwords.json')
stopwords_set = set(stopwords)

# Remove from stopwords anything that is now in preserve (prevent conflicts)
preserve_set_final = set(preserve_list)
conflicts_removed = stopwords_set & preserve_set_final
stopwords_set -= conflicts_removed
if conflicts_removed:
    print(f"  Removed {len(conflicts_removed)} stopword/preserve conflicts: {sorted(conflicts_removed)}")

# Remove overly-aggressive stopwords that carry topic signal
restore_from_stop = {
    # Temporal words — "malam ini", "hari ini", "bulan ini" carry meaning
    # Keep stripped so Sastrawi handles them naturally
    # (we remove them from stopwords so they are NOT aggressively deleted)
    'hari', 'malam', 'pagi', 'siang', 'sore', 'besok', 'kemarin', 'lusa',
    'minggu', 'bulan', 'tahun',
    # Directional words — "kiri" and "kanan" carry political meaning in Indonesian context
    'kiri', 'kanan',
    # These may be part of entity names in context
    'tengah',    # also removed from preserve conflicts
    # "dalam" and "luar" can be meaningful: "dalam negeri" vs "luar negeri"
    'dalam', 'luar',
}
stopwords_set -= restore_from_stop

# Add genuinely missing noise words
add_to_stop = {
    # Repeated/elongated forms that slipped through
    'ygy', 'ygy', 'ygy', 'asw', 'asw',
    # Pure noise internet tokens
    'hahaha', 'hahahaha', 'wkwkwk', 'wkwkwkwk', 'kwkwkw', 'kkkkk', 'kkkk',
    'ahahaha', 'lololol', 'lmao', 'lmfao', 'rofl', 'xd', 'xdd',
    'hehe', 'hihi', 'huhu', 'hwehwe', 'huy',
    # English filler words common in Indonesian tweets
    'like', 'so', 'just', 'yeah', 'nope', 'yep', 'nah', 'hmm', 'hm',
    'omg', 'wtf', 'lol', 'btw', 'afk', 'irl', 'tbh', 'imo', 'smh',
    # Indonesian filler
    'toh', 'nih', 'sih', 'deh', 'dong', 'lah', 'kah', 'yah', 'wah',
    'kan', 'lho', 'loh', 'kok', 'koq', 'ko', 'mah', 'teh', 'atuh', 'euy',
    # Single letters (noise after tokenization)
    'a', 'b', 'c', 'd', 'e', 'f', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z',
    # Common noise abbreviations
    'klo', 'kl', 'jd', 'jg', 'sm', 'tp', 'sdh', 'dg', 'pd', 'ny',
    'dr', 'utk', 'trs', 'tdk', 'ttg', 'tgl', 'krn',
    # Emoji descriptions that sometimes appear as text
    'hati', 'bintang', 'api', 'tangan',
}
stopwords_set |= add_to_stop

stopwords_list = sorted(stopwords_set)
save('stopwords.json', stopwords_list)
print(f"[OK] stopwords.json: {len(stopwords_list)} entries")

print("\n✅ All fixes applied successfully.")
print(f"   slang_dict : {len(slang)} entries")
print(f"   preserve   : {len(preserve_list)} entries")
print(f"   stopwords  : {len(stopwords_list)} entries")
