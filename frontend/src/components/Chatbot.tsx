import React, { useState, useEffect, useRef } from "react";

interface Product {
  title: string;
  price: string;
  link: string;
  image?: string;
}

interface Message {
  from: "user" | "bot" | "system";
  text: string;
  products?: Product[];
}

interface ChatHistoryMessage {
  role: "human" | "ai" | "system";
  content: string;
}

export default function Chatbot() {
  const [messages, setMessages] = useState<Message[]>([
    { from: "bot", text: "Hi! Ask me about any product." },
  ]);
  const [chatHistory, setChatHistory] = useState<ChatHistoryMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    if (!input.trim()) return;
    const userMessage = input.trim();

    // Update UI
    setMessages((msgs) => [...msgs, { from: "user", text: userMessage }]);
    setChatHistory((hist) => [...hist, { role: "human", content: userMessage }]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          history: chatHistory,
        }),
      });

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      const newBotMessage = {
        from: "bot" as const,
        text: data.response || "No response.",
        products: data.products ?? [],
      };

      setMessages((msgs) => [...msgs, newBotMessage]);

      // Update history with latest full server-side version
      if (data.history && Array.isArray(data.history)) {
        setChatHistory(data.history);
      }
    } catch (error) {
      setMessages((msgs) => [
        ...msgs,
        {
          from: "bot",
          text: `Sorry, something went wrong: ${(error as any)?.message ?? "Unknown error."}`,
        },
      ]);
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

  return (
    <div className="flex flex-col flex-1 border rounded-lg bg-white shadow p-4">
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`max-w-3/4 rounded-lg p-3 ${
              msg.from === "user"
                ? "bg-blue-600 text-white self-end rounded-br-none"
                : "bg-gray-200 text-gray-900 self-start rounded-bl-none"
            } flex flex-col`}
          >
            <p>{msg.text}</p>

            {msg.products && msg.products.length > 0 && (
              <div className="mt-2 flex space-x-3 overflow-x-auto">
                {msg.products.map((p, i) => (
                  <a
                    key={i}
                    href={p.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex flex-col w-36 border rounded-lg p-2 hover:shadow-lg transition"
                  >
                    <img
                      src={p.image ?? "https://via.placeholder.com/140"}
                      alt={p.title}
                      className="h-24 object-contain mb-2"
                      loading="lazy"
                    />
                    <strong className="truncate">{p.title}</strong>
                    <span className="text-sm text-gray-600">{p.price}</span>
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="flex gap-3">
        <textarea
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message here..."
          disabled={isLoading}
          className="flex-1 border rounded-lg p-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={sendMessage}
          disabled={isLoading || !input.trim()}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 disabled:bg-blue-300 transition"
        >
          {isLoading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}
