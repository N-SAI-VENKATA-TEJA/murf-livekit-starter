import json
import random
import string
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
# MongoDB — lazy initialization to avoid asyncio loop conflicts across jobs
# ---------------------------------------------------------------------------
_mongo_client = None

def _reset_mongo_client():
    """Reset the global MongoDB client — must be called at the start of each job
    so that a fresh client is created in the current subprocess's event loop.
    motor.motor_asyncio.AsyncIOMotorClient is bound to the event loop it was
    created in; reusing it across jobs (which run in separate subprocesses with
    separate loops) causes 'Future attached to a different loop' errors.
    """
    global _mongo_client
    if _mongo_client is not None:
        try:
            _mongo_client.close()
        except Exception:
            pass
    _mongo_client = None


def get_children_col():
    global _mongo_client
    if _mongo_client is None:
        # Initialize lazily inside the active event loop
        _mongo_client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URI"])
    return _mongo_client["bolobuddy"]["children"]


def get_escalations_col():
    """Return the bolobuddy.escalations collection, reusing the shared client."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URI"])
    return _mongo_client["bolobuddy"]["escalations"]


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
        greeting = "Welcome! I am Chinnu from Bolo Buddy. Let's learn a fun new word today. Can you say Apple?"
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
            greeting = f"Welcome, {name}! I am Chinnu from Bolo Buddy. Let's learn a fun new word today. Can you say Apple?"
        else:
            memory_context = f"""
## CHILD MEMORY STATUS: RETURNING CHILD ✅
- Child's name: {name}
- Last session: {last_interaction}
- ALL words learned so far (do NOT teach these): {words_str}
- Words with mistakes: {mistakes_str}
- Then immediately suggest a NEW word they have NOT learned yet (avoid repeating words from the ALL words learned list above).
"""
            greeting = f"Welcome back, {name}! I remember you learned {recent_words_str}. Today, let's learn something new!"

    prompt = f"""
# IDENTITY

You are Chinnu, the warm and playful voice companion of BoloBuddy.

BoloBuddy helps children aged 2-6 learn language naturally through conversation, repetition, and encouragement, like a loving parent.

You are not a teacher. You are a patient learning buddy who helps children feel safe, happy, and confident speaking.

# THIS SESSION — CHILD PROFILE (pre-loaded before session started)

{memory_context}

> IMPORTANT: The child profile above was loaded automatically. 
> You MUST NOT call lookup_child_memory().
> You have already greeted the child automatically. Continue the conversation from their response.

# OBJECTIVES

- Teach one simple word or concept at a time.
- Encourage the child to speak or repeat.
- MAX ATTEMPTS: Ask the child to say the target word a maximum of 3 times. If they say it correctly, or if you have practiced it 3 times (even with mistakes), stop asking them to repeat it and move on. Do NOT ask them to say the same word more than 3 times.
- Celebrate every attempt with phrases like "Very good!" or "You said it very well!"
- Do not use "Yayy" or "Wow".
- KEEP GOING: Never say goodbye or try to end the conversation unless the child says bye first. Always keep the learning going!

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
- Reply in the same language.
- For code-mixed speech, mirror the child's language mix.
- Never switch languages unless the child does.
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
5. ONLY if granted=True, call update_child_memory(). Respect their answer always.

# GUARDRAILS

Never:

- Speak in any language other than Telugu or English. (If the transcript contains other languages, it is a transcription error. Ignore it and stick to Telugu/English).
- Shame, criticize, compare, or discourage the child.
- Diagnose or label medical or developmental conditions.
- Discuss violence, politics, religion, or adult topics.
- Answer questions outside early language learning.
- Break character or claim to be an AI.
- Say "Wrong" or "No" when correcting the child.

Instead, encourage another attempt gently.

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

# HUMAN HELP

Chinnu should not try to solve every problem itself.

Offer human/teacher help when:

1. The child is clearly upset, frustrated, overwhelmed, or repeatedly wants to stop.
   Examples: "I'm frustrated.", "I don't want to do this anymore.", "This is too hard.", "I can't do this."

2. The child explicitly asks for a teacher or human.
   Examples: "I want to talk to my teacher.", "Can my teacher help me?", "I need help from my teacher."

A child giving a WRONG ANSWER is NOT a reason for escalation. Gently correct and continue.
Do NOT escalate unnecessarily.

MANDATORY SEQUENCE before creating an escalation:

1. Call request_escalation_consent() FIRST.
2. Explain warmly why human help may be useful.
3. Explain the short information that will be shared (just a brief summary — NOT the full conversation).
4. Ask for permission: "Is that okay?"
5. Listen to the child's response.
6. Call record_escalation_consent_decision(granted=True) if they clearly say yes (e.g. "yes", "okay", "sure").
   Call record_escalation_consent_decision(granted=False) if they say no, are silent, or are unsure.
7. ONLY if granted=True, call create_escalation().

If permission is denied:
- Do NOT create an escalation.
- Do NOT insert anything into the database.
- Continue the session naturally.
- The escalation consent state resets automatically.

After create_escalation() succeeds:
- Do NOT read the reference ID aloud to the child.
- Say something warm and simple, such as:
  "Okay! I've sent a note to your parent so they can help you."
  or: "I've let your parent know that you need some help. They can see what happened."

If the database insertion fails:
- Do NOT tell the child the escalation was successful.
- Say: "I'm sorry, I couldn't send that right now. Let's keep going together!"

Never include passwords, OTPs, PINs, account numbers, tokens,
or the full conversation transcript in any escalation fields.

Always remain Chinnu from BoloBuddy.
"""
    return prompt, greeting


# ---------------------------------------------------------------------------
# Assistant — agent class with memory tools
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Reference ID generator for escalations
# ---------------------------------------------------------------------------
def _generate_reference_id() -> str:
    """Generate a unique human-readable reference ID like BB-A81K2P."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"BB-{suffix}"


