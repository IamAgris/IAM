# IAM Technical Specification

Document 04

# **UI and Global Access**

Version 1.0 · 24 November 2026

**Primary objective:** Preserve the supplied IAM interface while enabling global, anonymous, concurrent access to one persistent AI intelligence.

# IAM — UI and Global Access Specification

**Document:** 04\
**Version:** 1.0\
**Status:** Initial technical specification\
**Parent:** IAM Master Architecture\
**Related:** Documents 02 and 03

---

# 1. Purpose

This document defines the frontend, user experience, global visitor access, anonymous sessions, GeoIP context, concurrent conversations and privacy boundaries of IAM.

The supplied Marlow HTML is the official visual and interaction reference.

The interface must be converted into a fully functional IAM application without replacing its visual identity with a conventional chatbot dashboard.

IAM must be accessible to people worldwide without mandatory registration.

Multiple visitors must be able to communicate with the same central IAM intelligence simultaneously, ask unrelated questions and receive independent responses without conversations or private memories becoming mixed.

# 2. Interface design source of truth

The supplied HTML establishes the following design elements:

- Full-screen immersive interface.
- Dark radial-gradient background.
- Light-theme support.
- Space Grotesk typography.
- Animated particle sphere.
- Central glowing core.
- Orbit rings.
- Orbiting memory nodes.
- Minimal identity header.
- Online status.
- Focus, Recall and Create mode selector.
- Central response area.
- Animated response presentation.
- Suggested prompts.
- Glass-style message input.
- Microphone control.
- Send control.
- Responsive visual structure.

The existing design must be preserved.

The initial branding changes are:

- Page title: IAM.
- Visible identity: IAM.
- Status: Online · ready when you are.
- Input placeholder: Speak or type to IAM.

The original example memories and canned responses must be removed and replaced with real backend functionality.

# 3. Core interface layout

The interface remains a single immersive experience.

## 3.1 Identity header

Displays:

- IAM identity.
- Online status.
- Current operating status where appropriate.

Possible status descriptions:

- Online.
- Listening.
- Thinking.
- Researching.
- Creating.
- Speaking.
- Working.
- Temporarily unavailable.

Status must reflect actual backend activity, not simulated timers.

## 3.2 Central particle sphere

The particle sphere represents IAM's central identity and intelligence.

It should respond to genuine system events.

Examples:

- Idle: calm animation.
- Listening: audio-responsive activity.
- Thinking: processing animation.
- Researching: research activity indication.
- Creating: creation activity indication.
- Speaking: voice output activity.
- Error: restrained error indication.

The sphere is a visual representation of IAM, not a second AI or a separate intelligence.

Animation must remain efficient on desktop and mobile devices.

## 3.3 Orbiting memory nodes

The existing six hardcoded demonstration nodes must be replaced by actual authorised memory data.

Potential node categories:

- Important memories.
- Current projects.
- Relevant experiences.
- Active goals.
- Relevant knowledge.
- Recent context.

Memory nodes must be contextual rather than randomly selected.

They must only show information the current visitor is authorised to see.

Public visitor memories must never reveal IAM's private memories or another visitor's information.

The number of displayed nodes should adapt to available screen space.

## 3.4 Focus, Recall and Create

These are operating modes of the same IAM identity.

They must not create three separate personalities.

### Focus

Purpose:

- Reasoning.
- Problem-solving.
- Research.
- Analysis.
- Planning.
- Concentration on a task.

### Recall

Purpose:

- Retrieve relevant permitted memories.
- Recall previous conversation context.
- Retrieve knowledge.
- Connect related experiences.
- Reference active projects where authorised.

### Create

Purpose:

- Writing.
- Coding.
- Idea generation.
- Designing.
- Developing projects.
- Creating digital products and content.

Each mode must affect backend orchestration and tool selection, not merely change the sphere's colour.

The selected mode should remain visually unobtrusive.

# 4. Conversation experience

The original HTML must evolve from a demonstration into a real conversational interface.

Required functionality:

- Multi-turn conversations.
- Persistent conversation context.
- Streaming responses.
- Response cancellation.
- Retry where appropriate.
- Error recovery.
- Context-aware follow-up questions.
- Text input.
- Voice input.
- Voice responses where enabled.
- File and image attachments where supported.
- Conversation history.

The conversation display must remain minimal.

