import { useState } from "react";

export default function ChatBot() {
  const [messages, setMessages] = useState([
    { text: "Hi! I'm your AI assistant 🤖", sender: "bot" },
  ]);
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage = { text: input, sender: "user" };
    let reply = "I can help with resume analysis 😊";

    if (input.toLowerCase().includes("upload")) {
      reply = "You can upload your resume here 📄 (PDF only)";
    } else if (input.toLowerCase().includes("resume")) {
      reply = "Upload your resume and I will analyze it for you!";
    } else if (input.toLowerCase().includes("hi")) {
      reply = "Hello 👋 How can I help you?";
    }

    const botMessage = { text: reply, sender: "bot" };

    setMessages([...messages, userMessage, botMessage]);
    setInput("");
  };

  return (
    <div className="fixed bottom-5 right-5 w-80 bg-white shadow-xl rounded-xl flex flex-col">
      {/* Header */}
      <div className="bg-indigo-600 text-white p-3 rounded-t-xl font-semibold">
        AI Assistant 🤖
      </div>

      {/* Messages */}
      <div className="p-3 h-60 overflow-y-auto text-sm space-y-2">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-2 rounded-lg ${
              msg.sender === "user"
                ? "bg-indigo-100 text-right"
                : "bg-gray-200 text-left"
            }`}
          >
            {msg.text}
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="flex border-t">
        <input
          className="flex-1 p-2 text-sm outline-none"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type message..."
        />
        <button onClick={handleSend} className="bg-indigo-600 text-white px-4">
          Send
        </button>
      </div>
    </div>
  );
}