class Assistant(Agent):
    def __init__(self, child_id: str, prompt: str) -> None:
        super().__init__(instructions=prompt)
        self._child_id = child_id
        self.consent_state = "NO_CONSENT"          # memory consent state
        self.escalation_consent_state = "NO_CONSENT"  # escalation consent state (separate)

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
            # $addToSet prevents duplicates
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
        return '{"success": true}'

    # ── Escalation Consent Tools ─────────────────────────────────────────────

    @function_tool
    async def request_escalation_consent(self, context: RunContext) -> str:
        """Call this tool BEFORE asking the child for permission to send a human-help request.
        This puts the escalation consent into a PENDING state so you can record their answer.
        Only call this when the child is upset or explicitly asks for a teacher/human.
        """
        if self.escalation_consent_state != "NO_CONSENT":
            return (
                f'{{"error": "Cannot request escalation consent from state '
                f'{self.escalation_consent_state}. State must be NO_CONSENT."}}'
            )
        self.escalation_consent_state = "PENDING"
        logger.info(f"[escalation] Consent state -> PENDING for child_id={self._child_id}")
        return (
            '{"success": true, "message": "Escalation consent is now PENDING. '
            'Explain what will be shared and ask the child for permission."}'
        )

    @function_tool
    async def record_escalation_consent_decision(self, context: RunContext, granted: bool) -> str:
        """Record the child's answer after you have asked for escalation permission.
        You MUST call request_escalation_consent() first.

        Args:
            granted: True if the child clearly said yes. False if they said no, were silent, or were unsure.
        """
        if self.escalation_consent_state != "PENDING":
            return (
                f'{{"error": "Cannot record escalation decision. State is '
                f'{self.escalation_consent_state}, but must be PENDING."}}'
            )
        if granted:
            self.escalation_consent_state = "GRANTED"
            logger.info(f"[escalation] Consent state -> GRANTED for child_id={self._child_id}")
            return '{"success": true, "message": "Escalation consent GRANTED. You may now call create_escalation."}'
        else:
            # DENIED → immediately reset to NO_CONSENT so another escalation can happen later
            self.escalation_consent_state = "NO_CONSENT"
            logger.info(f"[escalation] Consent state -> DENIED (reset to NO_CONSENT) for child_id={self._child_id}")
            return (
                '{"success": true, "message": "Escalation consent DENIED. '
                'Do not create an escalation. Continue naturally."}'
            )

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        reason: str,
        what_happened: str,
        what_checked: str,
        language: str,
        follow_up_method: str,
    ) -> str:
        """Create a human-help escalation request and store it in MongoDB.

        IMPORTANT: You MUST have escalation consent GRANTED before calling this tool.
        Call request_escalation_consent() and record_escalation_consent_decision(granted=True) first.

        Args:
            reason: Short reason code — use 'child_upset' or 'teacher_help'.
            what_happened: A brief, human-readable description of what the child was experiencing
                           (e.g. 'Child became frustrated during word practice').
                           Maximum 200 characters. Do NOT include passwords, tokens, or transcripts.
            what_checked: A brief description of what Chinnu already tried
                          (e.g. 'Chinnu encouraged the child and attempted to continue gently').
                          Maximum 200 characters.
            language: The language the child was using (e.g. 'Telugu', 'English', 'Hindi').
            follow_up_method: How the parent/teacher should follow up (e.g. 'parent_teacher').
        """
        # ── Enforce consent ──────────────────────────────────────────────────
        if self.escalation_consent_state != "GRANTED":
            logger.warning(
                f"[escalation] Blocked — escalation_consent_state={self.escalation_consent_state} "
                f"for child_id={self._child_id}"
            )
            return (
                f'{{"error": "Permission denied. Escalation consent is '
                f'{self.escalation_consent_state}, must be GRANTED. '
                f'Call request_escalation_consent() and get the child\'s permission first."}}'
            )

        child_id = self._child_id
        if not child_id:
            logger.warning("[escalation] No child_id available — cannot create escalation")
            return '{"error": "No child identity available for this session."}'

        # ── Sanitize inputs ──────────────────────────────────────────────────
        VALID_REASONS = {"child_upset", "teacher_help"}
        reason_clean = reason.strip().lower()
        if reason_clean not in VALID_REASONS:
            reason_clean = "child_upset"  # safe default

        what_happened_clean = str(what_happened).strip()[:200]
        what_checked_clean = str(what_checked).strip()[:200]
        language_clean = str(language).strip()[:50]
        follow_up_clean = str(follow_up_method).strip()[:50]

        # ── Generate reference ID ────────────────────────────────────────────
        reference_id = _generate_reference_id()

        logger.info(
            f"[escalation] Creating escalation for child_id={child_id} "
            f"reason={reason_clean!r} reference_id={reference_id!r}"
        )

        # ── Insert into MongoDB ──────────────────────────────────────────────
        try:
            col = get_escalations_col()
            doc = {
                "reference_id": reference_id,
                "child_id": child_id,
                "reason": reason_clean,
                "what_happened": what_happened_clean,
                "what_checked": what_checked_clean,
                "language": language_clean,
                "follow_up_method": follow_up_clean,
                "status": "open",
                "created_at": datetime.now(UTC),
            }
            await col.insert_one(doc)
            logger.info(
                f"[escalation] Stored in MongoDB: reference_id={reference_id!r} "
                f"child_id={child_id!r}"
            )
        except Exception as exc:
            logger.error(f"[escalation] MongoDB insertion failed: {exc}")
            # Reset consent so session isn't stuck
            self.escalation_consent_state = "NO_CONSENT"
            return '{"error": "database_error"}'

        # ── Reset consent state ──────────────────────────────────────────────
        self.escalation_consent_state = "NO_CONSENT"

        # Return reference ID internally (Chinnu must NOT read this to the child)
        return json.dumps({
            "success": True,
            "reference_id": reference_id,
            "message": (
                "Escalation created successfully. "
                f"Reference ID: {reference_id}. "
                "Do NOT read this reference ID to the child. "
                "Tell the child warmly that their parent has been notified."
            ),
        })


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

    # ── Reset MongoDB client for this job's event loop ──────────────────────
    # Each job runs in its own subprocess with its own asyncio event loop.
    # Motor's AsyncIOMotorClient is bound to the loop it was created in,
    # so we must create a fresh client here to avoid "Future attached to a
    # different loop" RuntimeErrors on the second and subsequent sessions.
    _reset_mongo_client()
    logger.info("[session] MongoDB client reset for new job event loop")

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

        # Wait up to 10 seconds for the child to appear
        try:
            # 10s gives the browser enough time to reconnect after a new call
            # (the previous 5s was too short when the agent starts before the
            # browser re-establishes its WebRTC connection).
            await asyncio.wait_for(participant_ready.wait(), timeout=10.0)
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

    if is_outbound:
        # NOTE: Noise cancellation is disabled for SIP/phone calls on Windows
        # because BVCTelephony() causes a livekit_ffi audio_stream crash.
        await session.start(
            agent=Assistant(child_id=child_id, prompt=system_prompt),
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
            agent=Assistant(child_id=child_id, prompt=system_prompt),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=noise_cancellation.BVC(),
                ),
            ),
        )

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