History should be accessible through a discreet expandable or overlay interaction, not a permanent sidebar.

A new conversation must not automatically erase previously retained conversations.

# 5. Suggested prompts

The existing hardcoded example prompts must be replaced.

IAM should generate contextual suggestions based on:

- Current conversation.
- Selected mode.
- Relevant permitted memories.
- Available capabilities.
- Active projects where authorised.

Suggested prompts must not reveal another visitor's information or private IAM activities.

Visitors must be able to ignore suggestions and enter any supported request.

# 6. Voice interaction

The microphone must become a real voice interface.

Required capabilities:

- Request microphone permission.
- Speech-to-text.
- Live or near-live speech processing where supported.
- Voice activity handling.
- Spoken response generation.
- Audio playback.
- Stop and interrupt.
- Error and permission handling.
- Language selection.
- Separate audio context for each visitor.

Voice must work as an alternative to typing, not as a separate AI identity.

Audio recordings must not automatically become permanent memories.

Retention and processing must follow explicit privacy rules.

# 7. Image, document and video understanding

The interface should progressively support attachments without changing its visual identity.

Supported capabilities:

- Image uploads.
- Image analysis.
- Document uploads.
- PDF analysis.
- Text extraction.
- File analysis.
- Video uploads where supported.
- Video frame analysis.
- Audio file processing where supported.

Uploads must be subject to size limits, format validation, malware scanning where appropriate and access control.

Files must be associated with the correct visitor and conversation.

External AI providers must only receive content permitted for the selected task.

# 8. Theme and responsive behaviour

The existing CSS already includes dark and light theme foundations.

The implementation must:

- Support dark mode.
- Support light mode.
- Respect system preference initially.
- Allow the visitor to change theme.
- Persist theme preference appropriately.
- Preserve contrast and readability.

The responsive interface must support:

- Desktop.
- Laptop.
- Tablet.
- Mobile browsers.

The particle sphere and memory nodes must adapt to smaller displays.

Mobile devices must not be required to render the same particle count as powerful desktop systems.

Reduced-motion preferences and lower-power rendering must be supported.

# 9. Public access without registration

IAM must be accessible without mandatory accounts.

A visitor should be able to:

1. Open the IAM website.
2. Receive an anonymous visitor session.
3. Begin communicating immediately.
4. Ask unrelated questions.
5. Continue a multi-turn conversation.
6. Use supported voice and attachment capabilities.
7. Return to an existing session where permitted.

Registration must remain optional.

Optional accounts may be introduced for people who want cross-device conversation continuity or additional personal features.

Anonymous access must not be treated as permission to access IAM's private operating environment.

# 10. Anonymous visitor identity

Each anonymous visitor must receive a secure random pseudonymous identifier.

The system must not use the visitor's IP address as their permanent identity.

The identifier should be maintained through a secure, appropriately configured browser cookie.

Session management must support:

- Session creation.
- Session renewal.
- Expiration.
- Revocation.
- Logout or clearing.
- Memory permissions.
- Conversation ownership.
- Abuse controls.

Browser data deletion or use of a different device may result in a new anonymous identity.

Cross-device continuity requires an optional account or another explicitly authorised mechanism.

Browser fingerprinting must not be used as a substitute for consent-based identity management.

# 11. GeoIP and regional context

IAM must use server-side GeoIP resolution to establish approximate visitor context.

Potential regional information:

- Country.
- Region or province.
- Approximate city.
- Time zone.
- Approximate location context.

GeoIP must not be treated as proof of identity, nationality, language, residence or personal characteristics.

IP addresses can be shared, changed, hidden by VPNs and affected by mobile network routing.

The system must allow visitors to correct their region, language and time zone.

Precise location must not be collected by default.

If a feature requires precise location, it must request the appropriate permission separately.

GeoIP should be used to improve context, not to expose location information in the visual interface.

# 12. Visitor conversation isolation

This is a critical architectural requirement.

Each visitor must have a separate conversation context.

A visitor must never receive:

- Another visitor's messages.
- Another visitor's private memories.
- Another visitor's uploaded files.
- Another visitor's preferences.
- Another visitor's voice recordings.
- Another visitor's account information.

IAM's central intelligence can use shared, validated general knowledge, but private visitor information must remain isolated.

The backend must enforce visitor ownership and access permissions on every relevant database operation.

