import ChatBot from "../components/ChatBot";
import UploadResume from "../components/UploadResume";

export default function Upload() {
  return (
    <>
      {/* Background + Upload Section */}
      <div className="min-h-screen bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center p-6">
        <UploadResume />
      </div>

      {/* 🤖 ChatBot */}
      <ChatBot />
    </>
  );
}