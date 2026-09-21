from typing import Tuple, Optional, Dict, Any

SUPPORTED_LOCALES = {"en", "te", "hi", "ta", "kn", "ml"}

# Deterministic multilingual templates for farm task lifecycle events
TEMPLATES: Dict[str, Dict[str, Dict[str, str]]] = {
    "TASK_DUE": {
        "en": {
            "title": "Task Due: {title}",
            "message": "Task '{title}' is now due for execution. Priority: {priority}."
        },
        "te": {
            "title": "టాస్క్ గడువు వచ్చింది: {title}",
            "message": "'{title}' టాస్క్ అమలు చేయడానికి సమయం ఆసన్నమైంది. ప్రాధాన్యత: {priority}."
        },
        "hi": {
            "title": "कार्य देय है: {title}",
            "message": "कार्य '{title}' अब निष्पादन के लिए देय है। प्राथमिकता: {priority}।"
        },
        "ta": {
            "title": "பணி நிலுவையில் உள்ளது: {title}",
            "message": "'{title}' பணி இப்போது செய்யப்பட வேண்டும். முன்னுரிமை: {priority}."
        },
        "kn": {
            "title": "ಕಾರ್ಯ ಬಾಕಿ ಇದೆ: {title}",
            "message": "'{title}' ಕಾರ್ಯವನ್ನು ಕಾರ್ಯಗತಗೊಳಿಸಲು ಈಗ ಸಮಯವಾಗಿದೆ. ಆದ್ಯತೆ: {priority}."
        },
        "ml": {
            "title": "ടാസ്ക് സമയം എത്തി: {title}",
            "message": "'{title}' എന്ന ടാസ്ക് നടപ്പിലാക്കാനുള്ള സമയം എത്തിയിരിക്കുന്നു. മുൻഗണന: {priority}."
        }
    },
    "TASK_OVERDUE": {
        "en": {
            "title": "Task Overdue: {title}",
            "message": "Action required: Task '{title}' is overdue since {due_time}."
        },
        "te": {
            "title": "టాస్క్ గడువు దాటింది: {title}",
            "message": "తక్షణ చర్య అవసరం: '{title}' టాస్క్ {due_time} నుండి గడువు దాటింది."
        },
        "hi": {
            "title": "कार्य अतिदेय हो गया है: {title}",
            "message": "कार्रवाई आवश्यक: कार्य '{title}' {due_time} से अतिदेय है।"
        },
        "ta": {
            "title": "பணி தாமதமானது: {title}",
            "message": "நடவடிக்கை தேவை: '{title}' பணி {due_time} முதல் தாமதமாக உள்ளது."
        },
        "kn": {
            "title": "ಕಾರ್ಯದ ಅವಧಿ ಮೀರಿದೆ: {title}",
            "message": "ಕ್ರಮ ಅಗತ್ಯ: '{title}' ಕಾರ್ಯವು {due_time} ರಿಂದ ಮೀರಿದೆ."
        },
        "ml": {
            "title": "ടാസ്ക് കാലാവധി കഴിഞ്ഞു: {title}",
            "message": "നടപടി ആവശ്യം: '{title}' ടാസ്ക് {due_time} മുതൽ കാലാവധി കഴിഞ്ഞു."
        }
    },
    "TASK_EXPIRED": {
        "en": {
            "title": "Task Expired: {title}",
            "message": "Task '{title}' has reached its expiration window and is now expired."
        },
        "te": {
            "title": "టాస్క్ గడువు ముగిసింది: {title}",
            "message": "'{title}' టాస్క్ గడువు ముగింపు విండోను చేరుకుంది మరియు ఇప్పుడు ముగిసింది."
        },
        "hi": {
            "title": "कार्य समाप्त हो गया: {title}",
            "message": "कार्य '{title}' अपनी समाप्ति सीमा तक पहुंच गया है और अब समाप्त हो गया है।"
        },
        "ta": {
            "title": "பணி காலாவதியானது: {title}",
            "message": "'{title}' பணி அதன் காலாவதி சாளரத்தை அடைந்து இப்போது காலாவதியாகிவிட்டது."
        },
        "kn": {
            "title": "ಕಾರ್ಯ ಮುಕ್ತಾಯಗೊಂಡಿದೆ: {title}",
            "message": "'{title}' ಕಾರ್ಯವು ಮುಕ್ತಾಯ ಸಮಯವನ್ನು ತಲುಪಿದ್ದು, ಈಗ ಮುಕ್ತಾಯಗೊಂಡಿದೆ."
        },
        "ml": {
            "title": "ടാസ്ക് കാലഹരണപ്പെട്ടു: {title}",
            "message": "'{title}' ടാസ്ക് കാലാവധി പൂർത്തിയാക്കി ഇപ്പോൾ റദ്ദായി."
        }
    },
    "TASK_REMINDER": {
        "en": {
            "title": "Reminder: Upcoming Task {title}",
            "message": "Reminder: '{title}' is scheduled soon ({due_time}). Please prepare necessary materials."
        },
        "te": {
            "title": "జ్ఞాపిక: రాబోయే టాస్క్ {title}",
            "message": "జ్ఞాపిక: '{title}' త్వరలో షెడ్యూల్ చేయబడింది ({due_time}). దయచేసి అవసరమైన సన్నాహాలు చేసుకోండి."
        },
        "hi": {
            "title": "स्मरणपत्र: आगामी कार्य {title}",
            "message": "स्मरणपत्र: '{title}' जल्द ही निर्धारित है ({due_time})। कृपया आवश्यक सामग्री तैयार रखें।"
        },
        "ta": {
            "title": "நினைவூட்டல்: வரவிருக்கும் பணி {title}",
            "message": "நினைவூட்டல்: '{title}' விரைவில் திட்டமிடப்பட்டுள்ளது ({due_time}). தயவுசெய்து தேவையானவற்றைத் தயார் செய்யவும்."
        },
        "kn": {
            "title": "ಜ್ಞಾಪನೆ: ಮುಂಬರುವ ಕಾರ್ಯ {title}",
            "message": "ಜ್ಞಾಪನೆ: '{title}' ಶೀಘ್ರದಲ್ಲೇ ನಿಗದಿಯಾಗಿದೆ ({due_time}). ದಯವಿಟ್ಟು ಅಗತ್ಯ ಸಿದ್ಧತೆಗಳನ್ನು ಮಾಡಿಕೊಳ್ಳಿ."
        },
        "ml": {
            "title": "ഓർമ്മപ്പെടുത്തൽ: വരാനിരിക്കുന്ന ടാസ്ക് {title}",
            "message": "ഓർമ്മപ്പെടുത്തൽ: '{title}' ഉടൻ ഷെഡ്യൂൾ ചെയ്തിരിക്കുന്നു ({due_time}). ദയവായി ആവശ്യമായ ഒരുക്കങ്ങൾ നടത്തുക."
        }
    }
}

