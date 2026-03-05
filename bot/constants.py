# Predefined Dhikr Categories and Subcategories

DHIKR_CATEGORIES = {
    "Quran": {
        "Surah Al-Fatiha": {},
        "Surah Al-Ikhlas": {},
        "Surah Al-Falaq": {},
        "Surah An-Nas": {},
        "Ayatul Kursi": {},
        "Other Surah/Ayah": {}
    },
    "Tasbih": {
        "Kalimah": {
            "1st Kalimah (Tayyabah)": {},
            "2nd Kalimah (Shahadat)": {},
            "3rd Kalimah (Tamjeed)": {},
            "4th Kalimah (Tauheed)": {},
            "5th Kalimah (Istigfar)": {},
            "Imane Mujmal": {},
            "Imane Muffassal": {}
        },
        "Astagfirullah": {},
        "SubhanAllah": {},
        "Alhamdulillah": {},
        "Allahu Akbar": {},
        "SubhanAllahi wa bihamdihi": {},
        "La hawla wala quwwata illa billah": {}
    },
    "Salawat": {
        "Durood-e-Ibrahim": {},
        "Short Durood (Sallallahu Alayhi Wasallam)": {},
        "Durood-e-Tunajjina": {},
        "Durood-e-Nariya": {},
        "Other Salawat": {}
    },
    "Other": {
        "Custom Dhikr": {}
    }
}

DHIKR_PRESETS = {
    "Surah Al-Fatiha": {
        "arabic": "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ (1) الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ (2) الرَّحْمَنِ الرَّحِيمِ (3) مَالِكِ يَوْمِ الدِّينِ (4) إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ (5) اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ (6) صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ (7)",
        "meaning": "In the name of Allah, the Entirely Merciful, the Especially Merciful. [All] praise is [due] to Allah, Lord of the worlds...",
        "description": "The Opening Surah of the Quran.",
        "reminder": "Have you recited Surah Al-Fatiha today?"
    },
    "Astagfirullah": {
        "arabic": "أَسْتَغْفِرُ اللَّهَ",
        "meaning": "I seek forgiveness from Allah.",
        "description": "Seeking forgiveness from the Almighty.",
        "reminder": "Take a moment to seek forgiveness with 'Astagfirullah'."
    },
    "SubhanAllah": {
        "arabic": "سُبْحَانَ اللَّهِ",
        "meaning": "Glory be to Allah.",
        "description": "Glorifying Allah.",
        "reminder": "Glorify Allah by saying 'SubhanAllah'."
    },
    "Alhamdulillah": {
        "arabic": "الْحَمْدُ لِلَّهِ",
        "meaning": "Praise be to Allah.",
        "description": "Expressing gratitude to Allah.",
        "reminder": "Be grateful today and say 'Alhamdulillah'."
    },
    "Allahu Akbar": {
        "arabic": "اللَّهُ أَكْبَرُ",
        "meaning": "Allah is the Greatest.",
        "description": "Proclaiming the greatness of Allah.",
        "reminder": "Remember Allah's greatness: 'Allahu Akbar'."
    },
    "1st Kalimah (Tayyabah)": {
        "arabic": "لَا إِلٰهَ إِلَّا اللّٰهُ مُحَمَّدٌ رَسُولُ اللّٰهِ",
        "meaning": "There is no god but Allah, Muhammad is the Messenger of Allah.",
        "description": "The declaration of faith.",
        "reminder": "Recite the 1st Kalimah: La ilaha illallah..."
    },
    "Durood-e-Ibrahim": {
        "arabic": "اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ كَمَا صَلَّيْتَ عَلَى إِبْرَاهِيمَ وَعَلَى آلِ إِبْرَاهِيمَ إِنَّكَ حَمِيدٌ مَجِيدٌ...",
        "meaning": "O Allah, let Your Peace come upon Muhammad and his family as it came upon Ibrahim and his family...",
        "description": "The Salawat recited in prayer.",
        "reminder": "Send blessings upon the Prophet (PBUH) with Durood-e-Ibrahim."
    },
    "Short Durood (Sallallahu Alayhi Wasallam)": {
        "arabic": "صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ",
        "meaning": "May Allah bless him and grant him peace.",
        "description": "A short salutation upon the Prophet (PBUH).",
        "reminder": "Send a quick Salawat: Sallallahu Alayhi Wasallam."
    }
}

def get_category_list():
    return list(DHIKR_CATEGORIES.keys())

def get_subcategory_list(category):
    return list(DHIKR_CATEGORIES.get(category, {}).keys())

def get_sub_subcategory_list(category, subcategory):
    return list(DHIKR_CATEGORIES.get(category, {}).get(subcategory, {}).keys())
