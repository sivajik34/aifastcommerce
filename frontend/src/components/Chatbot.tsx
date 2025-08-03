import React, { useState, useEffect, useRef } from "react";

interface Message {
  from: "user" | "bot" | "system";
  text: string;
}

function generateSessionId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export default function Chatbot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessions, setSessions] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<null | {
    type: string;
    args: Record<string, any>;
  }>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Store/retrieve sessions from localStorage
  useEffect(() => {
    const storedSessions = JSON.parse(localStorage.getItem("chat_sessions") || "[]");
    if (storedSessions.length > 0) {
      setSessions(storedSessions);
      const lastSession = storedSessions[storedSessions.length - 1];
      setSessionId(lastSession);
    } else {
      createNewSession();
    }
  }, []);

  // Fetch history when session changes
  useEffect(() => {
    if (sessionId) {
      fetch(`/assistant/chat/${sessionId}/history`)
        .then(res => res.json())
        .then(data => {
          const restoredMessages = data.messages.map((msg: any) => ({
            from: msg.type === "ai" ? "bot" : msg.type === "human" ? "user" : "system",
            text: msg.content,
          }));
          setMessages(restoredMessages.length > 0 ? restoredMessages : [{ from: "bot", text: "Hi! Welcome to Magento AI Ecommerce Assistant." }]);
        })
        .catch(err => {
          console.error("Failed to load history", err);
          setMessages([{ from: "bot", text: "Hi! Welcome to Magento AI Ecommerce Assistant." }]);
        });
    }
  }, [sessionId]);

  function createNewSession() {
    const newSession = generateSessionId();
    const updated = [...sessions, newSession];
    localStorage.setItem("chat_sessions", JSON.stringify(updated));
    setSessions(updated);
    setSessionId(newSession);
  }

  function switchSession(id: string) {
    setSessionId(id);
  }

  async function sendMessage() {
    if (!input.trim() || !sessionId) return;

    const userMessage = input.trim();
    setMessages((msgs) => [...msgs, { from: "user", text: userMessage }]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("/assistant/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: userMessage }),
      });

      if (!response.ok || !response.body) throw new Error("Unable to connect");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let botResponse = "";
      setMessages((msgs) => [...msgs, { from: "bot", text: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        botResponse += chunk;

        setMessages((msgs) => {
          const updated = [...msgs];
          const last = updated[updated.length - 1];
          if (last?.from === "bot") {
            updated[updated.length - 1] = { ...last, text: botResponse };
          }
          return updated;
        });
      }

      try {
        const parsed = JSON.parse(botResponse);
        if (parsed.interruption?.type) {
          setPendingAction({
            type: parsed.interruption.type,
            args: parsed.interruption.args,
          });
          setMessages((msgs) => [...msgs.slice(0, -1), {
            from: "bot",
            text: parsed.interruption.message || "An action is pending.",
          }]);
        }
      } catch {}

    } catch (error) {
      console.error("Streaming error:", error);
      setMessages((msgs) => [...msgs, {
        from: "bot",
        text: `Sorry, something went wrong: ${(error as Error)?.message || "Unknown error."}`,
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  async function clearHistory() {
    if (!sessionId) return;
    try {
      const res = await fetch(`/assistant/chat/${sessionId}`, { method: "DELETE" });
      if (res.ok) {
        setMessages([{ from: "bot", text: "Hi! Welcome to Magento AI Ecommerce Assistant." }]);
      }
    } catch (e) {
      console.error("Error clearing history", e);
    }
  }

  async function resumeAction(actionType: "accept" | "edit" | "reject", editedArgs: any = {}) {
    if (!pendingAction || !sessionId) return;

    const payload = {
      session_id: sessionId,
      action: actionType === "edit" ? { type: "edit", args: editedArgs } : { type: actionType },
    };

    try {
      setMessages((msgs) => [...msgs, { from: "user", text: `[${actionType.toUpperCase()}]` }]);
      setPendingAction(null);
      setIsLoading(true);

      const res = await fetch("/assistant/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const text = await res.text();
      let botText = text;

      try {
        const parsed = JSON.parse(text);
        botText = parsed.interruption?.message || JSON.stringify(parsed, null, 2);
        if (parsed.interruption?.type) {
          setPendingAction({ type: parsed.interruption.type, args: parsed.interruption.args });
        }
      } catch {}

      setMessages((msgs) => [...msgs, { from: "bot", text: botText }]);
    } catch (err) {
      console.error("Resume failed:", err);
      setMessages((msgs) => [...msgs, { from: "bot", text: "Failed to resume agent." }]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="flex justify-between items-center p-4 bg-white border-b shadow-sm">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Magento AI Assistant</h2>
          <div className="text-xs text-gray-500">Session ID: {sessionId}</div>
        </div>
        <div className="space-x-2 flex items-center">
          <select
            value={sessionId || ""}
            onChange={(e) => switchSession(e.target.value)}
            className="text-sm border rounded px-2 py-1"
          >
            {sessions.map((id) => (
              <option key={id} value={id}>
                {id.slice(0, 8)}...
              </option>
            ))}
          </select>
          <button onClick={createNewSession} className="text-sm text-blue-600 hover:underline">
            + New
          </button>
          <button onClick={clearHistory} className="text-sm text-red-500 hover:underline">
            Clear
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-xl rounded-lg p-3 ${
                msg.from === "user"
                  ? "bg-blue-600 text-white rounded-br-none"
                  : msg.from === "bot"
                  ? "bg-white text-gray-900 border rounded-bl-none shadow-sm"
                  : "bg-yellow-100 text-yellow-900 border"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>
            </div>
          </div>
        ))}

        {pendingAction && (
          <div className="bg-yellow-50 p-4 rounded-md border border-yellow-300 text-sm text-yellow-800">
            <div className="mb-2">
              Pending action: <strong>{pendingAction.type}</strong>
              <pre className="text-xs mt-1">{JSON.stringify(pendingAction.args, null, 2)}</pre>
            </div>
            <div className="flex gap-2">
              <button onClick={() => resumeAction("accept")} className="bg-green-600 text-white px-4 py-1 rounded">
                Approve
              </button>
              <button
                onClick={() =>
                  resumeAction("edit", {
                    args: {
                      ...pendingAction.args,
                      sku:
                        prompt("Enter new SKU:", pendingAction.args?.sku) || pendingAction.args?.sku,
                    },
                  })
                }
                className="bg-blue-600 text-white px-4 py-1 rounded"
              >
                Edit
              </button>
              <button
                onClick={() => {
                  setMessages((msgs) => [
                    ...msgs,
                    { from: "bot", text: "Action rejected. Please modify your request." },
                  ]);
                  setPendingAction(null);
                }}
                className="bg-red-600 text-white px-4 py-1 rounded"
              >
                Reject
              </button>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t">
        <div className="flex gap-3">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Ask about products, check stock, etc..."
            className="flex-1 border rounded-lg p-3 resize-none focus:ring-blue-500"
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="bg-blue-600 text-white rounded-lg px-6 py-2"
          >
            {isLoading ? <span className="animate-spin">⏳</span> : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