DEFAULT_FALLBACK_TITLES = {
    "en": "Farm Task",
    "te": "వ్యవసాయ పని",
    "hi": "खेत कार्य",
    "ta": "பண்ணை பணி",
    "kn": "ಕೃಷಿ ಕಾರ್ಯ",
    "ml": "ഫാം ടാസ്ക്"
}


def format_notification(
    event_type: str,
    task_title: Optional[str] = None,
    priority: str = "MEDIUM",
    due_time: Optional[str] = None,
    locale: str = "en",
    payload: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """
    Deterministically formats localized notification title and message from durable task event data.
    Never fabricates agronomic or weather information.
    Falls back safely to 'en' if the requested locale is not supported.
    """
    clean_locale = (locale or "en").lower().strip()
    if clean_locale not in SUPPORTED_LOCALES:
        clean_locale = "en"

    event_templates = TEMPLATES.get(event_type, TEMPLATES.get("TASK_DUE", {}))
    localized = event_templates.get(clean_locale) or event_templates.get("en", {
        "title": "Notification: {title}",
        "message": "Update for task '{title}'."
    })

    safe_title = (task_title or "").strip()
    if not safe_title:
        safe_title = DEFAULT_FALLBACK_TITLES.get(clean_locale, "Farm Task")

    safe_due_time = (due_time or "").strip()
    if not safe_due_time and payload:
        safe_due_time = str(payload.get("due_at") or payload.get("due_date") or "scheduled time")
    if not safe_due_time:
        safe_due_time = "scheduled time"

    title_fmt = localized.get("title", "{title}")
    msg_fmt = localized.get("message", "{title}")

    title = title_fmt.format(
        title=safe_title,
        priority=priority,
        due_time=safe_due_time
    )
    message = msg_fmt.format(
        title=safe_title,
        priority=priority,
        due_time=safe_due_time
    )

    return title, message
