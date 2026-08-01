"""Telugu native conversation formatting and detection utility for JARVIS."""

import os
import re
from JARVIS.core.memory.memory_preferences import get_preference, set_preference

TELUGU_WORDS = {
    "entha", "cheyyi", "teruvu", "pettukunnanu", "unnanu", "pettuko",
    "samayam", "eppudu", "ippudu", "sare", "avunu", "kosam", "ippude",
    "konchem", "cheyyaku", "cheyaku", "undhi", "undi", "chestunnanu",
    "nanna", "amma", "em chestunnav", "bagunnava", "ledu", "lanti",
    "kooda", "cheyyandi", "chesi", "choodu", "chudu", "pettuko", "unnayi",
    "unnam", "cheppu", "ante", "enti", "yenti", "chey"
}

TELUGU_SCRIPT_MAP = {
    "sir": "సార్",
    "ippudu": "ఇప్పుడు",
    "samayam": "సమయం",
    "sare": "సరే",
    "chestunnanu": "చేస్తున్నాను",
    "mee": "మీ",
    "battery": "బ్యాటరీ",
    "undi": "ఉంది",
    "undhi": "ఉంది",
    "em": "ఏం",
    "chestunnav": "చేస్తున్నావు",
    "chestunnavu": "చేస్తున్నావు",
    "ready": "రెడీ",
    "ga": "గా",
    "unnanu": "ఉన్నాను",
    "avunu": "అవును",
    "anni": "అన్ని",
    "normal": "నార్మల్",
    "pani": "పని",
    "chestunnayi": "చేస్తున్నాయి",
    "welcome": "వెల్కమ్",
    "kosam": "కోసం",
    "ippude": "ఇప్పుడే",
    "konchem": "కొంచెం",
    "wait": "వెయిట్",
    "cheyyandi": "చేయండి",
    "complete": "కంప్లీట్",
    "ayyindi": "అయింది",
    "open": "ఓపెన్",
    "play": "ప్లే",
}

def contains_telugu_script(text: str) -> bool:
    """Return True if text contains Telugu Unicode characters."""
    return any(ord(char) >= 0x0c00 and ord(char) <= 0x0c7f for char in text)

def detect_language(command: str) -> str:
    """Detect if the command is Telugu or English."""
    if contains_telugu_script(command):
        return "telugu"
    lowered = command.lower()
    # Split text into alphabetic tokens for fast O(1) matching
    words = set(re.findall(r"\b\w+\b", lowered))
    for word in TELUGU_WORDS:
        if word.lower() in words:
            return "telugu"
    return "english"

def translate_to_telugu_script(text: str) -> str:
    """Convert transliterated Telugu to Telugu script based on mapping."""
    words = text.split()
    converted_words = []
    for word in words:
        # Strip punctuation for matching
        clean_word = re.sub(r"[^\w]", "", word).lower()
        punctuation_before = re.match(r"^[^\w]*", word).group(0)
        punctuation_after = re.search(r"[^\w]*$", word).group(0)
        
        if clean_word in TELUGU_SCRIPT_MAP:
            converted = TELUGU_SCRIPT_MAP[clean_word]
            converted_words.append(f"{punctuation_before}{converted}{punctuation_after}")
        else:
            converted_words.append(word)
    return " ".join(converted_words)

