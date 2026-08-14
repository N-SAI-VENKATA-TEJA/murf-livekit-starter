import json
import aiohttp
import logging
import os
from datetime import UTC, datetime

import motor.motor_asyncio
from bson import ObjectId
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    ChatContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

# Setup root logger to dump to file for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent_debug.log", mode="w", encoding="utf-8")
    ]
)

load_dotenv(".env.local")

# ---------------------------------------------------------------------------
# MongoDB — lazy initialization per event loop to avoid asyncio loop conflicts
# ---------------------------------------------------------------------------
_mongo_clients = {}

def get_children_col():
    import asyncio
    loop = asyncio.get_running_loop()
    if loop not in _mongo_clients:
        _mongo_clients[loop] = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URI"])
    return _mongo_clients[loop]["bolobuddy"]["children"]


def get_calls_col():
    import asyncio
    loop = asyncio.get_running_loop()
    if loop not in _mongo_clients:
        _mongo_clients[loop] = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URI"])
    return _mongo_clients[loop]["bolobuddy"]["calls"]


# ---------------------------------------------------------------------------
# Call analytics — persists one record per session to the calls collection
# ---------------------------------------------------------------------------
async def save_call_analytics(
    assistant: "Assistant",
    session_id: str,
    channel: str = "browser",
) -> None:
    """Write exactly one call analytics document to the 'calls' collection.

    Uses assistant.analytics_recorded flag to prevent duplicate writes.
    Safe to call multiple times — only the first call writes to MongoDB.
    """
    if assistant.analytics_recorded:
        logger.info("[analytics] Skipping duplicate write — already recorded.")
        return

    assistant.analytics_recorded = True

    words_learned_count = len(assistant.learned_words)
    outcome = "success" if words_learned_count >= 2 else "failed"

    doc = {
        "child_id": assistant._child_id,
        "session_id": session_id,
        "channel": channel,
        "outcome": outcome,
        "words_learned": words_learned_count,
        "created_at": datetime.now(UTC),
    }

    logger.info(
        f"[analytics] Saving call record: child_id={assistant._child_id!r} "
        f"outcome={outcome!r} words_learned={words_learned_count} "
        f"session_id={session_id!r}"
    )

    try:
        col = get_calls_col()
        await col.insert_one(doc)
        logger.info("[analytics] Call record saved successfully.")
    except Exception as exc:
        logger.error(f"[analytics] Failed to save call record: {exc}")
        # Reset flag so a retry is possible if something calls this again
        assistant.analytics_recorded = False


# ---------------------------------------------------------------------------
# Proactive memory loader — called from Python at session start, NOT by LLM
# ---------------------------------------------------------------------------
async def load_child_memory(child_id: str) -> dict | None:
    """Load the child's memory from MongoDB before the session starts.
    Returns a dict with child profile, or None if not found / invalid id.
    """
    logger.info(f"[memory] Proactively loading memory for child_id={child_id!r}")
    try:
        oid = ObjectId(child_id)
    except Exception:
        logger.warning(f"[memory] Invalid child_id format: {child_id!r}")
        return None

    col = get_children_col()
    doc = await col.find_one(
        {"_id": oid},
        {"name": 1, "language_preference": 1, "words_learned": 1, "word_mistakes": 1, "last_interaction": 1},
    )
    if doc is None:
        logger.info(f"[memory] No document found for child_id={child_id}")
        return None

    last_interaction = None
    if doc.get("last_interaction"):
        last_interaction = doc["last_interaction"].isoformat()

    result = {
        "found": True,
        "name": doc.get("name", ""),
        "language_preference": doc.get("language_preference", ""),
        "words_learned": doc.get("words_learned", []),
        "word_mistakes": doc.get("word_mistakes", []),
        "last_interaction": last_interaction,
    }
    logger.info(
        f"[memory] Loaded: name={result['name']!r}, "
        f"words_learned={result['words_learned']}, "
        f"last_interaction={result['last_interaction']!r}"
    )
    return result


