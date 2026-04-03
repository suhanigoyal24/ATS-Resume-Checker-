import { useState } from "react";
import { uploadResume } from "../services/api";

export default function UploadResume() {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState("");
  const [result, setResult] = useState<any>(null);

  const handleUpload = async () => {
    console.log("BUTTON CLICKED"); // debug

    if (!file) {
      alert("Please select a file!");
      return;
    }

    try {
      const data = await uploadResume(file, job);

      console.log("API Response:", data);

      setResult(data);
    } catch (error) {
      console.error(error);
      alert("Backend error ❌");
    }
  };

  return (
    <div>
      <h2>Upload Resume</h2>

      <input
        type="file"
        onChange={(e: any) => setFile(e.target.files[0])}
      />

      <textarea
        placeholder="Job description"
        value={job}
        onChange={(e) => setJob(e.target.value)}
      />

      <button onClick={handleUpload}>
        Upload Resume
      </button>

      {result && (
        <div>
          <h3>Score: {result.score}</h3>
          <p>Keywords: {result.matched_keywords.join(", ")}</p>
        </div>
      )}
    </div>
  );
}