def format_telugu_response(text: str, user_command: str = "") -> str:
    """Format an English response into conversational Telugu if the preferred language is Telugu."""
    # Check if preference is set to Telugu
    pref_lang = get_preference("preferred_language")
    if pref_lang != "telugu":
        # Check if the command itself was in Telugu (dynamic backup)
        if user_command and detect_language(user_command) == "telugu":
            set_preference("preferred_language", "telugu")
        else:
            return text

    # If the user speaks pure English, bypass translation and respond in English.
    if user_command and detect_language(user_command) == "english":
        return text

    # Apply formatting mappings for common template strings
    cleaned = text.strip()
    lowered = cleaned.lower()
    formatted = cleaned

    # 1. Startup / Greetings
    if any(phrase in lowered for phrase in ["good day", "good morning", "all systems online", "systems are ready", "hesa is ready", "systems are operational"]):
        formatted = "Namaskaram sir. HESA siddhanga undi. Mee commands kosam ready ga unnanu sir."
    # 2. Confirmations / Tasks
    elif any(phrase in lowered for phrase in ["task completed", "command completed", "successfully completed"]):
        formatted = "Task complete ayyindi sir."
    # 3. Internet Warnings
    elif any(phrase in lowered for phrase in ["internet connection is down", "no internet connection", "internet connection ledu"]):
        formatted = "Internet connection ledu sir."
    # 4. Security Verification
    elif any(phrase in lowered for phrase in ["security verification complete", "integrity check passed"]):
        formatted = "Security verification complete ayyindi."
    # 5. System Ready
    elif any(phrase in lowered for phrase in ["system is ready"]):
        formatted = "System ready ga undi sir."
    # Check other specific patterns
    elif "Opening" in cleaned and "sir." in cleaned:
        # Extract app/web target
        match = re.search(r"Opening\s+(.+?),\s+sir\.", cleaned)
        if match:
            target = match.group(1)
            formatted = f"Sare sir, {target} open chestunnanu."
    elif "current time is" in cleaned:
        match = re.search(r"current time is\s+([^,]+)", cleaned)
        if match:
            time_val = match.group(1).strip()
            formatted = f"Sir, ippudu samayam {time_val}."
    elif "Battery is at" in cleaned:
        match = re.search(r"Battery is at\s+(\d+)\s+percent", cleaned)
        if match:
            percent = match.group(1)
            formatted = f"Sir, mee battery {percent}% undi."
    elif "Searching Google for" in cleaned:
        match = re.search(r"Searching Google for\s+(.+?),\s+sir\.", cleaned)
        if match:
            query = match.group(1)
            formatted = f"Sare sir, Google lo {query} kosam search chestunnanu."
    elif "remember that you love" in cleaned:
        match = re.search(r"remember that you love\s+(.+?)\.", cleaned)
        if match:
            artist = match.group(1)
            formatted = f"Sare sir, mee favorite artist {artist} ani gurthupettukunnanu."
    elif "Default volume set to" in cleaned:
        match = re.search(r"Default volume set to\s+(\d+)\s+percent", cleaned)
        if match:
            vol = match.group(1)
            formatted = f"Sare sir, default volume {vol}% ki set chesanu."
    elif "remember you prefer" in cleaned:
        match = re.search(r"remember you prefer\s+(.+?)\.", cleaned)
        if match:
            app = match.group(1)
            formatted = f"Sare sir, mee preferred app {app} ani gurthupettukunnanu."
    elif "local fallback routines" in cleaned:
        formatted = "Mee commands kosam ready ga unnanu sir."

    # If the user typed in Telugu script, convert transliterated output to Telugu script
    if user_command and contains_telugu_script(user_command):
        formatted = translate_to_telugu_script(formatted)
        
    return formatted

def translate_telugu_script_to_transliteration(command: str) -> str:
    """Convert common Telugu script phrases to transliterated text for routing."""
    if not contains_telugu_script(command):
        return command
        
    trans_map = {
        "సమయం ఎంత": "time entha",
        "టైం ఎంత": "time entha",
        "ఎంత": "entha",
        "సమయం": "samayam",
        "బ్యాటరీ": "battery",
        "క్రోమ్": "chrome",
        "ఓపెన్ చేయి": "open cheyyi",
        "ఓపెన్ చేయండి": "open cheyyi",
        "ఓపెన్": "open",
        "తెరవు": "teruvu",
        "స్టార్ట్ చేయి": "start cheyyi",
        "రన్ చేయి": "run cheyyi",
        "లాంచ్ చేయి": "launch cheyyi",
        "ప్లే చేయి": "play cheyyi",
        "డిలీట్ చేయకు": "delete cheyyaku",
        "ఏం చేస్తున్నావు": "em chestunnav",
        "బాగున్నావా": "bagunnava",
        "థాంక్స్": "thanks",
        "ధన్యవాదాలు": "thanks"
    }
    
    cmd = command
    for script, trans in trans_map.items():
        cmd = cmd.replace(script, trans)
    return cmd

def normalize_telugu_command(command: str) -> str:
    """Normalize and convert Telugu/mixed commands to equivalent English commands."""
    cmd = translate_telugu_script_to_transliteration(command)
    cmd = cmd.lower().strip()
    cmd = re.sub(r"\b(jarvis|hesa)\b", "", cmd).strip()
    cmd = re.sub(r"[?!.]", "", cmd).strip()
    
    if cmd in ["em chestunnav", "em chestunnavu"]:
        return "what are you doing"
    if cmd in ["bagunnava", "bagunnara"]:
        return "how are you"
    if cmd in ["thanks", "thank you", "dhanyavadalu"]:
        return "thanks"
        
    if "time entha" in cmd or "samayam entha" in cmd or "time cheppu" in cmd:
        return "what time"
    if "battery entha" in cmd or "battery entha undi" in cmd or "naa battery entha undi" in cmd:
        return "battery status"
        
    action_words = r"(open cheyyi|teruvu|start cheyyi|run cheyyi|launch cheyyi|open chey|terava|start chey|run chey|launch chey)"
    match = re.search(r"(.+?)\s+" + action_words, cmd)
    if match:
        target = match.group(1).strip()
        return f"open {target}"
        
    match_play = re.search(r"(.+?)\s+(play cheyyi|play chey|vinipinchu)", cmd)
    if match_play:
        target = match_play.group(1).strip()
        if target in ["song", "music", "patalu", "pata"]:
            return "play music"
        return f"play {target} on spotify"
        
    return cmd

