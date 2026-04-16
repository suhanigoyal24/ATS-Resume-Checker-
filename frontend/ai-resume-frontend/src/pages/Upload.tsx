// src/pages/Upload.tsx
import UploadResume from "../components/UploadResume";

export default function UploadPage() {
  return (
    <div className="min-h-screen bg-blue-600 flex flex-col items-center justify-center p-4 py-12">
      <div className="w-full max-w-3xl">
        <UploadResume />
      </div>
    </div>
  );
}