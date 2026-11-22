"""
Expanded voice library with 40+ voices from edge-tts
Grouped by region and verified to exist
"""

BUILTIN_VOICES = [
    # ===== NORTH AMERICA =====
    # United States - Adult
    {"voice_id": "en-US-AvaNeural", "name": "Ava (US Female)", "gender": "female", "age_group": "adult", "language": "en-US", "locale": "en-US", "region": "North America", "country": "United States", "accent": "American", "voice_type": "general"},
    {"voice_id": "en-US-AndrewNeural", "name": "Andrew (US Male)", "gender": "male", "age_group": "adult", "language": "en-US", "locale": "en-US", "region": "North America", "country": "United States", "accent": "American", "voice_type": "general"},
    {"voice_id": "en-US-EmmaNeural", "name": "Emma (US Female)", "gender": "female", "age_group": "adult", "language": "en-US", "locale": "en-US", "region": "North America", "country": "United States", "accent": "American", "voice_type": "general"},
    {"voice_id": "en-US-BrianNeural", "name": "Brian (US Male)", "gender": "male", "age_group": "adult", "language": "en-US", "locale": "en-US", "region": "North America", "country": "United States", "accent": "American", "voice_type": "general"},
    
    # United States - Child
    {"voice_id": "en-US-AnaNeural", "name": "Ana (US Child)", "gender": "female", "age_group": "child", "language": "en-US", "locale": "en-US", "region": "North America", "country": "United States", "accent": "American", "voice_type": "general"},
    
    # Canada
    {"voice_id": "en-CA-ClaraNeural", "name": "Clara (Canadian Female)", "gender": "female", "age_group": "adult", "language": "en-CA", "locale": "en-CA", "region": "North America", "country": "Canada", "accent": "Canadian", "voice_type": "general"},
    {"voice_id": "en-CA-LiamNeural", "name": "Liam (Canadian Male)", "gender": "male", "age_group": "adult", "language": "en-CA", "locale": "en-CA", "region": "North America", "country": "Canada", "accent": "Canadian", "voice_type": "general"},
    
    # Mexico
    {"voice_id": "es-MX-DaliaNeural", "name": "Dalia (Mexican Female)", "gender": "female", "age_group": "adult", "language": "es-MX", "locale": "es-MX", "region": "North America", "country": "Mexico", "accent": "Mexican", "voice_type": "general"},
    {"voice_id": "es-MX-JorgeNeural", "name": "Jorge (Mexican Male)", "gender": "male", "age_group": "adult", "language": "es-MX", "locale": "es-MX", "region": "North America", "country": "Mexico", "accent": "Mexican", "voice_type": "general"},
    
    # ===== SOUTH AMERICA =====
    {"voice_id": "pt-BR-FranciscaNeural", "name": "Francisca (Brazilian Female)", "gender": "female", "age_group": "adult", "language": "pt-BR", "locale": "pt-BR", "region": "South America", "country": "Brazil", "accent": "Brazilian", "voice_type": "general"},
    {"voice_id": "pt-BR-AntonioNeural", "name": "Antonio (Brazilian Male)", "gender": "male", "age_group": "adult", "language": "pt-BR", "locale": "pt-BR", "region": "South America", "country": "Brazil", "accent": "Brazilian", "voice_type": "general"},
    {"voice_id": "es-AR-ElenaNeural", "name": "Elena (Argentine Female)", "gender": "female", "age_group": "adult", "language": "es-AR", "locale": "es-AR", "region": "South America", "country": "Argentina", "accent": "Argentine", "voice_type": "general"},
    {"voice_id": "es-AR-TomasNeural", "name": "Tomas (Argentine Male)", "gender": "male", "age_group": "adult", "language": "es-AR", "locale": "es-AR", "region": "South America", "country": "Argentina", "accent": "Argentine", "voice_type": "general"},
    
    # ===== EUROPE =====
    # United Kingdom
    {"voice_id": "en-GB-SoniaNeural", "name": "Sonia (UK Female)", "gender": "female", "age_group": "adult", "language": "en-GB", "locale": "en-GB", "region": "Europe", "country": "United Kingdom", "accent": "British", "voice_type": "general"},
    {"voice_id": "en-GB-RyanNeural", "name": "Ryan (UK Male)", "gender": "male", "age_group": "adult", "language": "en-GB", "locale": "en-GB", "region": "Europe", "country": "United Kingdom", "accent": "British", "voice_type": "general"},
    
    # Ireland
    {"voice_id": "en-IE-EmilyNeural", "name": "Emily (Irish Female)", "gender": "female", "age_group": "adult", "language": "en-IE", "locale": "en-IE", "region": "Europe", "country": "Ireland", "accent": "Irish", "voice_type": "general"},
    {"voice_id": "en-IE-ConnorNeural", "name": "Connor (Irish Male)", "gender": "male", "age_group": "adult", "language": "en-IE", "locale": "en-IE", "region": "Europe", "country": "Ireland", "accent": "Irish", "voice_type": "general"},
    
    # France
    {"voice_id": "fr-FR-DeniseNeural", "name": "Denise (French Female)", "gender": "female", "age_group": "adult", "language": "fr-FR", "locale": "fr-FR", "region": "Europe", "country": "France", "accent": "French", "voice_type": "general"},
    {"voice_id": "fr-FR-RemyMultilingualNeural", "name": "Remy (French Male)", "gender": "male", "age_group": "adult", "language": "fr-FR", "locale": "fr-FR", "region": "Europe", "country": "France", "accent": "French", "voice_type": "general"},
    
    # Germany
    {"voice_id": "de-DE-TanjaNeural", "name": "Tanja (German Female)", "gender": "female", "age_group": "adult", "language": "de-DE", "locale": "de-DE", "region": "Europe", "country": "Germany", "accent": "German", "voice_type": "general"},
    {"voice_id": "de-DE-ChristophNeural", "name": "Christoph (German Male)", "gender": "male", "age_group": "adult", "language": "de-DE", "locale": "de-DE", "region": "Europe", "country": "Germany", "accent": "German", "voice_type": "general"},
    
    # Spain
    {"voice_id": "es-ES-XimenaNeural", "name": "Ximena (Spanish Female)", "gender": "female", "age_group": "adult", "language": "es-ES", "locale": "es-ES", "region": "Europe", "country": "Spain", "accent": "Spanish", "voice_type": "general"},
    {"voice_id": "es-ES-AlvaroNeural", "name": "Alvaro (Spanish Male)", "gender": "male", "age_group": "adult", "language": "es-ES", "locale": "es-ES", "region": "Europe", "country": "Spain", "accent": "Spanish", "voice_type": "general"},
    
    # Italy
    {"voice_id": "it-IT-ElsaNeural", "name": "Elsa (Italian Female)", "gender": "female", "age_group": "adult", "language": "it-IT", "locale": "it-IT", "region": "Europe", "country": "Italy", "accent": "Italian", "voice_type": "general"},
    {"voice_id": "it-IT-DiegoNeural", "name": "Diego (Italian Male)", "gender": "male", "age_group": "adult", "language": "it-IT", "locale": "it-IT", "region": "Europe", "country": "Italy", "accent": "Italian", "voice_type": "general"},
    
    # Netherlands
    {"voice_id": "nl-NL-ColetteNeural", "name": "Colette (Dutch Female)", "gender": "female", "age_group": "adult", "language": "nl-NL", "locale": "nl-NL", "region": "Europe", "country": "Netherlands", "accent": "Dutch", "voice_type": "general"},
    {"voice_id": "nl-NL-MaartenNeural", "name": "Maarten (Dutch Male)", "gender": "male", "age_group": "adult", "language": "nl-NL", "locale": "nl-NL", "region": "Europe", "country": "Netherlands", "accent": "Dutch", "voice_type": "general"},
    
    # Poland
    {"voice_id": "pl-PL-ZofiaNeural", "name": "Zofia (Polish Female)", "gender": "female", "age_group": "adult", "language": "pl-PL", "locale": "pl-PL", "region": "Europe", "country": "Poland", "accent": "Polish", "voice_type": "general"},
    {"voice_id": "pl-PL-MarekNeural", "name": "Marek (Polish Male)", "gender": "male", "age_group": "adult", "language": "pl-PL", "locale": "pl-PL", "region": "Europe", "country": "Poland", "accent": "Polish", "voice_type": "general"},
    
    # ===== AUSTRALIA / OCEANIA =====
    {"voice_id": "en-AU-NatashaNeural", "name": "Natasha (Australian Female)", "gender": "female", "age_group": "adult", "language": "en-AU", "locale": "en-AU", "region": "Oceania", "country": "Australia", "accent": "Australian", "voice_type": "general"},
    {"voice_id": "en-AU-WilliamMultilingualNeural", "name": "William (Australian Male)", "gender": "male", "age_group": "adult", "language": "en-AU", "locale": "en-AU", "region": "Oceania", "country": "Australia", "accent": "Australian", "voice_type": "general"},
    {"voice_id": "en-NZ-MollyNeural", "name": "Molly (New Zealand Female)", "gender": "female", "age_group": "adult", "language": "en-NZ", "locale": "en-NZ", "region": "Oceania", "country": "New Zealand", "accent": "Kiwi", "voice_type": "general"},
    {"voice_id": "en-NZ-MitchellNeural", "name": "Mitchell (New Zealand Male)", "gender": "male", "age_group": "adult", "language": "en-NZ", "locale": "en-NZ", "region": "Oceania", "country": "New Zealand", "accent": "Kiwi", "voice_type": "general"},
    
    # ===== AFRICA =====
    # South Africa
    {"voice_id": "en-ZA-LeahNeural", "name": "Leah (South African Female)", "gender": "female", "age_group": "adult", "language": "en-ZA", "locale": "en-ZA", "region": "Africa", "country": "South Africa", "accent": "South African", "voice_type": "general"},
    {"voice_id": "en-ZA-LukeNeural", "name": "Luke (South African Male)", "gender": "male", "age_group": "adult", "language": "en-ZA", "locale": "en-ZA", "region": "Africa", "country": "South Africa", "accent": "South African", "voice_type": "general"},
    {"voice_id": "af-ZA-AdriNeural", "name": "Adri (Afrikaans Female)", "gender": "female", "age_group": "adult", "language": "af-ZA", "locale": "af-ZA", "region": "Africa", "country": "South Africa", "accent": "Afrikaans", "voice_type": "general"},
    {"voice_id": "af-ZA-WillemNeural", "name": "Willem (Afrikaans Male)", "gender": "male", "age_group": "adult", "language": "af-ZA", "locale": "af-ZA", "region": "Africa", "country": "South Africa", "accent": "Afrikaans", "voice_type": "general"},
    
    # Nigeria
    {"voice_id": "en-NG-EzinneNeural", "name": "Ezinne (Nigerian Female)", "gender": "female", "age_group": "adult", "language": "en-NG", "locale": "en-NG", "region": "Africa", "country": "Nigeria", "accent": "Nigerian", "voice_type": "general"},
    {"voice_id": "en-NG-AbeoNeural", "name": "Abeo (Nigerian Male)", "gender": "male", "age_group": "adult", "language": "en-NG", "locale": "en-NG", "region": "Africa", "country": "Nigeria", "accent": "Nigerian", "voice_type": "general"},
    
    # Kenya
    {"voice_id": "en-KE-AsiliaNeural", "name": "Asilia (Kenyan Female)", "gender": "female", "age_group": "adult", "language": "en-KE", "locale": "en-KE", "region": "Africa", "country": "Kenya", "accent": "Kenyan", "voice_type": "general"},
    {"voice_id": "en-KE-ChilembaNeural", "name": "Chilemba (Kenyan Male)", "gender": "male", "age_group": "adult", "language": "en-KE", "locale": "en-KE", "region": "Africa", "country": "Kenya", "accent": "Kenyan", "voice_type": "general"},
    {"voice_id": "sw-KE-ZuriNeural", "name": "Zuri (Swahili Female)", "gender": "female", "age_group": "adult", "language": "sw-KE", "locale": "sw-KE", "region": "Africa", "country": "Kenya", "accent": "Swahili", "voice_type": "general"},
    {"voice_id": "sw-KE-RafikiNeural", "name": "Rafiki (Swahili Male)", "gender": "male", "age_group": "adult", "language": "sw-KE", "locale": "sw-KE", "region": "Africa", "country": "Kenya", "accent": "Swahili", "voice_type": "general"},
    
    # Egypt
    {"voice_id": "ar-EG-SalmaNeural", "name": "Salma (Egyptian Female)", "gender": "female", "age_group": "adult", "language": "ar-EG", "locale": "ar-EG", "region": "Africa", "country": "Egypt", "accent": "Egyptian", "voice_type": "general"},
    {"voice_id": "ar-EG-ShakirNeural", "name": "Shakir (Egyptian Male)", "gender": "male", "age_group": "adult", "language": "ar-EG", "locale": "ar-EG", "region": "Africa", "country": "Egypt", "accent": "Egyptian", "voice_type": "general"},
    
    # ===== ASIA =====
    # India
    {"voice_id": "en-IN-NeerjaNeural", "name": "Neerja (India Female)", "gender": "female", "age_group": "adult", "language": "en-IN", "locale": "en-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "general"},
    {"voice_id": "en-IN-PrabhatNeural", "name": "Prabhat (India Male)", "gender": "male", "age_group": "adult", "language": "en-IN", "locale": "en-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "general"},
    {"voice_id": "hi-IN-SwaraNeural", "name": "Swara (Hindi Female)", "gender": "female", "age_group": "adult", "language": "hi-IN", "locale": "hi-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "general"},
    {"voice_id": "hi-IN-MadhurNeural", "name": "Madhur (Hindi Male)", "gender": "male", "age_group": "adult", "language": "hi-IN", "locale": "hi-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "general"},
    {"voice_id": "te-IN-ShrutiNeural", "name": "Shruti (Telugu Female)", "gender": "female", "age_group": "adult", "language": "te-IN", "locale": "te-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "general"},
    {"voice_id": "te-IN-MohanNeural", "name": "Mohan (Telugu Male)", "gender": "male", "age_group": "adult", "language": "te-IN", "locale": "te-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "general"},
    {"voice_id": "ta-IN-PallaviNeural", "name": "Pallavi (Tamil Female)", "gender": "female", "age_group": "adult", "language": "ta-IN", "locale": "ta-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "general"},
    {"voice_id": "ta-IN-ValluvarNeural", "name": "Valluvar (Tamil Male)", "gender": "male", "age_group": "adult", "language": "ta-IN", "locale": "ta-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "general"},
    
    # Child-style presets for India (using existing presets)
    {"voice_id": "preset-child-en-IN", "name": "Child-Style (India English)", "gender": "female", "age_group": "child", "language": "en-IN", "locale": "en-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "child-style", "base_voice": "en-IN-NeerjaNeural", "preset_pitch": 1.3, "preset_rate": 1.1},
    {"voice_id": "preset-child-hi-IN", "name": "Child-Style (Hindi)", "gender": "female", "age_group": "child", "language": "hi-IN", "locale": "hi-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "child-style", "base_voice": "hi-IN-SwaraNeural", "preset_pitch": 1.3, "preset_rate": 1.1},
    {"voice_id": "preset-child-te-IN", "name": "Child-Style (Telugu)", "gender": "female", "age_group": "child", "language": "te-IN", "locale": "te-IN", "region": "Asia", "country": "India", "accent": "Indian", "voice_type": "child-style", "base_voice": "te-IN-ShrutiNeural", "preset_pitch": 1.3, "preset_rate": 1.1},
    
    # Japan
    {"voice_id": "ja-JP-NanamiNeural", "name": "Nanami (Japanese Female)", "gender": "female", "age_group": "adult", "language": "ja-JP", "locale": "ja-JP", "region": "Asia", "country": "Japan", "accent": "Japanese", "voice_type": "general"},
    {"voice_id": "ja-JP-KeitaNeural", "name": "Keita (Japanese Male)", "gender": "male", "age_group": "adult", "language": "ja-JP", "locale": "ja-JP", "region": "Asia", "country": "Japan", "accent": "Japanese", "voice_type": "general"},
    
    # China
    {"voice_id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao (Chinese Female)", "gender": "female", "age_group": "adult", "language": "zh-CN", "locale": "zh-CN", "region": "Asia", "country": "China", "accent": "Chinese", "voice_type": "general"},
    {"voice_id": "zh-CN-YunxiNeural", "name": "Yunxi (Chinese Male)", "gender": "male", "age_group": "adult", "language": "zh-CN", "locale": "zh-CN", "region": "Asia", "country": "China", "accent": "Chinese", "voice_type": "general"},
    
    # Korea
    {"voice_id": "ko-KR-SunHiNeural", "name": "SunHi (Korean Female)", "gender": "female", "age_group": "adult", "language": "ko-KR", "locale": "ko-KR", "region": "Asia", "country": "South Korea", "accent": "Korean", "voice_type": "general"},
    {"voice_id": "ko-KR-InJoonNeural", "name": "InJoon (Korean Male)", "gender": "male", "age_group": "adult", "language": "ko-KR", "locale": "ko-KR", "region": "Asia", "country": "South Korea", "accent": "Korean", "voice_type": "general"},
    
    # ===== MIDDLE EAST =====
    {"voice_id": "ar-SA-ZariyahNeural", "name": "Zariyah (Saudi Female)", "gender": "female", "age_group": "adult", "language": "ar-SA", "locale": "ar-SA", "region": "Middle East", "country": "Saudi Arabia", "accent": "Gulf Arabic", "voice_type": "general"},
    {"voice_id": "ar-SA-HamedNeural", "name": "Hamed (Saudi Male)", "gender": "male", "age_group": "adult", "language": "ar-SA", "locale": "ar-SA", "region": "Middle East", "country": "Saudi Arabia", "accent": "Gulf Arabic", "voice_type": "general"},
]

# Preview texts for each language
PREVIEW_TEXTS = {
    "en": "Hello! I'm {name}. I can help you create natural sounding speech.",
    "es": "¡Hola! Soy {name}. Puedo ayudarte a crear voz natural.",
    "pt": "Olá! Eu sou {name}. Posso ajudá-lo a criar fala natural.",
    "fr": "Bonjour! Je suis {name}. Je peux vous aider à créer une parole naturelle.",
    "de": "Hallo! Ich bin {name}. Ich kann Ihnen helfen, natürliche Sprache zu erstellen.",
    "it": "Ciao! Sono {name}. Posso aiutarti a creare una voce naturale.",
    "nl": "Hallo! Ik ben {name}. Ik kan je helpen natuurlijke spraak te creëren.",
    "pl": "Cześć! Jestem {name}. Mogę pomóc Ci stworzyć naturalną mowę.",
    "ja": "こんにちは！私は{name}です。自然な音声を作成するお手伝いをします。",
    "zh": "你好！我是{name}。我可以帮助你创建自然的语音。",
    "ko": "안녕하세요! 저는 {name}입니다. 자연스러운 음성을 만들 수 있습니다.",
    "ar": "مرحبًا! أنا {name}. يمكنني مساعدتك في إنشاء كلام طبيعي.",
    "hi": "नमस्ते! मैं {name} हूं। मैं आपको प्राकृतिक आवाज़ बनाने में मदद कर सकता हूं।",
    "te": "హలో! నేను {name}. నేను సహజ శబ్దం సృష్టించడానికి మీకు సహాయం చేయగలను.",
    "ta": "வணக்கம்! நான் {name}. இயற்கையான குரலை உருவாக்க உங்களுக்கு உதவ முடியும்.",
    "af": "Hallo! Ek is {name}. Ek kan jou help om natuurlike spraak te skep.",
    "sw": "Habari! Mimi ni {name}. Ninaweza kukusaidia kuunda hotuba asili.",
}

def get_preview_text(language_code, voice_name):
    """Get preview text for a language, with fallback to English"""
    # Extract base language (en-US -> en)
    base_lang = language_code.split('-')[0] if language_code else 'en'
    text_template = PREVIEW_TEXTS.get(base_lang, PREVIEW_TEXTS['en'])
    return text_template.format(name=voice_name.split('(')[0].strip())
