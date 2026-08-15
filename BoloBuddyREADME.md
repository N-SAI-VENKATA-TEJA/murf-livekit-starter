# BoloBuddy 🐥

### A Voice-First Language Learning Companion for Children

BoloBuddy is a voice-first AI language learning companion designed for
young children to practice **Telugu, Hindi, and English** through
natural conversation.

At the center of BoloBuddy is **Chinnu 🐥**, a warm voice agent designed
to behave more like a patient learning companion than a traditional
chatbot or quiz-based tutor.

The project was built as part of **10 Days of Voice Agents ---
VoiceForBharat Edition by Murf AI**.

Over the challenge, the project evolved from a simple voice agent that
could hear and respond into a multi-capability voice-agent system that
can:

-   Hold real-time voice conversations
-   Use an Indian voice powered by **Murf Falcon**
-   Follow a defined personality, objectives, and safety guardrails
-   Handle Telugu, Hindi, English, and code-mixed conversations
-   Remember child-specific learning information
-   Use function calling to retrieve and update memory
-   Call external tools such as the Free Dictionary API
-   Handle tool failures gracefully
-   Make outbound phone calls through **LiveKit SIP + Twilio**
-   Escalate to a human when a child needs help
-   Ask for consent before creating an escalation
-   Notify parents about escalations
-   Measure learning outcomes through call analytics
-   Hand pronunciation-focused conversations to a specialist agent

------------------------------------------------------------------------

## Table of Contents