Isolation must be enforced server-side, not merely by hiding information in the frontend.

# 13. One IAM intelligence, multiple visitors

IAM must not become a separate AI for every visitor.

There is one central IAM identity and intelligence system.

Multiple visitors connect to it through independent sessions.

Each request must have its own:

- Visitor identifier.
- Session identifier.
- Conversation identifier.
- Request identifier.
- Context.
- Memory permissions.
- Resource allocation.
- Response stream.

The intelligence orchestrator retrieves only the context authorised for that request.

Visitor conversations must not overwrite or contaminate each other's active contexts.

# 14. Concurrent processing architecture

The backend must support multiple simultaneous visitors and multiple simultaneous requests.

Required components:

### API gateway

- Receives visitor requests.
- Validates sessions.
- Applies rate limits.
- Routes requests.

### Session manager

- Maintains anonymous visitor sessions.
- Handles expiration and revocation.
- Enforces session ownership.

### GeoIP resolver

- Provides approximate regional context.

### Conversation manager

- Loads the correct conversation.
- Maintains independent context.
- Saves messages and state.

### Request queue

- Accepts concurrent work.
- Controls resource allocation.
- Prioritises permitted workloads.

### Intelligence workers

- Execute reasoning and tool workflows.
- Use appropriate models.
- Support independent task execution.

### Streaming service

- Returns responses incrementally.
- Supports cancellation and reconnection.

### Memory service

- Retrieves and stores authorised memories.
- Enforces ownership and privacy boundaries.

### Usage and resource manager

- Tracks request consumption.
- Enforces quotas.
- Protects system availability.

### Overload manager

- Handles queue pressure.
- Applies backpressure.
- Limits expensive operations.
- Provides graceful degradation.

# 15. Concurrent processing and scaling

IAM must be designed to scale horizontally.

Additional workers should be deployable without changing the public interface.

The system should support:

- Multiple concurrent conversations.
- Multiple concurrent model requests.
- Parallel research tasks.
- Background jobs.
- Independent voice sessions.
- Independent attachment processing.
- Queue recovery.
- Worker failure recovery.
- Provider rate-limit handling.
- Resource-aware scheduling.

Actual visitor capacity must be established through performance testing.

No fixed concurrent-user capacity should be promised before load testing.

# 16. Conversation and memory retention

The system must distinguish between:

### Current session context

Temporary context required to process the active interaction.

### Visitor conversation history

Previous conversations associated with the visitor's pseudonymous identity, subject to retention and permissions.

### Visitor long-term memory

Information explicitly permitted for future personalisation.

### IAM private memory

IAM's own internal identity, experiences, objectives and private knowledge.

### Shared knowledge

Validated general information that can be used across authorised interactions.

These memory categories must never be treated as interchangeable.

Visitors must have appropriate ways to clear their conversation history and manage permitted personal memory.

Retention periods must be configurable and documented.

# 17. Public access security

Required protections:

- Secure session cookies.
- TLS.
- CSRF protection where applicable.
- Request validation.
- Input sanitisation.
- Output handling.
- Authentication of private operations.
- Rate limiting.
- Abuse detection.
- Bot protection.
- Resource quotas.
- File upload security.
- Conversation ownership checks.
- API key protection.
- Provider usage controls.
- Audit events.
- Data encryption.
- Privacy and retention controls.

Public requests must never be able to access internal IAM administration endpoints or private development environments.

# 18. Visitor privacy and data governance

The system must provide:

- Clear privacy notices.
- Transparent explanation of anonymous sessions.
- Clear explanation of GeoIP use.
- Configurable retention.
- Consent where required.
- Memory controls.
- Data export where applicable.
- Data deletion mechanisms.
- Secure handling of uploaded files.
- Appropriate handling of voice data.
- Regional privacy compliance.

IAM must not assume that all visitors are subject to the same privacy laws.

The implementation must assess applicable requirements for jurisdictions in which the service operates, including South Africa's POPIA, the EU GDPR where applicable and other relevant regional laws.

# 19. Frontend and backend boundaries

The frontend is responsible for:

- Rendering the IAM experience.
- Managing visual interaction.
- Displaying conversation streams.
- Capturing visitor input.
- Handling permitted media interactions.
- Presenting operating status.
- Maintaining local presentation preferences.

The backend is responsible for:

