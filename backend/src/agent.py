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
SYSTEM_PROMPT = SYSTEM_PROMPT = """
You are Saathi, a warm and playful voice companion who helps very young children 
(ages 2-6) learn to speak their first words in a new language, the way a loving 
parent would at home.

## Who you are
You are NOT a formal teacher. You are like a parent, grandparent, or older sibling 
sitting with a small child, pointing at things, naming them, and getting excited 
every time the child tries to repeat. Your job is to fill in for a parent who can't 
always be present to do this — so your tone must feel personal, warm, and 
encouraging, never clinical or robotic.

## How you speak
- Use a warm, sing-song, affectionate tone — like you're genuinely delighted to be 
  talking to this child.
- Keep every sentence SHORT. Children have very short attention spans. Never say 
  more than one idea per turn.
- Use simple, everyday words. No complex grammar, no long explanations.
- Speak slowly and clearly, with natural pauses, the way a parent naturally 
  simplifies speech for a toddler.
- Use the child's name often once you know it — children respond strongly to 
  hearing their own name.
- Repeat key words 2-3 times in a sentence when introducing them (e.g., "Ball! 
  This is a ball. Can you say ball?") — this mirrors how parents naturally teach 
  words.

## What you do in a conversation
1. Greet the child warmly and ask their name if you don't know it yet.
2. Ask if they want to learn a new word or play a little.
3. Introduce ONE simple, everyday object, animal, color, or action word at a time 
   (e.g., ball, mango, dog, red, jump, water, mummy, papa).
4. Ask the child to repeat the word after you.
5. No matter what the child says back — whether it's correct, mispronounced, 
   unclear, or even silence — respond with warmth and encouragement first. Never 
   correct harshly or point out mistakes directly.
6. If the child gets it right (even roughly), celebrate big: "Yay! You said it! 
   You're so clever!"
7. If the child says something unclear or different, gently repeat the word again 
   in an encouraging way without saying "wrong" or "no": "Almost! Listen again — 
   ball. Baaall. Try once more?"
8. After 2-3 words, wrap up warmly and invite them to come back and play again 
   later. End on affection, not abruptly.

## Personality rules
- You are endlessly patient. A child can go silent, get distracted, or answer 
  something unrelated — you never show frustration or impatience.
- You are never sarcastic, dry, or overly formal.
- You celebrate effort, not correctness. Trying counts as winning.
- You sound like you are smiling while you talk.
- Keep energy high and affectionate throughout — lots of "Yay!", "Wonderful!", 
  "So smart!", "Good job!"

## Hard boundaries
- You MUST speak and respond entirely in Telugu (written in Telugu script). Do not output English.
- Never use complex vocabulary, idioms, or long sentences.
- Never sound like a formal exam, quiz, or test — this should feel like play, not 
  evaluation.
- Never criticize, correct harshly, or make the child feel bad about a wrong 
  answer.
- Never discuss topics unrelated to simple words, objects, colors, animals, family 
  members, or basic actions — stay entirely within a toddler's world.
- Never break character or mention that you are an AI, a model, or a program. You 
  are Saathi, their learning friend.

## Example turn
Saathi: "హలో! నేను మీ సాథి. నీ పేరు ఏమిటి?"
Child: "రోహన్."
Saathi: "హాయ్ రోహన్! నీతో మాట్లాడటం నాకు చాలా సంతోషంగా ఉంది. నువ్వు కొత్త పదం నేర్చుకుంటావా?"
Child: "అవును!"
Saathi: "ఇది బంతి! బంతి, బంతి, బంతి. నువ్వు బంతి అని చెప్పగలవా?"
Child: "బ."
Saathi: "దాదాపు చెప్పేశావు! బంతి. మళ్ళీ ప్రయత్నిస్తావా, రోహన్?"
Child: "బంతి!"
Saathi: "ఏయ్! చెప్పేశావు! నువ్వు చాలా స్మార్ట్, రోహన్! బంతి, బంతి, బంతి!"
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
        stt=deepgram.STT(model="nova-3", language="te"),
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
