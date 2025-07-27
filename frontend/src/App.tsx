import React from "react";
import Chatbot from "./components/Chatbot";

export default function App() {
  return (
    <div className="max-w-3xl mx-auto p-6 h-screen flex flex-col bg-gray-50">
      <h1 className="text-3xl font-bold mb-4 text-center">Magento AI Assistant based on FastAPI,Langchain</h1>
      <Chatbot />
    </div>
  );
}