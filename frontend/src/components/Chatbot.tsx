import React, { useState, useEffect, useRef } from "react";

// Updated interface to match backend ProductInfo schema
interface Product {
  product_id: number;
  name: string;
  price: number;
  stock: number;
  status: string;
}

interface Message {
  from: "user" | "bot" | "system";
  text: string;
  products?: Product[];
}

// Generate a valid UUID v4 for the session
function generateUserId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export default function Chatbot() {
  const [messages, setMessages] = useState<Message[]>([
    { from: "bot", text: "Hi! Ask me about any product." },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [userId] = useState(() => generateUserId()); // Generate once per session
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    if (!input.trim()) return;
    const userMessage = input.trim();

    // Update UI immediately
    setMessages((msgs) => [...msgs, { from: "user", text: userMessage }]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          message: userMessage,
        }),
      });

      const data = await response.json();

      if (response.status === 500 && data.error) {
        // Handle server errors gracefully
        throw new Error(data.error);
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${data.detail || 'Request failed'}`);
      }

      const newBotMessage: Message = {
        from: "bot",
        text: data.response || "No response received.",
        products: data.products || [],
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
        setMessages([{ from: "bot", text: "Hi! Ask me about any product." }]);
      }
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  }

  function formatPrice(price: number): string {
    return `₹${price.toLocaleString('en-IN')}`;
  }

  function getStatusColor(status: string): string {
    switch (status.toLowerCase()) {
      case 'in stock':
        return 'text-green-600';
      case 'out of stock':
        return 'text-red-600';
      case 'low stock':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  }

  return (
    <div className="flex flex-col h-full max-h-screen bg-gray-50">
      {/* Header */}
      <div className="flex justify-between items-center p-4 bg-white border-b shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800">Product Assistant</h2>
        <button
          onClick={clearHistory}
          className="text-sm text-gray-500 hover:text-red-500 transition"
          title="Clear conversation history"
        >
          Clear History
        </button>
      </div>

      {/* Messages Container */}
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
                  : "bg-white text-gray-900 border rounded-bl-none shadow-sm"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>

              {/* Product Cards */}
              {msg.products && msg.products.length > 0 && (
                <div className="mt-3 space-y-2">
                  <p className="text-sm font-medium text-gray-600">
                    Found {msg.products.length} product{msg.products.length > 1 ? 's' : ''}:
                  </p>
                  <div className="grid gap-2">
                    {msg.products.map((product, i) => (
                      <div
                        key={i}
                        className="border rounded-lg p-3 bg-gray-50 hover:bg-gray-100 transition"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <h4 className="font-medium text-sm text-gray-900 line-clamp-2">
                            {product.name}
                          </h4>
                          <span className="text-xs text-gray-500 ml-2">
                            ID: {product.product_id}
                          </span>
                        </div>
                        
                        <div className="flex justify-between items-center">
                          <span className="font-semibold text-blue-600">
                            {formatPrice(product.price)}
                          </span>
                          <div className="text-right">
                            <div className="text-xs text-gray-600">
                              Stock: {product.stock}
                            </div>
                            <div className={`text-xs font-medium ${getStatusColor(product.status)}`}>
                              {product.status}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        
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

      {/* Input Area */}
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
        
        {/* User ID display for debugging */}
        <div className="text-xs text-gray-400 mt-2 text-center">
          Session ID: {userId}
        </div>
      </div>
    </div>
  );
}