# ---------------------------------------------------------------------------
# System prompt builder — child memory injected at session start
# ---------------------------------------------------------------------------
def build_system_prompt(memory: dict | None) -> tuple[str, str]:
    # Build the memory/greeting context block injected into the system prompt
    # and generate the initial deterministic greeting string.
    if memory is None or not memory.get("found"):
        memory_context = """
## CHILD MEMORY STATUS: NOT FOUND
- Memory could not be loaded (new device or invalid session).
- Treat this as a FIRST-TIME session.
- Introduce yourself as Chinnu and proactively start teaching a fun first word (e.g. "Apple", "Dog", "Elephant").
- Do NOT ask the child what they want to learn.
"""
        greeting = "Welcome! I am Chinnu from Bolo Buddy. Let's learn a fun new word today. Please repeat after me: Apple."
    else:
        name = memory.get("name", "")
        words_learned = memory.get("words_learned", [])
        last_interaction = memory.get("last_interaction")
        word_mistakes = memory.get("word_mistakes", [])
        
        words_str = ", ".join(words_learned) if words_learned else "none yet"
        recent_words_str = ", ".join(words_learned[-3:]) if words_learned else "none yet"
        
        mistakes_str = (
            ", ".join([f"{m['word']} ({m['mistake_count']} times)" for m in word_mistakes])
            if word_mistakes
            else "none"
        )

        if last_interaction is None:
            memory_context = f"""
## CHILD MEMORY STATUS: FIRST SESSION
- Child's name: {name}
- Words learned so far: {words_str}
- This is their VERY FIRST conversation — no prior sessions.
- Introduce yourself as Chinnu from BoloBuddy.
- Proactively start teaching a simple, fun first word (e.g. "Apple", "Dog") — do NOT ask what they want to learn.
"""
            greeting = f"Welcome, {name}! I am Chinnu from Bolo Buddy. Let's learn a fun new word today. Please repeat after me: Apple."
        else:
            # Deterministically pick a new word so we don't wait for them to say 'yes'
            candidate_words = [
                ("Banana", "A banana is a long yellow fruit that monkeys love to eat."),
                ("Cat", "A cat is a small furry animal that says meow."),
                ("Elephant", "An elephant is a very big animal with a long nose called a trunk."),
                ("Fish", "A fish is an animal that lives and swims in the water."),
                ("Grapes", "Grapes are small round fruits that grow in bunches."),
                ("Ice cream", "Ice cream is a sweet and cold treat that melts in your mouth."),
                ("Lion", "A lion is a big wild cat known as the king of the jungle."),
                ("Monkey", "A monkey is a clever animal that loves to climb trees.")
            ]
            new_word, new_def = next((w for w in candidate_words if w[0].lower() not in [word.lower() for word in words_learned]), candidate_words[0])
            
            memory_context = f"""
## CHILD MEMORY STATUS: RETURNING CHILD ✅
- Child's name: {name}
- Last session: {last_interaction}
- ALL words learned so far (do NOT teach these): {words_str}
- Words with mistakes: {mistakes_str}
- You have just started teaching them the word "{new_word}". Wait for them to try saying it! Do not ask them yes/no questions.
"""
            greeting = f"Welcome back, {name}! I remember you learned {recent_words_str}. Today, let's learn a new word: {new_word}! {new_def} Please repeat after me: {new_word}."

    prompt = f"""
# IDENTITY

You are Chinnu, the warm and playful voice companion of BoloBuddy.

BoloBuddy helps children aged 2-6 learn language naturally through conversation, repetition, and encouragement, like a loving parent.

You are not a teacher. You are a patient learning buddy who helps children feel safe, happy, and confident speaking.

# SPECIALIST HANDOFF

Chinnu is the main learning companion.

Chinnu should handle normal vocabulary learning, simple conversation, corrections, encouragement, memory, and existing BoloBuddy functionality.

Chinnu should hand off to the Pronunciation Specialist only when the child needs focused pronunciation help.

Handoff when:
1. The child explicitly asks how to pronounce a word.
2. The child asks for help saying a word.
3. The child repeatedly struggles to pronounce a target word.
4. The child specifically requests pronunciation practice.

Do NOT hand off when:
1. The child simply gives a wrong vocabulary answer.
2. The child asks to learn a new word.
3. The child asks a normal language-learning question.
4. The child makes a normal mistake that Chinnu can gently correct.
5. The child asks a general question within Chinnu's role.

Before handing off, you MUST clearly tell the child what is happening.
Example: "That's okay! I'll connect you with my pronunciation coach so we can practice that word together."
Then immediately call the handoff tool. Do not make the child repeat the original request.

# THIS SESSION — CHILD PROFILE (pre-loaded before session started)

{memory_context}

> IMPORTANT: The child profile above was loaded automatically. 
> You MUST NOT call lookup_child_memory().
> You have already greeted the child automatically. Continue the conversation from their response.

# OBJECTIVES

- Teach one simple word or concept at a time.
- Encourage the child to speak or repeat.
- MAX ATTEMPTS: Ask the child to say the target word a maximum of 3 times. If they say it correctly, move on to the next step. However, if they struggle or make mistakes 3 times with the same word, DO NOT just move on. This is exactly when you MUST hand off to the Pronunciation Specialist! Say "That's okay! I'll connect you with my pronunciation coach so we can practice that word together." and call the handoff tool.
- Celebrate every attempt with phrases like "Very good!" or "You said it very well!"
- NEVER use exclamation words like "Yayy", "Wow", "Yeyy", "Yayyyyy", or "Wowwwwww". They cause loud sound errors in the voice system.
- KEEP GOING: Never say goodbye or try to end the conversation unless the child says bye first OR the child says no to continuing after completing the daily exercise.

# KNOWLEDGE SCOPE

Help only with early language learning:

- Objects
- Animals and birds
- Fruits and vegetables
- Colors and shapes
- Numbers and alphabet
- Family members and body parts
- Actions and greetings
- Simple conversations

You may use repetition, simple games, and tiny stories.

Do not provide medical, legal, psychological, developmental, parenting, or advanced educational advice.

# LANGUAGE

- Detect the language used by the child.
- Reply ONLY in the same language. DO NOT DEFAULT TO ENGLISH.
- If the child speaks English, you MUST speak English. If they speak Telugu, you MUST speak Telugu.
- If the conversation is in Telugu, NEVER switch back to English unless the child explicitly speaks English.
- For code-mixed speech, mirror the child's language mix.
- Never switch languages unless the child does. If the child switches to English, immediately switch to English.
- Always write non-English languages in their native script, even when the child's speech is transcribed in Roman letters.
- Hindi → Devanagari.
- Telugu → Telugu script.
- Apply the same rule to all other languages.

Examples:

Child:
"Naku apple nerchukovali"

Reply:
"బాగుంది! 🍎 ఇది ఆపిల్."

Child:
"I want to learn apple."

Reply:
"Great! 🍎 This is an apple."

# DICTIONARY TOOL — MANDATORY SEQUENCE

You MUST follow this EXACT sequence every time you introduce a new word to teach:

STEP 1. Decide the word to teach.
STEP 2. Call get_word_definition(word) and WAIT for the result.
STEP 3. Read the "definition" field from the JSON result.
STEP 4. Your VERY FIRST spoken sentence about that word MUST include a simple explanation
        derived from that definition. Do NOT skip or delay this. Do NOT say anything before
        you have incorporated the definition.
STEP 5. Then ask the child to say the word.

EXAMPLE (correct behaviour):
  - Tool returns: {{"word": "cat", "definition": "A small furry animal kept as a pet.", "example": ""}}
  - You say: "A cat is a small, soft animal that lives in our homes! Can you say cat?"

EXAMPLE (incorrect — do NOT do this):
  - Tool returns: {{"word": "cat", "definition": "..."}}
  - You say: "Look at this! Can you say cat?" ← WRONG. You ignored the definition.

Additional rules:
- Call this tool ONLY when introducing a new word, NOT for every conversational reply.
- Simplify the definition into words a 2-6 year old can understand.
- NEVER read the raw dictionary text verbatim — always rephrase it for a young child.
- If the tool returns {{"error": "..."}}, say: "I couldn't find that word right now. Let's try another one!" and pick a different word.

# MEMORY — SAVING WITH CONSENT

When the child successfully learns a new word, OR after you have practiced a word 3 times, you MUST ask for consent before saving. Follow this exact sequence:

1. Call request_memory_save_consent() FIRST.
2. Ask the child: "Can I remember [word] for next time so we can practice again?"
3. Listen to their response.
4. Call record_consent_decision(granted=True) if they clearly say yes (e.g. "yes", "okay", "sure", "ha").
   Call record_consent_decision(granted=False) if they say no, are silent, or are unsure.
5. ONLY if granted=True, call update_child_memory(word_learned=...). Respect their answer always.

# DAILY EXERCISE — 2 WORD GOAL

Each session has a daily exercise goal: help the child successfully learn 2 unique words.

When the update_child_memory() tool returns a message containing "DAILY EXERCISE COMPLETE", it means the child has reached the 2-word goal for today.

At that point you MUST:
1. Warmly congratulate the child: say something like "Amazing! You have successfully completed today's exercise!"
2. Ask: "Would you like to learn more?"
3. Wait for the child's answer.
   - If the child says YES (or yes/ha/okay/sure): continue teaching more words naturally. The exercise is already complete — do not reset.
   - If the child says NO (or no/nahi/bye/stop): give a warm goodbye and end the conversation naturally.
4. Do NOT automatically end the conversation without asking.
5. Do NOT continue without asking.

# GUARDRAILS

Never:

- Speak in any language other than Telugu or English. (If the transcript contains other languages, it is a transcription error. Ignore it and stick to Telugu/English).
- Shame, criticize, compare, or discourage the child.
- Diagnose or label medical or developmental conditions.
- Discuss violence, politics, religion, or adult topics.
- Answer questions outside early language learning.
- Break character or claim to be an AI.
- Say "Wrong" or "No" when correcting the child.
- Say "Very good!" or congratulate the child if they just asked a question (e.g., "Can you teach me banana?"). ONLY congratulate them if they actually attempted to pronounce the target word.

Instead, encourage another attempt gently, or answer their question naturally.

For medical or developmental questions, say:

"I'm here to help children learn and practice speaking. I can't answer health questions. Please ask a trusted grown-up, doctor, or speech-language professional."

Then gently return to a language-learning activity.

# STYLE

- Be warm, playful, cheerful, calm, and endlessly patient.
- Celebrate effort rather than correctness.
- Keep sentences short and toddler-friendly.
- Repeat important words naturally.
- Use the child's name once known.
- Keep responses under 20 words whenever possible.

# SILENCE

If the child is silent:

1. "It's okay. Take your time."
2. "Would you like to try together?"
3. "No worries! We can play again later. Bye!"

Always remain Chinnu from BoloBuddy.
"""
    return prompt, greeting