def get_similarity_score(str1: str, str2: str) -> float:
    """Compute lightweight Jaccard similarity score between two command strings."""
    w1 = set(re.findall(r"\w+", str1.lower()))
    w2 = set(re.findall(r"\w+", str2.lower()))
    if not w1 and not w2:
        return 1.0
    if not w1 or not w2:
        return 0.0
    intersection = w1.intersection(w2)
    union = w1.union(w2)
    
    jaccard = len(intersection) / len(union)
    
    s1_clean = " ".join(re.findall(r"\w+", str1.lower()))
    s2_clean = " ".join(re.findall(r"\w+", str2.lower()))
    if s1_clean and s2_clean:
        if s1_clean in s2_clean or s2_clean in s1_clean:
            len_ratio = min(len(s1_clean), len(s2_clean)) / max(len(s1_clean), len(s2_clean))
            return max(jaccard, 0.5 + 0.5 * len_ratio)
            
    return jaccard

def match_telugu_intent(command: str) -> dict | None:
    """
    Match a user command against the Telugu Knowledge Base using fuzzy matching,
    confidence scoring, and context memory checks.
    """
    import json
    from JARVIS.core.memory.memory_preferences import get_preference, set_preference
    
    # 1. Check/Load Learned Mappings from learning_memory.json
    learned_path = os.path.join("knowledge", "telugu", "learning_memory.json")
    learned_cmds = {}
    if os.path.exists(learned_path):
        try:
            with open(learned_path, "r", encoding="utf-8") as f:
                learned_cmds = json.load(f)
        except Exception:
            pass
            
    # Merge learned_commands from preferences
    pref_learned = get_preference("learned_commands") or {}
    learned_cmds.update(pref_learned)
    
    # Check exact match on learned commands first
    norm_cmd = command.lower().strip()
    if norm_cmd in learned_cmds:
        return {
            "intent": "learned_command",
            "target": learned_cmds[norm_cmd],
            "confidence": 1.0
        }
        
    # Check fuzzy match on learned commands
    best_match = None
    best_score = 0.0
    best_target = None
    
    for l_cmd, target in learned_cmds.items():
        score = get_similarity_score(norm_cmd, l_cmd)
        if score > best_score:
            best_score = score
            best_match = l_cmd
            best_target = target
            
    if best_score >= 0.8:
        return {
            "intent": "learned_command",
            "target": best_target,
            "confidence": best_score
        }

    # 2. Check Context Memory (Enhancement)
    last_context = get_preference("last_telugu_context")
    if norm_cmd in {"enti", "yenti", "yento", "ento", "enti sir", "cheppu"}:
        if last_context == "battery":
            return {
                "intent": "system_query",
                "target": "battery status",
                "confidence": 0.95
            }
        elif last_context == "time":
            return {
                "intent": "system_query",
                "target": "what time",
                "confidence": 0.95
            }

    # 3. Load all Telugu KB files
    kb_files = {
        "commands.json": "system_command",
        "greetings.json": "greeting",
        "daily_conversations.json": "conversational",
        "technology.json": "technology",
        "education.json": "education"
    }
    
    best_kb_match = None
    best_kb_score = 0.0
    best_kb_ans = None
    best_kb_type = None
    
    for filename, kb_type in kb_files.items():
        path = os.path.join("knowledge", "telugu", filename)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                db = json.load(f)
                
            for query, response in db.items():
                score = get_similarity_score(norm_cmd, query)
                if score > best_kb_score:
                    best_kb_score = score
                    best_kb_match = query
                    best_kb_ans = response
                    best_kb_type = kb_type
        except Exception:
            pass
            
    if best_kb_score >= 0.60:
        # Save active context
        if "battery" in best_kb_match:
            set_preference("last_telugu_context", "battery")
        elif "time" in best_kb_match or "samayam" in best_kb_match:
            set_preference("last_telugu_context", "time")
            
        if best_kb_type == "system_command":
            return {
                "intent": "system_query",
                "target": best_kb_ans,
                "confidence": best_kb_score
            }
        else:
            return {
                "intent": "talk",
                "target": best_kb_ans,
                "confidence": best_kb_score
            }
            
    return None
