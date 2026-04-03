import ChatBot from "../components/ChatBot";

export default function ChatPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-center mb-6">🤖 AI Assistant</h1>

      <ChatBot />
    </div>
  );
}