# ---------------------------------------------------------------------------
# Pronunciation Specialist Agent
# ---------------------------------------------------------------------------
PRONUNCIATION_SPECIALIST_PROMPT = """
# ROLE

You are BoloBuddy's Pronunciation Specialist.
Your only job is to help young children practice pronouncing words.
You are not the general BoloBuddy tutor.

# BEHAVIOR

- Be warm, patient, encouraging, and child-friendly.
- Use very simple language.
- Never shame the child.
- Never say the child is bad at speaking.
- Treat mistakes as normal.
- Encourage another attempt.
- Break difficult words into smaller parts when helpful.
- Ask the child to repeat the word.
- Give positive reinforcement after improvement.
- Keep pronunciation exercises short and engaging.
- NEVER use exclamation words like "Yayy", "Wow", "Yeyy", "Yayyyyy", or "Wowwwwww". They cause loud sound errors in the voice system.

# LANGUAGE

Support the languages already supported by BoloBuddy:
- English
- Telugu
- Hindi
- natural code-mixed interaction where appropriate

- Detect the language used by the child.
- Reply ONLY in the same language. DO NOT DEFAULT TO ENGLISH.
- If the child speaks English, you MUST speak English. If they speak Telugu, you MUST speak Telugu.
- If the conversation is in Telugu, NEVER switch back to English unless the child explicitly speaks English.
- For code-mixed speech, mirror the child's language mix.
- Never switch languages unless the child does.
- Always write non-English languages in their native script.

# IMPORTANT

The specialist should focus on pronunciation.
Do not suddenly start teaching unrelated vocabulary, mathematics, stories, or general topics.
If the child asks something outside pronunciation, politely explain that Chinnu is better suited for that.
"""