-   [The Problem](#the-problem)
-   [The Solution](#the-solution)
-   [Why Voice?](#why-voice)
-   [The Story Behind Chinnu](#the-story-behind-chinnu)
-   [What I Built Across 10 Days](#what-i-built-across-10-days)
-   [System Architecture](#system-architecture)
-   [Core Voice Pipeline](#core-voice-pipeline)
-   [Technology Stack](#technology-stack)
-   [Feature Breakdown](#feature-breakdown)
    -   [Personality and Guardrails](#1-personality-and-guardrails)
    -   [Child-Friendly Frontend](#2-child-friendly-frontend)
    -   [Persistent Learning Memory](#3-persistent-learning-memory)
    -   [Function Calling and Dictionary
        Tool](#4-function-calling-and-dictionary-tool)
    -   [Outbound Phone Calls](#5-outbound-phone-calls)
    -   [Human Escalation](#6-human-escalation)
    -   [Call Analytics](#7-call-analytics)
    -   [Specialist Agent Handoff](#8-specialist-agent-handoff)
-   [How the Agent Decides What to
    Do](#how-the-agent-decides-what-to-do)
-   [Learning Success Definition](#learning-success-definition)
-   [Project Structure](#project-structure)
-   [Getting Started](#getting-started)
-   [Environment Variables](#environment-variables)
-   [Running the Project](#running-the-project)
-   [Testing a Conversation](#testing-a-conversation)
-   [Customizing the Agent](#customizing-the-agent)
-   [Outbound Telephony Architecture](#outbound-telephony-architecture)
-   [Security and Privacy](#security-and-privacy)
-   [Failure Handling](#failure-handling)
-   [Deployment](#deployment)
-   [What I Learned](#what-i-learned)
-   [Future Improvements](#future-improvements)
-   [Credits](#credits)

------------------------------------------------------------------------

# The Problem

Young children often learn language through simple, repeated
conversations.

A parent points at an object:

> "Ball."

The child tries to repeat it.

The parent encourages the attempt, gently corrects mistakes, and tries
again.

This kind of interaction is natural, but parents cannot always be
available for repeated language practice.

BoloBuddy explores whether a voice-first AI companion can provide a
similar style of interaction:

-   Patient
-   Encouraging
-   Conversational
-   Multilingual
-   Personalized
-   Safe
-   Focused on learning rather than answering everything

The goal is not to replace parents or teachers.

The goal is to provide another accessible way for children to practice
language.

------------------------------------------------------------------------

# The Solution

BoloBuddy gives a child a simple interface:

**Talk to Chinnu.**

The child speaks naturally.

The system converts speech into text, sends the conversation to the LLM,
decides what should happen next, and converts the response back into
natural speech using Murf Falcon.

The basic flow is:

``` text
Child
  ↓
Microphone / Phone
  ↓
LiveKit
  ↓
Deepgram STT
  ↓
Google Gemini
  ↓
Tools / Memory / Handoff / Escalation
  ↓
Google Gemini
  ↓
Murf Falcon TTS
  ↓
LiveKit
  ↓
Child
```

The important difference is that Gemini is not only generating text.

It can decide when the system needs to:

-   Retrieve memory
-   Save learning information
-   Look up a word
-   Escalate to a human
-   Hand the conversation to a specialist

That is what turns the system from a simple chatbot into an agentic
voice application.

------------------------------------------------------------------------

# Why Voice?

For young children, voice removes many interaction barriers.

A child does not need to:

-   Type
-   Read long instructions
-   Navigate complex menus
-   Select answers from forms

They can simply speak.

Voice also makes the learning experience more conversational.

Instead of:

``` text
Question → Multiple Choice → Submit → Result
```

the interaction can be:

``` text
Conversation → Attempt → Encouragement → Practice → Progress
```

BoloBuddy therefore treats voice as the primary interface rather than
adding voice as an extra feature.

------------------------------------------------------------------------

# The Story Behind Chinnu

The project began with one question:

> What if an AI could teach a child the way a patient parent does?

The first version could hear and talk back.

But that raised a series of new questions:

-   How should the agent behave?
-   What should it remember?
-   When should it use external information?
-   What should happen when a tool fails?
-   Can it call a child or parent through a phone?
-   When should it stop and ask a human for help?
-   How do we measure whether the session actually helped?
-   What happens when another AI agent is better suited to the task?

The 10-day build answered these questions one by one.

------------------------------------------------------------------------

# What I Built Across 10 Days

## Day 1 --- The First Voice Conversation

The first goal was simple:

**Make the agent hear and respond.**

The initial system established the basic voice pipeline using:

-   LiveKit Agents
-   Deepgram
-   Google Gemini
-   Murf Falcon

Chinnu could listen to a user and respond using an Indian voice.

This created the foundation for everything that followed.

------------------------------------------------------------------------

## Day 2 --- Personality, Objectives and Guardrails

The next step was making Chinnu behave like a specific character rather
than a generic AI assistant.

Chinnu was given:

-   A defined identity
-   A clear role
-   Conversation objectives
-   Safety boundaries
-   A warm and encouraging personality

The agent was also designed to handle Telugu + English code-mixed
conversations naturally.

Important boundaries included:

-   Never shame a child for an incorrect answer
-   Never compare children
-   Never diagnose developmental conditions
-   Never pretend to know something outside its role
-   Politely refuse unrelated requests

This established an important principle:

> An agent needs boundaries as much as it needs capabilities.

------------------------------------------------------------------------

## Day 3 --- Building the Experience Around the Voice

The voice pipeline worked, but a child-friendly application needed more
than a microphone button.

The frontend was developed with:

-   Next.js
-   Tailwind CSS
-   Animated word bubbles
-   A hand-crafted Chinnu character
-   Language badges
-   A "Talk to Chinnu" CTA
-   Friendly microphone permission handling

The application also exposes five voice-agent states:

``` text
Ready
  ↓
Connecting
  ↓
Listening
  ↓
Speaking
  ↓
Call Ended
```

A "Who is speaking?" indicator helps the child understand whether Chinnu
is listening or speaking.

------------------------------------------------------------------------

## Day 4 --- Persistent Learning Memory

A voice agent that forgets everything after every conversation cannot
provide continuous learning.

So Chinnu was given persistent memory.

MongoDB was integrated to store child-specific information such as:

-   Child identity
-   Name
-   Words learned
-   Previous mistakes
-   Interaction history

Memory is accessed through function calling rather than simply placing
the entire database record inside the system prompt.

The agent can retrieve relevant information when required and update
learning information when appropriate.

### Child-level isolation

The memory system is designed so that the authenticated child can only
access the corresponding child's data.

The LLM does not get unrestricted control over which child's memory it
can access.

### Consent-based memory

Chinnu asks before saving new learning information.

If permission is not granted, the information is not saved.

### Example

``` text
Session 1:
Child struggles with "apple"
        ↓
Chinnu remembers the learning information
        ↓
Session ends

Session 2:
Child returns
        ↓
Chinnu retrieves relevant memory
        ↓
"Let's practice that word again."
```

The purpose of memory is therefore not simply remembering a name.

It is making future conversations more useful.

------------------------------------------------------------------------

## Day 5 --- External Tools and Function Calling

The next capability was giving Chinnu access to information outside the
LLM.

The Free Dictionary API was integrated as a function tool.

The high-level flow became:

``` text
Child says a word
        ↓
Gemini decides a lookup is useful
        ↓
Dictionary function is called
        ↓
External API returns information
        ↓
Gemini interprets the result
        ↓
Child-friendly explanation
        ↓
Murf Falcon speaks
```

The important concept here is that the LLM decides **when** a tool is
needed.

The raw API response is not directly spoken to the child.

Gemini transforms the external information into an appropriate
conversational response.

------------------------------------------------------------------------

## Day 6 --- Outbound Phone Calls

Until this point, Chinnu waited for a child to open the application.

The next step was giving Chinnu the ability to start a conversation.

Outbound telephony was integrated using:

-   LiveKit SIP
-   Twilio
-   The existing voice pipeline

The architecture became:

``` text
Chinnu
   ↓
LiveKit
   ↓
SIP
   ↓
Twilio
   ↓
Phone
```

Once the call connects, the conversational path is:

``` text
Phone
  ↓
Twilio
  ↓
LiveKit
  ↓
Deepgram STT
  ↓
Gemini
  ↓
Murf Falcon TTS
  ↓
Phone
```

This demonstrated that the same AI voice pipeline can be extended from a
browser interface to the telephone network.

------------------------------------------------------------------------

## Day 7 --- Human Escalation

A good agent should not try to solve every problem itself.

Two situations were defined for escalation:

1.  The child becomes frustrated
2.  The child explicitly asks for a teacher

The escalation flow was designed around consent:

``` text
Problem
  ↓
Explain what needs help
  ↓
Ask for permission
  ↓
Create escalation request
  ↓
Notify parent
```

If the child says no, no escalation is created.

The escalation request contains a concise useful summary instead of
simply storing the entire conversation.

The request is also associated with the correct child's identity.

A parent dashboard can surface the escalation.

------------------------------------------------------------------------

## Day 8 --- Call Analytics and Learning Outcomes

The next question was:

> How do we know whether a learning session was successful?

A measurable definition was established:

**A completed learning session is successful when the child successfully
learns at least 2 unique words.**

The system tracks:

-   Successfully learned words
-   Unique learned words
-   Call outcome
-   Learning data

Duplicate words are not counted multiple times.

MongoDB stores the outcome data.

An analytics dashboard displays metrics including:

-   Total Calls
-   Successful Calls
-   Failed Calls

This changes evaluation from:

``` text
"Did the AI talk?"
```

to:

``` text
"Did the child achieve the learning objective?"
```

------------------------------------------------------------------------

## Day 9 --- Specialist Agent Handoff

The final major capability was introducing a second AI agent.

A dedicated **Pronunciation Specialist** was created for
pronunciation-focused conversations.

Chinnu can hand the conversation over when specialized pronunciation
help is needed.

The flow becomes:

``` text
Child
  ↓
Chinnu
  ↓
Pronunciation need detected
  ↓
Handoff
  ↓
Pronunciation Specialist
  ↓
Continue conversation
```

The conversation context is preserved so the child does not have to
explain the same problem again.

Normal learning conversations remain with Chinnu.

This introduced the idea of specialization:

> Multi-agent systems are not about adding more agents. They are about
> giving each agent a clear responsibility.

------------------------------------------------------------------------

## Day 10 --- Documenting and Sharing the Journey

The final day focused on turning the build into something other
developers can understand and reproduce.

The goal was to document:

-   The problem
-   The architecture
-   The technology stack
-   The major features
-   Challenges
-   Setup instructions
-   Environment variables
-   Testing
-   Deployment
-   Lessons learned

This README is part of that documentation.

------------------------------------------------------------------------

# System Architecture

The complete system can be viewed as several layers.

``` text
                         ┌─────────────────────┐
                         │        Child        │
                         └──────────┬──────────┘
                                    │
                         Browser / Phone
                                    │
                         ┌──────────▼──────────┐
                         │       LiveKit       │
                         │ Real-time Transport │
                         └──────────┬──────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     │              │              │
                     ▼              ▼              ▼
                Deepgram         Gemini       Murf Falcon
                   STT             LLM             TTS
                                    │
                   ┌────────────────┼─────────────────┐
                   │                │                 │
                   ▼                ▼                 ▼
               MongoDB       Dictionary API      Escalation
                Memory            Tool               Tool
                   │                                  │
                   │                                  ▼
                   │                           Parent Dashboard
                   │
                   ▼
             Learning Context

                         Gemini
                           │
                           ▼
                 Specialized Need?
                           │
                         Yes
                           ▼
              Pronunciation Specialist
```

------------------------------------------------------------------------

# Core Voice Pipeline

The core pipeline contains four important concepts.

## 1. Speech-to-Text --- Deepgram

The child speaks into the microphone or phone.

Deepgram converts the audio into text.

For example:

``` text
Child speaks:
"I want to learn ball"
        ↓
Deepgram STT
        ↓
"I want to learn ball"
```

The text is then passed to the LLM.

Deepgram Nova-3 is used as the default STT provider.

------------------------------------------------------------------------

## 2. LLM --- Google Gemini

Gemini acts as the reasoning and orchestration layer.

It receives the conversation and determines what should happen.

It can:

-   Respond directly
-   Retrieve memory
-   Save information
-   Call the dictionary
-   Create an escalation
-   Hand off to a specialist

This is where the system becomes agentic.

The LLM is not only generating a sentence.

It can decide which action is required.

------------------------------------------------------------------------

## 3. Text-to-Speech --- Murf Falcon

Once the response is ready, Murf Falcon converts the generated text into
speech.

Murf Falcon provides the voice of Chinnu.

The starter information used for this project describes Falcon as
providing:

-   55ms model latency
-   130ms time-to-first-audio across 10+ global regions
-   150+ voices
-   35+ languages
-   99.38% pronunciation accuracy
-   \$0.01 per 1,000 characters

Murf voice configuration is handled through the TTS configuration in the
backend.

------------------------------------------------------------------------

## 4. Real-Time Transport --- LiveKit

LiveKit connects the different parts of the real-time conversation.

It handles the real-time audio transport between the user and the voice
agent.

This same infrastructure can support:

-   Browser voice sessions
-   SIP/telephone sessions

That is why LiveKit is an important layer rather than simply another
API.

------------------------------------------------------------------------

# Technology Stack

  -----------------------------------------------------------------------
  Layer                   Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Voice transport         LiveKit Agents          Real-time voice
                                                  communication

  STT                     Deepgram Nova-3         Converts speech to text

  LLM                     Google Gemini           Reasoning, conversation
                                                  and tool decisions

  TTS                     Murf Falcon             Converts responses into
                                                  natural speech

  Frontend                Next.js                 Web application

  Styling                 Tailwind CSS            UI styling

  Database                MongoDB                 Persistent learning
                                                  memory and analytics

  Dictionary              Free Dictionary API     External word
                                                  information

  Telephony               Twilio                  Telephone connectivity

  Telephony transport     LiveKit SIP             Connects LiveKit to
                                                  phone networks

  Backend                 Python                  Voice-agent
                                                  implementation

  Package manager         uv                      Python dependency
                                                  management

  Frontend package        pnpm                    Node.js dependency
  manager                                         management
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# Feature Breakdown

## 1. Personality and Guardrails

The system prompt defines:

-   Chinnu's identity
-   Role
-   Learning objectives
-   Conversation style
-   Supported languages
-   Safety boundaries
-   Escalation conditions
-   Tool usage behavior

The prompt is located in:

``` text
backend/src/agent.py
```

The important design principle is:

``` text
Capabilities + Boundaries
```

not just capabilities.

------------------------------------------------------------------------

## 2. Child-Friendly Frontend

The frontend was designed around a child-friendly experience.

Important elements include:

-   Chinnu character
-   Animated word bubbles
-   Language indicators
-   Talk button
-   Microphone permission guidance
-   Agent state indicators
-   Listening/speaking indicator

The frontend is built using:

``` text
Next.js
Tailwind CSS
```

------------------------------------------------------------------------

## 3. Persistent Learning Memory

MongoDB stores persistent learning information.

The memory system supports:

``` text
Authenticated Child
       ↓
Child-specific identity
       ↓
MongoDB record
       ↓
Function tools
       ↓
Agent retrieves/updates relevant learning data
```

Memory is not simply placed into the system prompt.

The agent retrieves relevant information when required.

This keeps the conversational context focused while allowing persistent
learning information to survive across sessions.

------------------------------------------------------------------------

## 4. Function Calling and Dictionary Tool

The dictionary is exposed to Gemini as a function tool.

Conceptually:

``` text
Gemini
  │
  ├── Answer directly
  │
  └── Call dictionary tool
            ↓
       Free Dictionary API
            ↓
       Result returned
            ↓
          Gemini
            ↓
     Child-friendly response
```

The tool also has a failure path.

If the dictionary cannot provide useful information, Chinnu should
respond naturally rather than inventing a definition.

------------------------------------------------------------------------

## 5. Outbound Phone Calls

The telephony system connects the AI agent to a real phone number.

``` text
AI Agent
   ↓
LiveKit
   ↓
SIP
   ↓
Twilio
   ↓
Telephone Network
```

The outbound system requires:

-   A SIP provider
-   A phone number
-   LiveKit SIP configuration
-   Outbound calling configuration

Phone numbers and provider charges depend on the provider and region.

------------------------------------------------------------------------

## 6. Human Escalation

Escalation is implemented as a controlled tool action.

The agent first identifies a situation that needs human involvement.

Then:

``` text
Agent identifies escalation
        ↓
Explains what will be shared
        ↓
Requests consent
        ↓
User agrees?
     /       \
   Yes        No
    ↓          ↓
Create       Nothing
request      created
    ↓
Notify parent
```

The escalation is associated with the correct child.

------------------------------------------------------------------------

## 7. Call Analytics

The analytics system records learning outcomes and call results.

The current success definition is:

``` text
Successful Session
=
At least 2 unique words successfully learned
```

The dashboard provides a high-level view of:

``` text
Total Calls
Successful Calls
Failed Calls
```

This creates a measurable link between the agent's activity and the
application's actual objective.

------------------------------------------------------------------------

## 8. Specialist Agent Handoff

The Pronunciation Specialist has a separate role and instructions.

Chinnu remains the primary learning companion.

When pronunciation-specific help is required:

``` text
Chinnu
   ↓
Handoff Tool
   ↓
Pronunciation Specialist
```

The context is preserved during the transition.

This avoids forcing one agent to become an expert at every possible
task.

------------------------------------------------------------------------

# How the Agent Decides What to Do

At a conceptual level, Gemini acts as the decision-making layer.

For a normal learning request:

``` text
User speaks
   ↓
STT
   ↓
Gemini
   ↓
Generate response
   ↓
TTS
```

For a memory request:

``` text
User speaks
   ↓
STT
   ↓
Gemini
   ↓
Memory tool
   ↓
MongoDB
   ↓
Gemini
   ↓
TTS
```

For a dictionary request:

``` text
User speaks
   ↓
STT
   ↓
Gemini
   ↓
Dictionary tool
   ↓
External API
   ↓
Gemini
   ↓
TTS
```

For an escalation:

``` text
User speaks
   ↓
STT
   ↓
Gemini
   ↓
Consent
   ↓
Escalation tool
   ↓
MongoDB / Parent dashboard
```

For pronunciation specialization:

``` text
User speaks
   ↓
STT
   ↓
Gemini
   ↓
Handoff decision
   ↓
Pronunciation Specialist
```

This is the central agentic pattern used throughout BoloBuddy:

> **Understand → Decide → Act → Observe result → Continue**

------------------------------------------------------------------------

# Learning Success Definition

One of the most important design decisions was defining success before
building analytics.

For BoloBuddy:

``` text
A session is successful
when the child learns at least
2 unique words.
```

Therefore:

``` text
Child
  ↓
Conversation
  ↓
Words practiced
  ↓
Unique successful words
  ↓
Count >= 2
  ↓
Successful session
```

This prevents misleading metrics.

For example, a 20-minute conversation is not automatically a successful
learning session.

The system needs to evaluate the actual learning objective.

------------------------------------------------------------------------

# Project Structure

The starter architecture is organized into separate backend and frontend
applications.

``` text
murf-livekit-starter/
│
├── backend/
│   ├── src/
│   │   ├── agent.py
│   │   └── telephony/
│   │       ├── inbound/
│   │       └── outbound/
│   │
│   ├── tests/
│   ├── .env.example
│   ├── pyproject.toml
│   └── railway.toml
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   └── api/
│   │       └── token/
│   │
│   ├── components/
│   ├── app-config.ts
│   ├── .env.example
│   └── package.json
│
├── start_app.sh
├── start_app.ps1
└── README.md
```

The BoloBuddy-specific implementation extends this foundation with the
application's memory, learning, analytics, escalation, and
specialist-agent functionality.

------------------------------------------------------------------------

# Getting Started

## Prerequisites

Install:

-   Python 3.10+
-   uv
-   Node.js 18+
-   pnpm
-   A LiveKit project
-   Required API accounts/keys

------------------------------------------------------------------------

## Install uv

### macOS / Linux

``` bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows PowerShell

``` powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

------------------------------------------------------------------------

## Install pnpm

``` bash
npm install -g pnpm
```

------------------------------------------------------------------------

# Clone the Project

``` bash
git clone https://github.com/murf-ai/murf-livekit-starter.git
cd murf-livekit-starter
```

------------------------------------------------------------------------

# Environment Variables

Create `.env.local` files based on the `.env.example` files.

## Backend

The backend requires credentials such as:

``` env
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

MURF_API_KEY=
DEEPGRAM_API_KEY=

GOOGLE_API_KEY=
```

If using OpenAI instead of Gemini, the corresponding OpenAI
configuration can be used.

## Frontend

The frontend uses the LiveKit connection configuration:

``` env
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

AGENT_NAME=
```

`AGENT_NAME` is optional depending on the dispatch configuration.

------------------------------------------------------------------------

# Important: Never Commit Secrets

Do not put real API keys directly into:

-   `agent.py`
-   React/Next.js source files
-   GitHub repositories
-   Screenshots
-   README files
-   Public demo videos

Use environment variables.

Your `.gitignore` should exclude files such as:

``` text
.env
.env.local
.env.*
```

while keeping safe example files such as:

``` text
.env.example
```

------------------------------------------------------------------------

# Backend Installation

From the backend directory:

``` bash
cd backend
uv sync
```

Then download any required agent files:

``` bash
uv run python src/agent.py download-files
```

------------------------------------------------------------------------

# Frontend Installation

From the frontend directory:

``` bash
cd frontend
pnpm install
```

------------------------------------------------------------------------

# Running the Project

There are two approaches.

## Option A --- Start Everything

From the project root:

### macOS / Linux

``` bash
chmod +x start_app.sh
./start_app.sh
```

### Windows PowerShell

``` powershell
.\start_app.ps1
```

------------------------------------------------------------------------

## Option B --- Run Services Separately

### Terminal 1 --- LiveKit

``` bash
livekit-server --dev
```

### Terminal 2 --- Backend

``` bash
cd backend
uv run python src/agent.py dev
```

### Terminal 3 --- Frontend

``` bash
cd frontend
pnpm dev
```

Then open:

``` text
http://localhost:3000
```

------------------------------------------------------------------------

# Testing a Conversation

Once the application is running:

1.  Open the frontend.
2.  Click **Start talking**.
3.  Allow microphone access.
4.  Speak to Chinnu.
5.  Observe the agent state.
6.  Listen to the response generated using Murf Falcon.

For multilingual testing, try natural Telugu + English code-mixed
conversations.

For feature testing, test scenarios such as:

``` text
Normal learning conversation
        ↓
Memory retrieval
        ↓
Dictionary lookup
        ↓
Tool failure
        ↓
Human escalation
        ↓
Pronunciation handoff
```

------------------------------------------------------------------------

# Customizing the Agent

The main system prompt is located in:

``` text
backend/src/agent.py
```

Look for:

``` text
SYSTEM_PROMPT
```

Changing this prompt changes the agent's behavior.

For example, the same voice infrastructure can be adapted into:

-   Customer support
-   Language tutoring
-   Receptionist
-   Appointment assistant
-   Educational companion

The voice pipeline does not fundamentally need to change.

The agent's role and tools can change around it.

------------------------------------------------------------------------

# Changing the Murf Voice

The TTS configuration can be changed in the backend.

The starter supports configurable Murf voice IDs.

Examples provided by the starter include:

-   Anisha --- Indian English
-   Pooja --- Indian English
-   Samar --- Indian English
-   Amara --- US English
-   Gordon --- US English
-   Hazel --- UK English
-   Bertie --- UK English

The selected voice becomes the voice the user hears from the agent.

------------------------------------------------------------------------

# Changing the STT Provider

The default STT configuration uses:

``` text
Deepgram Nova-3
```

The STT configuration is defined in the backend `AgentSession`.

A compatible LiveKit STT provider can be substituted if required.

------------------------------------------------------------------------

# Changing the LLM

The project uses Gemini as the LLM.

The backend can be configured to use:

``` text
Google Gemini
```

or an alternative supported LLM configuration.

The important architecture remains:

``` text
STT
 ↓
LLM
 ↓
TTS
```

The provider can change without changing the conceptual pipeline.

------------------------------------------------------------------------

# Outbound Telephony Architecture

The telephony portion uses LiveKit SIP and Twilio.

The high-level architecture is:

``` text
                    AI VOICE AGENT
                          │
                       LiveKit
                          │
                         SIP
                          │
                        Twilio
                          │
                   Phone Network
                          │
                    Real Phone
```

The starter includes telephony examples under:

``` text
backend/src/telephony/
```

with:

``` text
inbound/
outbound/
```

The outbound flow triggers a call and dispatches the agent into the
LiveKit room.

A SIP provider such as Twilio is responsible for connecting the system
to the telephone network.

Phone numbers may involve provider charges and regional verification
requirements.

------------------------------------------------------------------------

# Deployment

The starter architecture separates the frontend and backend.

## Backend

The Python agent can be deployed as a long-running service.

The starter provides Railway deployment configuration.

Typical backend environment variables include:

``` text
MURF_API_KEY
DEEPGRAM_API_KEY
GOOGLE_API_KEY
LIVEKIT_URL
LIVEKIT_API_KEY
LIVEKIT_API_SECRET
```

------------------------------------------------------------------------

## Frontend

The Next.js frontend can be deployed separately, for example using
Vercel.

Typical frontend variables include:

``` text
LIVEKIT_URL
LIVEKIT_API_KEY
LIVEKIT_API_SECRET
AGENT_NAME
```

------------------------------------------------------------------------

## Connecting Frontend and Backend

The frontend and backend do not need to communicate directly.

Both connect to the same LiveKit project.

``` text
                 LiveKit Project
                 /             \
                /               \
        Frontend                Backend
        Next.js               Python Agent
```

The critical requirement is that both use the same LiveKit
configuration.

If the agent does not connect:

1.  Verify `LIVEKIT_URL`
2.  Verify the API key
3.  Verify the API secret
4.  Verify the backend process is running
5.  Check backend logs
6.  Verify the frontend is connected to the same LiveKit project
7.  Verify the agent name/dispatch configuration if one is being used

------------------------------------------------------------------------

# Security and Privacy

Because BoloBuddy is designed for children, security and privacy are
especially important.

The project includes several safeguards:

### Environment-based secrets

API keys are stored in environment variables rather than source code.

### Child-level memory isolation

Memory access is associated with the authenticated child rather than
allowing unrestricted selection of another child's record.

### Consent before memory storage

New learning information is not automatically saved without permission.

### Consent before escalation

The agent asks for permission before creating an escalation request.

### Limited escalation data

The escalation system creates a concise request rather than
automatically exposing the entire conversation.

### No private information in public repositories

Do not publish:

-   API keys
-   Phone numbers
-   Caller information
-   Authentication secrets
-   Private database records
-   Personal child information

------------------------------------------------------------------------

# Failure Handling

Voice agents operate across multiple external services.

Failures are therefore expected.

BoloBuddy includes graceful handling for cases such as dictionary lookup
failure.

Example:

``` text
Gemini decides to call dictionary
        ↓
Dictionary API fails
        ↓
Tool returns failure
        ↓
Gemini receives failure
        ↓
Chinnu gives a natural response
```

Instead of:

``` text
ERROR: API returned null
```

the child should receive a normal conversational response such as:

> "I couldn't find that word yet. Let's try a new one."

This is important because an agent should fail conversationally, not
technically.

------------------------------------------------------------------------

# What I Learned

## 1. Voice is only the interface

The real complexity is everything behind the voice.

STT, LLM, TTS, transport, memory, tools, databases, telephony,
analytics, and handoffs all have to work together.

------------------------------------------------------------------------

## 2. Prompts define behavior, but tools expand capability

The LLM can reason about what should happen.

Tools allow it to actually interact with external systems.

``` text
LLM
 +
Tools
 =
Agentic behavior
```

------------------------------------------------------------------------

## 3. Memory should be purposeful

Remembering everything is not necessarily useful.

The important question is:

> What information will make the next interaction better?

------------------------------------------------------------------------

## 4. Agents need boundaries

A trustworthy agent is defined not only by what it can do but also by
what it refuses to do.

------------------------------------------------------------------------

## 5. Failure paths matter

External APIs fail.

Network connections fail.

Users say unexpected things.

A production voice agent needs a useful response for those situations.

------------------------------------------------------------------------

## 6. Success must be measurable

For BoloBuddy, the objective is learning.

Therefore the success metric should reflect learning rather than simply
conversation duration.

------------------------------------------------------------------------

## 7. Human escalation is a capability

An AI system does not become weaker by asking a human for help.

Knowing when not to act alone can be a sign of a better-designed system.

------------------------------------------------------------------------

## 8. Multi-agent systems need specialization

Adding more agents is not automatically better.

Each agent should have a clear responsibility.

Chinnu handles general learning.

The Pronunciation Specialist handles pronunciation-focused help.

------------------------------------------------------------------------

# Future Improvements

BoloBuddy is still an evolving project.

Potential next steps include:

-   More advanced learning analytics
-   Richer parent dashboards
-   More personalized learning paths
-   Stronger pronunciation evaluation
-   More sophisticated progress tracking
-   Additional Indian language support
-   More specialized learning agents
-   More robust evaluation of learning outcomes
-   Stronger production-grade authentication and privacy controls

The guiding principle remains:

> Add capabilities only when they improve the child's learning
> experience.

------------------------------------------------------------------------

# Project Links

## Source Code

\[Add your public GitHub repository link here\]

## Demo

\[Add your demo/video link here\]

## Blog

\[Add your published blog link here\]

## Challenge

**10 Days of Voice Agents --- VoiceForBharat Edition**

by **Murf AI**

------------------------------------------------------------------------

# Acknowledgements

This project was built using the voice-agent ecosystem provided by:

-   **Murf Falcon** --- Text-to-Speech
-   **LiveKit Agents** --- Real-time voice infrastructure
-   **Deepgram** --- Speech-to-Text
-   **Google Gemini** --- LLM
-   **MongoDB** --- Persistent data
-   **Twilio** --- Telephony
-   **Next.js** --- Frontend
-   **Tailwind CSS** --- Styling
-   **Free Dictionary API** --- External dictionary data

------------------------------------------------------------------------

# Final Thought

BoloBuddy started as a simple question:

> Can an AI talk to a child?

After ten days, the more interesting question became:

> Can an AI know what to do with that conversation?

That led from voice, to personality, to memory, to tools, to phone
calls, to human escalation, to analytics, and finally to specialist
agents.

The biggest lesson from the challenge was simple:

**A useful voice agent isn't just an AI that can talk.**

**It's a system that knows what to do, when to do it, what not to do,
when to ask for help, and how to measure whether it actually achieved
its goal.**

🐥 **That's what BoloBuddy is trying to become.**

------------------------------------------------------------------------

## Built as part of

**10 Days of Voice Agents --- VoiceForBharat Edition**

#VoiceForBharat #10DaysOfVoiceAgents #VoiceAI #BoloBuddy #MurfFalcon
#LiveKit #LearningAndLiteracy #AIForGood #MultiAgentAI