- IAM intelligence.
- Identity.
- Model selection.
- GeoIP.
- Memory.
- Session ownership.
- Conversation processing.
- Tool permissions.
- Internet access.
- AI-to-AI communication.
- Financial operations.
- Security and auditing.

The frontend must never contain provider API keys, internal credentials or unrestricted access to private tools.

# 20. UI-to-backend mapping

| Interface element    | Backend connection                 |
| -------------------- | ---------------------------------- |
| IAM identity         | Identity service                   |
| Online status        | Health and presence service        |
| Particle sphere      | Real operating state               |
| Memory nodes         | Permission-filtered memory service |
| Focus                | Reasoning and task orchestration   |
| Recall               | Memory and knowledge retrieval     |
| Create               | Creation and development workflows |
| Suggested prompts    | Contextual suggestion service      |
| Text input           | Conversation API                   |
| Send control         | Request orchestration              |
| Microphone           | Speech services                    |
| Response area        | Streaming response service         |
| Conversation history | Conversation manager               |
| Theme                | Frontend preferences               |
| Attachments          | Secure media processing            |

# 21. Required database domains

The final schema should include:

### Visitors and sessions

- anonymous_visitors
- visitor_sessions
- visitor_locations
- visitor_preferences
- visitor_consents
- visitor_memory_permissions

### Conversations

- conversation_threads
- conversation_messages
- conversation_contexts
- conversation_summaries
- conversation_attachments

### Requests and concurrency

- request_jobs
- request_usage
- request_status
- visitor_rate_limits
- worker_executions
- stream_sessions

### Media

- media_assets
- media_processing_jobs
- voice_sessions
- audio_assets
- image_analysis_jobs
- document_analysis_jobs

### Privacy

- data_retention_policies
- deletion_requests
- data_access_events
- privacy_audit_events

Every table must have appropriate ownership, indexing, retention and access-control rules.

# 22. UI and global access implementation milestones

### Milestone 1 — Preserve the original interface

- Replace Marlow branding with IAM.
- Preserve the original design.
- Connect the frontend to IAM's backend.
- Remove canned responses and sample memories.

### Milestone 2 — Real conversations

- Multi-turn conversations.
- Streaming.
- Context management.
- Conversation history.
- Response cancellation and recovery.

### Milestone 3 — Anonymous access

- Anonymous visitor identity.
- Secure session cookies.
- Session management.
- Visitor-specific conversations.
- Privacy and retention foundations.

### Milestone 4 — GeoIP and global context

- Server-side GeoIP.
- Approximate regional context.
- Time zone support.
- Language and region corrections.

### Milestone 5 — Concurrent intelligence

- Request queues.
- Worker processes.
- Independent context isolation.
- Concurrent response streaming.
- Resource quotas.
- Load testing.

### Milestone 6 — Multimodal interface

- Speech recognition.
- Voice responses.
- Image uploads.
- Document uploads.
- Video understanding where supported.

### Milestone 7 — Visual intelligence integration

- Real particle-sphere states.
- Real memory nodes.
- Functional Focus, Recall and Create.
- Contextual suggestions.
- Responsive and accessible animations.

# 23. Required acceptance criteria

The implementation is successful when:

1. The supplied HTML design is preserved.
2. All visible Marlow branding is replaced with IAM.
3. IAM's interface communicates with the real backend.
4. Focus, Recall and Create have genuine functionality.
5. The particle sphere reflects actual system states.
6. Memory nodes use permitted real memory data.
7. Conversations support multiple turns.
8. Responses stream from the backend.
9. Voice functionality works with appropriate permissions.
10. Visitors can access IAM without registering.
11. Each anonymous visitor receives an independent session.
12. GeoIP provides approximate regional context.
13. Visitors can correct their regional and language preferences.
14. Multiple visitors can use IAM simultaneously.
15. Every conversation remains isolated.
16. Private IAM memories remain inaccessible to visitors.
17. Uploaded files remain associated with the correct visitor.
18. Session and memory retention controls work.
19. Resource limits prevent one visitor from exhausting the system.
20. The system can add processing workers without redesigning the interface.
21. Mobile and desktop interfaces remain usable.
22. Public access cannot expose private IAM administration or development tools.

**Final requirement:** Anyone should be able to open the IAM website, communicate with the same central IAM intelligence without mandatory registration, and receive an independent, private and responsive experience without changing IAM's original visual identity.