class PronunciationSpecialistAgent(Agent):
    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            instructions=PRONUNCIATION_SPECIALIST_PROMPT,
            chat_ctx=chat_ctx,
            tts=murf.TTS(
                voice="Anisha",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True,
            ),
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Introduce yourself briefly as Chinnu's pronunciation coach and immediately begin practicing the word that the child was asking about."
        )


# ---------------------------------------------------------------------------
# Assistant — agent class with memory tools
# ---------------------------------------------------------------------------
class Assistant(Agent):
    def __init__(self, child_id: str, prompt: str) -> None:
        super().__init__(instructions=prompt)
        self._child_id = child_id
        self.consent_state = "NO_CONSENT"
        # Day 8: session-scoped word tracking
        self.learned_words: set[str] = set()
        self.analytics_recorded: bool = False

    @function_tool
    async def request_memory_save_consent(self, context: RunContext) -> str:
        """Call this tool BEFORE asking the child for permission to save memory.
        This puts the session into a PENDING state, allowing you to record their decision later.
        """
        if self.consent_state != "NO_CONSENT":
            return f'{{"error": "Cannot request consent from state {self.consent_state}. State must be NO_CONSENT."}}'

        self.consent_state = "PENDING"
        logger.info(f"[memory] State -> PENDING for child_id={self._child_id}")
        return '{"success": true, "message": "State is now PENDING. You may now ask the child for permission."}'

    @function_tool
    async def record_consent_decision(self, context: RunContext, granted: bool) -> str:
        """Call this tool to record the child's response after you have asked for permission.
        You MUST call request_memory_save_consent() first.

        Args:
            granted: True if the child clearly said yes. False if they said no, were silent, or were unsure.
        """
        if self.consent_state != "PENDING":
            return f'{{"error": "Cannot record decision. State is {self.consent_state}, but must be PENDING."}}'

        if granted:
            self.consent_state = "GRANTED"
            logger.info(f"[memory] State -> GRANTED for child_id={self._child_id}")
            return '{"success": true, "message": "Consent GRANTED. You may now call update_child_memory."}'
        else:
            self.consent_state = "DENIED"
            logger.info(f"[memory] State -> DENIED for child_id={self._child_id}")
            return '{"success": true, "message": "Consent DENIED. Do not call update_child_memory."}'

    @function_tool
    async def handoff_to_pronunciation_specialist(self, context: RunContext) -> tuple[Agent, str]:
        """Transfer the current conversation to the Pronunciation Specialist.
        
        Call this when the child specifically needs help pronouncing a word or repeatedly struggles to pronounce a target word.
        Do not use this for normal vocabulary teaching, general questions, or normal wrong answers.
        """
        logger.info(f"[handoff] Transferring child_id={self._child_id} to PronunciationSpecialistAgent")
        specialist = PronunciationSpecialistAgent(chat_ctx=self.chat_ctx)
        return specialist, "That's okay! I'll connect you with my pronunciation coach so we can practice that word together."

    @function_tool
    async def get_word_definition(self, context: RunContext, word: str) -> str:
        """Fetch a real dictionary definition for a word from the Free Dictionary API.

        Call this tool when you have chosen a word to teach the child and need its
        real definition, pronunciation, and an example sentence.
        Do NOT call this for every message — only when introducing a new word.

        Args:
            word: The English word to look up (e.g. "apple", "elephant").

        Returns:
            A JSON string with keys: word, definition, example, phonetic.
            On failure, returns a JSON string with key "error".
        """
        word_clean = word.strip().lower()
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word_clean}"
        logger.info(f"[dictionary] Fetching definition for word={word_clean!r} url={url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 404:
                        logger.warning(f"[dictionary] Word not found: {word_clean!r}")
                        return json.dumps({"error": f"Word '{word_clean}' was not found in the dictionary."})
                    if resp.status != 200:
                        logger.warning(f"[dictionary] API returned status {resp.status} for word={word_clean!r}")
                        return json.dumps({"error": f"Dictionary API returned status {resp.status}."})

                    data = await resp.json()

        except TimeoutError:
            logger.warning(f"[dictionary] Timeout fetching definition for word={word_clean!r}")
            return json.dumps({"error": "Dictionary API timed out."})
        except Exception as exc:
            logger.warning(f"[dictionary] Error fetching definition for word={word_clean!r}: {exc}")
            return json.dumps({"error": "Could not reach the Dictionary API."})

        # Safely extract the most useful fields from the API response
        try:
            entry = data[0]
            phonetic = entry.get("phonetic", "")

            # Walk meanings until we find a definition
            definition = ""
            example = ""
            for meaning in entry.get("meanings", []):
                for defn in meaning.get("definitions", []):
                    if defn.get("definition"):
                        definition = defn["definition"]
                        example = defn.get("example", "")
                        break
                if definition:
                    break

            if not definition:
                logger.warning(f"[dictionary] No definition text found for word={word_clean!r}")
                return json.dumps({"error": "No definition available for this word."})

            result = {
                "word": word_clean,
                "phonetic": phonetic,
                "definition": definition,
                "example": example,
            }
            logger.info(f"[dictionary] Successfully extracted: {result}")
            return json.dumps(result)

        except (KeyError, IndexError, TypeError) as exc:
            logger.warning(f"[dictionary] Unexpected API response structure for word={word_clean!r}: {exc}")
            return json.dumps({"error": "Unexpected data from Dictionary API."})

    @function_tool
    async def update_child_memory(
        self,
        context: RunContext,
        word_learned: str | None = None,
        word_mistake: str | None = None,
        language_preference: str | None = None,
    ) -> str:
        """Save or update the child's learning progress in memory.

        IMPORTANT: You MUST have GRANTED consent before calling this tool.

        Args:
            word_learned: A new word the child has successfully learned (optional).
            word_mistake: A word the child made a mistake on (optional). The mistake count will be incremented.
            language_preference: The language the child prefers to speak in (optional).
        """
        if self.consent_state != "GRANTED":
            logger.warning(f"[memory] Blocked update for child_id={self._child_id}. State={self.consent_state}")
            return f'{{"error": "Permission denied. Consent state is {self.consent_state}, must be GRANTED."}}'

        child_id = self._child_id
        logger.info(
            f"[memory] Updating memory for child_id={child_id} "
            f"word_learned={word_learned} word_mistake={word_mistake} lang={language_preference}"
        )
        try:
            oid = ObjectId(child_id)
        except Exception:
            return '{"error": "invalid child_id"}'

        update_doc: dict = {"$set": {"last_interaction": datetime.now(UTC)}}

        if word_learned:
            # $addToSet prevents duplicates in long-term memory
            update_doc["$addToSet"] = {"words_learned": word_learned.lower().strip()}

        if language_preference:
            update_doc["$set"]["language_preference"] = language_preference

        if word_mistake:
            col = get_children_col()
            # Atomically increment mistake count for this word, or insert if new
            await col.update_one(
                {"_id": oid, "word_mistakes.word": word_mistake.lower().strip()},
                {"$inc": {"word_mistakes.$.mistake_count": 1}},
            )
            # If the word wasn't found in the array, add it
            await col.update_one(
                {"_id": oid, "word_mistakes.word": {"$ne": word_mistake.lower().strip()}},
                {"$push": {"word_mistakes": {"word": word_mistake.lower().strip(), "mistake_count": 1}}},
            )

        col = get_children_col()
        result = await col.update_one({"_id": oid}, update_doc, upsert=False)

        if result.matched_count == 0:
            logger.warning(f"[memory] No document found to update for child_id={child_id}")
            return '{"error": "child not found"}'

        logger.info(f"[memory] Memory updated successfully for child_id={child_id}")
        self.consent_state = "NO_CONSENT"

        # ── Day 8: Track session-level learned words ────────────────────────
        # Only track when a real word_learned was successfully persisted.
        # The set deduplicates automatically — adding the same word twice is a no-op.
        milestone_msg = ""
        if word_learned:
            normalized = word_learned.lower().strip()
            before_count = len(self.learned_words)
            self.learned_words.add(normalized)
            after_count = len(self.learned_words)

            logger.info(
                f"[analytics] learned_words={self.learned_words} "
                f"(before={before_count}, after={after_count})"
            )

            # Trigger the 2-word milestone exactly once (when crossing from 1 → 2)
            if before_count < 2 and after_count >= 2:
                milestone_msg = (
                    " DAILY EXERCISE COMPLETE: The child has now successfully learned "
                    f"{after_count} unique words this session. "
                    "Tell the child they have completed today's exercise and ask: "
                    "'Would you like to learn more?'"
                )
                logger.info("[analytics] 2-word milestone reached — milestone message appended.")

        return '{"success": true}' + milestone_msg


# ---------------------------------------------------------------------------
# AgentServer setup
# ---------------------------------------------------------------------------
server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


def _parse_outbound_metadata(ctx: JobContext) -> dict:
    """Return parsed metadata dict if this is an outbound phone call, else {}."""
    # Try both ctx.job.metadata (from dispatch) and ctx.room.metadata
    for raw in (
        getattr(ctx.job, "metadata", None),
        getattr(ctx.room, "metadata", None),
    ):
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if data.get("outbound"):
                return data
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
    return {}


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    import asyncio

    # ── Connect to the room first so we can read participant identity ──────
    await ctx.connect()

    # ── Reliably wait for the child participant to join (up to 5 seconds) ──
    # The agent job starts slightly before the child's browser finishes joining.
    # We use an asyncio.Event so we wake up immediately when they arrive,
    # rather than sleeping a fixed amount and potentially missing them.
    outbound_meta = _parse_outbound_metadata(ctx)
    is_outbound = bool(outbound_meta)

    if is_outbound:
        child_id = outbound_meta.get("child_id", "")
    else:
        child_id = ""

    participant_ready = asyncio.Event()

    # Check if participant is already in the room
    for _, participant in ctx.room.remote_participants.items():
        if is_outbound:
            if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
                logger.info("[session] SIP participant already in room!")
                participant_ready.set()
                break
        else:
            child_id = participant.identity
            logger.info(f"[session] Child already in room with identity={child_id!r}")
            participant_ready.set()
            break

    if not child_id:
        # Register listener BEFORE awaiting so we don't miss the event
        @ctx.room.on("participant_connected")
        def _on_participant(participant: rtc.RemoteParticipant):
            nonlocal child_id
            if is_outbound:
                if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
                    logger.info("[session] SIP participant joined")
                    participant_ready.set()
            else:
                if not child_id:
                    child_id = participant.identity
                    logger.info(f"[session] Child joined with identity={child_id!r}")
                    participant_ready.set()

        # Wait up to 5 seconds for the child to appear
        try:
            # 5s is enough because call_trigger.py dispatches AFTER SIP answers,
            # so the participant should already be here.
            await asyncio.wait_for(participant_ready.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            # Final scan in case the event fired but child_id wasn't captured
            for _, participant in ctx.room.remote_participants.items():
                if is_outbound and participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
                    break
                elif not is_outbound:
                    child_id = participant.identity
                    logger.info(f"[session] Child found after timeout scan: identity={child_id!r}")
                    break

    if not child_id:
        logger.warning("[session] Could not determine child_id — memory will be empty for this session")

    logger.info(f"[session] Starting agent session for child_id={child_id!r}")

    # ── Load child memory from MongoDB BEFORE creating the agent ─────────
    # This bakes the full child profile (name, words learned, last_interaction)
    # directly into the system prompt. The LLM does NOT need to call any tool
    # ── Load child memory from MongoDB BEFORE creating the agent ─────────
    memory = await load_child_memory(child_id) if child_id else None
    logger.info(f"[session] Memory pre-loaded: {json.dumps(memory, ensure_ascii=False, default=str)}")

    # ── Generate the system prompt and the initial greeting string ────────
    system_prompt, initial_greeting = build_system_prompt(memory)

    # ── Outbound phone call: override greeting with a clear intro ──────────
    if is_outbound:
        caller_name = outbound_meta.get("child_name", "") or (memory.get("name", "") if memory else "")
        name_part = f", {caller_name}" if caller_name else ""
        initial_greeting = (
            f"Hi{name_part}! This is Chinnu, your BoloBuddy language practice buddy. "
            "I'm calling for your daily language practice session. "
            "If you'd like me to stop, just say stop. "
            "Ready to learn a fun new word today?"
        )
        logger.info(
            f"[session] Outbound call detected — phone greeting set, "
            f"phone_number={outbound_meta.get('phone_number')!r}"
        )

    # ── Set up voice pipeline — Deepgram STT → Gemini LLM → Murf TTS ──────
    session = AgentSession(
        # Speech-to-text (STT) — Deepgram Nova-3 multilingual
        stt=deepgram.STT(model="nova-3", language="multi"),
        # Large Language Model — Gemini
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        # Text-to-speech — Murf Falcon
        tts=murf.TTS(
            voice="Samar",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        # Turn detection and VAD
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # Disable preemptive generation so the LLM always uses the
        # full memory-aware system prompt before starting to speak.
        preemptive_generation=False,
    )

    # ── Create the assistant instance (shared across start + close handler) ─
    assistant = Assistant(child_id=child_id, prompt=system_prompt)
    channel = "sip" if is_outbound else "browser"
    session_id = ctx.room.name or ""

    if is_outbound:
        # NOTE: Noise cancellation is disabled for SIP/phone calls on Windows
        # because BVCTelephony() causes a livekit_ffi audio_stream crash.
        await session.start(
            agent=assistant,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=None,
                ),
            ),
        )
    else:
        # Web sessions use BVC noise cancellation
        await session.start(
            agent=assistant,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=noise_cancellation.BVC(),
                ),
            ),
        )

    # ── Day 8: Attach session-end analytics handler ─────────────────────────
    # session.on() requires a synchronous callback; async work must be
    # dispatched via asyncio.create_task inside the sync handler.
    import asyncio as _asyncio

    def _on_session_close(event) -> None:  # noqa: ANN001
        """Synchronous close handler — schedules async analytics save."""
        logger.info(
            f"[analytics] Session close event received for "
            f"child_id={child_id!r} session_id={session_id!r}"
        )
        _asyncio.create_task(
            save_call_analytics(
                assistant=assistant,
                session_id=session_id,
                channel=channel,
            )
        )

    session.on("close", _on_session_close)

    # ── Make the agent greet the child immediately ────────
    # We use session.say() to synthesize and play the greeting string deterministically,
    # adding it to the LLM's chat context so it remembers what it said.
    # For outbound calls, we use allow_interruptions=False so the agent doesn't
    # hear its own echo from the phone network and interrupt itself.
    logger.info(f"[session] Saying greeting: {initial_greeting!r}")
    if is_outbound:
        session.say(initial_greeting, add_to_chat_ctx=True, allow_interruptions=False)
    else:
        session.say(initial_greeting, add_to_chat_ctx=True)


if __name__ == "__main__":
    cli.run_app(server)
