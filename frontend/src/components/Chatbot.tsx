import React, { useState, useEffect, useRef } from "react";

interface Message {
  from: "user" | "bot" | "system";
  text: string;
}

function generateUserId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export default function Chatbot() {
  const [messages, setMessages] = useState<Message[]>([
    { from: "bot", text: "Hi! Welcome to Magento AI Ecommerce Assistant." },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [userId] = useState(() => generateUserId());
  const [pendingAction, setPendingAction] = useState<null | {
    type: string;
    args: Record<string, any>;
  }>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    if (!input.trim()) return;
    const userMessage = input.trim();

    setMessages((msgs) => [...msgs, { from: "user", text: userMessage }]);
    setInput("");
    setIsLoading(true);

    const controller = new AbortController();
    const signal = controller.signal;

    try {
      const response = await fetch("/assistant/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: userId,
          message: userMessage,
        }),
        signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}: Unable to connect to assistant.`);
      }

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
          if (last && last.from === "bot") {
            updated[updated.length - 1] = { ...last, text: botResponse };
          }
          return updated;
        });
      }

      // Try to parse the final bot response to check for action
      try {
        const parsed = JSON.parse(botResponse);
        if (parsed.interruption?.type) {
          setPendingAction({
            type: parsed.interruption.type,
            args: parsed.interruption.args,
          });

          setMessages((msgs) => [
            ...msgs.slice(0, -1),
            {
              from: "bot",
              text: parsed.interruption.message || "An action is pending.",
            },
          ]);
        }
      } catch (err) {
        // Ignore JSON parsing errors — treat as regular message
      }

    } catch (error) {
      console.error("Streaming error:", error);
      setMessages((msgs) => [
        ...msgs,
        {
          from: "bot",
          text: `Sorry, something went wrong: ${(error as Error)?.message || "Unknown error."}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  async function resumeAction(actionType: "accept" | "edit" | "reject", editedArgs: any = {}) {
    if (!pendingAction) return;

    const actionPayload =
      actionType === "edit"
        ? { type: "edit", args: editedArgs }
        : { type: actionType };

    const payload = {
      session_id: userId,
      action: actionPayload,
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

// 🛠️ Read response as text first
const text = await res.text();

let botText = text;
try {
  const parsed = JSON.parse(text);
  botText = parsed.interruption?.message || JSON.stringify(parsed, null, 2);

  if (parsed.interruption?.type) {
    setPendingAction({
      type: parsed.interruption.type,
      args: parsed.interruption.args,
    });
  }
} catch {
  // Not JSON — use plain text as bot message
}


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

  async function clearHistory() {
    try {
      const response = await fetch(`/assistant/chat/${userId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        setMessages([{ from: "bot", text: "Hi! Welcome to Magento AI Ecommerce Assistant." }]);
      }
    } catch (error) {
      console.error("Failed to clear history:", error);
    }
  }

  return (
    <div className="flex flex-col h-full max-h-screen bg-gray-50">
      <div className="flex justify-between items-center p-4 bg-white border-b shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800">Magento AI Assistant</h2>
        <button
          onClick={clearHistory}
          className="text-sm text-gray-500 hover:text-red-500 transition"
          title="Clear conversation history"
        >
          Clear History
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-xs sm:max-w-md md:max-w-lg lg:max-w-xl rounded-lg p-3 ${
                msg.from === "user"
                  ? "bg-blue-600 text-white rounded-br-none"
                  : msg.from === "bot"
                  ? "bg-white text-gray-900 border rounded-bl-none shadow-sm"
                  : "bg-yellow-100 text-yellow-900 border border-yellow-300"
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
              <button
                onClick={() => resumeAction("accept")}
                className="px-4 py-1 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Approve
              </button>
              <button
                onClick={() =>
                  resumeAction("edit", {
                    args: {
                      ...pendingAction.args,
                      sku:
                        prompt("Enter new SKU:", pendingAction.args?.sku) ||
                        pendingAction.args?.sku,
                    },
                  })
                }
                className="px-4 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
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
                className="px-4 py-1 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Reject
              </button>
            </div>
          </div>
        )}

        {isLoading && messages[messages.length - 1]?.text === "" && (
          <div className="flex justify-start">
            <div className="bg-white rounded-lg p-3 border shadow-sm">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                </div>
                <span className="text-sm text-gray-500">Assistant is responding...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t">
        <div className="flex gap-3 max-w-4xl mx-auto">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about products, check stock, get recommendations..."
            disabled={isLoading}
            className="flex-1 border rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            style={{ minHeight: "44px", maxHeight: "120px" }}
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="bg-blue-600 text-white rounded-lg px-6 py-2 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors hover:bg-blue-700 flex items-center justify-center min-w-[80px]"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              "Send"
            )}
          </button>
        </div>
        <div className="text-xs text-gray-400 mt-2 text-center">Session ID: {userId}</div>
      </div>
    </div>
  );
}
