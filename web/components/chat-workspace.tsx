"use client";

import { startTransition, useEffect, useRef, useState } from "react";

import { getErrorMessage, readJson } from "@/lib/console";

type SourceItem = {
  id: string;
  filename: string;
  content: string;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceItem[];
};

type ChatResponse = {
  answer: string;
  sources?: SourceItem[];
};

const WELCOME_MESSAGE: ChatMessage = {
  id: "assistant-welcome",
  role: "assistant",
  content: "Salem. Start the conversation whenever you’re ready.",
  sources: []
};

const STARTERS = [
  "Tell me what you can help me with.",
  "Help me write a short reply.",
  "Summarize this idea in simple words."
];

export function ChatWorkspace() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [messageInput, setMessageInput] = useState("");
  const [chatPending, setChatPending] = useState(false);
  const [chatError, setChatError] = useState("");
  const [showResources, setShowResources] = useState(false);

  const formRef = useRef<HTMLFormElement | null>(null);
  const streamEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    streamEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, chatPending]);

  async function handleChatSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextMessage = messageInput.trim();
    if (!nextMessage || chatPending) {
      return;
    }

    const history = messages.map(({ role, content }) => ({ role, content }));

    setChatPending(true);
    setChatError("");
    setMessageInput("");
    setMessages((current) => [
      ...current,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content: nextMessage,
        sources: []
      }
    ]);

    try {
      const data = await readJson<ChatResponse>(
        await fetch("/api/chat", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            message: nextMessage,
            history
          })
        })
      );

      startTransition(() => {
        setMessages((current) => [
          ...current,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: data.answer,
            sources: data.sources || []
          }
        ]);
      });
    } catch (error) {
      setChatError(getErrorMessage(error, "Could not get an answer from the backend."));
    } finally {
      setChatPending(false);
    }
  }

  function handleComposerKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  return (
    <section className="page-shell">
      <header className="page-hero">
        <div>
          <p className="eyebrow">Conversation</p>
          <h2>Chat your way.</h2>
          <p className="hero-copy">
            Switch between a plain conversation and a richer view that also shows retrieved
            resources for each assistant reply.
          </p>
        </div>
        <div className="hero-stats">
          <article>
            <span>Messages</span>
            <strong>{Math.max(messages.length - 1, 0)}</strong>
          </article>
          <article>
            <span>Status</span>
            <strong>{chatPending ? "Thinking" : "Ready"}</strong>
          </article>
        </div>
      </header>

      <section className="panel conversation-layout">
        <div className="panel-head">
          <div>
            <p className="panel-kicker">Transcript</p>
            <h3>Talk to the assistant</h3>
          </div>
          <div className="chat-head-actions">
            <button
              className="toggle-button"
              onClick={() => setShowResources((current) => !current)}
              type="button"
            >
              {showResources ? "Hide resources" : "Show resources"}
            </button>
            <span className={`status-pill ${chatPending ? "busy" : "idle"}`}>
              {chatPending ? "Generating" : "Live"}
            </span>
          </div>
        </div>

        <div className="starter-row">
          {STARTERS.map((starter) => (
            <button
              className="starter-chip"
              key={starter}
              onClick={() => setMessageInput(starter)}
              type="button"
            >
              {starter}
            </button>
          ))}
        </div>

        <div className="chat-stream spacious">
          {messages.map((item) => (
            <article key={item.id} className={`bubble ${item.role}`}>
              <div className="bubble-role">{item.role === "user" ? "You" : "AI"}</div>
              <p>{item.content}</p>
              {showResources && item.sources.length ? (
                <div className="sources">
                  {item.sources.map((source) => (
                    <div className="source-card" key={source.id}>
                      <strong>{source.filename}</strong>
                      <span>{source.content}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
          <div ref={streamEndRef} />
        </div>

        <form className="chat-form elevated-form" onSubmit={handleChatSubmit} ref={formRef}>
          <label className="field-shell">
            <span>Message</span>
            <textarea
              onChange={(event) => setMessageInput(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder="Write your message..."
              rows={4}
              value={messageInput}
            />
          </label>

          <div className="composer-foot">
            <p className="keyboard-hint">Enter sends. Shift+Enter adds a new line.</p>
            <div className="actions">
              <button className="primary-button" disabled={chatPending || !messageInput.trim()} type="submit">
                {chatPending ? "Sending..." : "Send"}
              </button>
            </div>
          </div>

          {chatError ? <p className="error-text">{chatError}</p> : null}
        </form>
      </section>
    </section>
  );
}
