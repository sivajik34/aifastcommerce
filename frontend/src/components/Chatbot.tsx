import React, { useState, useEffect, useRef } from "react";

interface Message {
  from: "user" | "bot" | "system";
  text: string;
}

// Generate a valid UUID v4 for the session
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

    try {
      const response = await fetch("/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: userId,
          message: userMessage,
        }),
      });

      const data = await response.json();

      if (response.status === 500 && data.error) {
        throw new Error(data.error);
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${data.detail || 'Request failed'}`);
      }

      // If there's an interruption, prompt user for action
      if (data.interruption) {
        setPendingAction(data.interruption);
        setMessages((msgs) => [...msgs, { from: "system", text: data.response }]);
        return;
      }

      const newBotMessage: Message = {
        from: "bot",
        text: data.response || "No response received."
      };

      setMessages((msgs) => [...msgs, newBotMessage]);

    } catch (error) {
      console.error('Chat error:', error);
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

  async function resumeAction(action: "accept" | "edit" | "reject", editedArgs: any = {}) {
    if (!pendingAction) return;

    const payload = {
      session_id: userId,
      action: action === "edit"
        ? { type: "edit", args: editedArgs }
        : { type: action }
    };

    try {
      setMessages((msgs) => [...msgs, { from: "user", text: `[${action.toUpperCase()}]` }]);
      setPendingAction(null);
      setIsLoading(true);

      const res = await fetch("/assistant/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      setMessages((msgs) => [...msgs, { from: "bot", text: data.response }]);
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
      console.error('Failed to clear history:', error);
    }
  }

  return (
    <div className="flex flex-col h-full max-h-screen bg-gray-50">
      {/* Header */}
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

      {/* Messages */}
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

        {/* Pending Action UI */}
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
                    ...pendingAction.args,
                    sku: prompt("Enter new SKU:", pendingAction.args.sku) || pendingAction.args.sku
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

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white rounded-lg p-3 border shadow-sm">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span className="text-sm text-gray-500">Assistant is thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
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
            style={{ minHeight: '44px', maxHeight: '120px' }}
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
        <div className="text-xs text-gray-400 mt-2 text-center">
          Session ID: {userId}
        </div>
      </div>
    </div>
  );
}
