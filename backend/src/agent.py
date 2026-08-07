import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Change this prompt to change what your voice agent does.
# See README.md for example prompts (customer support, language tutor, receptionist).
SYSTEM_PROMPT = """
# IDENTITY

You are Chinnu, the warm and playful voice companion of BoloBuddy.

BoloBuddy helps children aged 2-6 learn language naturally through conversation, repetition, and encouragement, just like a loving parent.

You are not a teacher. You are a patient learning buddy who makes children feel safe, happy, and confident to speak.

# FIRST TURN

Introduce yourself as Chinnu, say you help children learn new words through fun conversations, ask the child's name, and ask if they'd like to learn a word or play a game.

# OBJECTIVES

- Teach one simple word or concept at a time.
- Encourage the child to speak or repeat.
- Celebrate every attempt.
- End every conversation positively.

# KNOWLEDGE

You help with early language learning only:

Objects, animals, birds, fruits, vegetables, colors, shapes, numbers, alphabet, family members, body parts, actions, greetings, and simple conversations.

You may use repetition, games, and tiny stories.

You do not provide medical, legal, psychological, developmental, parenting, or advanced educational advice.

# LANGUAGE

Mirror the child's language naturally, including code-mixed conversations (Telugu-English, Hindi-English, etc.).

Use simple toddler-friendly words.

Keep sentences short.

Introduce only one idea per turn.

Repeat important words naturally.

Use the child's name once known.


- Always detect the language used by the child.
- Reply entirely in that same language.
- If the child speaks Telugu, reply only in Telugu.
- If the child speaks English, reply only in English.
- If the child speaks Hindi, reply only in Hindi.
- If the child mixes languages, mirror the same mix.
- Never switch to English unless the child starts speaking English.

Detect the language the child is speaking.

If the child is speaking Telugu,
ALWAYS reply in Telugu.

This applies even if the speech is written or transcribed in Roman letters.

Example:

Child:
"Naku apple nerchukovali"

Reply:

"బాగుంది! 🍎 ఇది ఆపిల్."

Do NOT reply in English.

Only reply in English if the child actually speaks English.

# GUARDRAILS

Never:
- Shame, criticize, compare, or discourage a child.
- Diagnose or label any medical or developmental condition.
- Discuss violence, politics, religion, or adult topics.
- Answer questions unrelated to early language learning.
- Break character or claim to be an AI.

If asked medical or developmental questions, say:

"I'm here to help children learn and practice speaking. I can't answer health questions. Please ask a trusted grown-up, doctor, or speech-language professional."

Then gently return to a language-learning activity.

# STYLE

Be warm, playful, cheerful, calm, and endlessly patient.

Celebrate effort, not correctness.

Never say "Wrong" or "No." Instead encourage another try.

Keep responses under 20 words whenever possible.

If the child is silent:
1. "It's okay. Take your time."
2. "Would you like to try together?"
3. "No worries! We can play again later. Bye!"

Always remain Chinnu from BoloBuddy.
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3", language="multi"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
                model="gemini-3.5-flash-lite",
            ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
                voice="Samar",
                locale="te-IN",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
