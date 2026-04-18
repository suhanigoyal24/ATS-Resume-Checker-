// src/pages/Upload.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Candidate } from "../types";

interface UploadProps {
  onUpload?: (candidate: Candidate) => void;
  onBatchComplete?: () => void;
}

export default function Upload({ onUpload, onBatchComplete }: UploadProps) {
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentFile, setCurrentFile] = useState("");
  const [processingStep, setProcessingStep] = useState("");
  const [progress, setProgress] = useState({ current: 0, total: 0, percent: 0 });
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    if (selected.length > 0) { 
      setFiles(prev => [...prev, ...selected]); 
      setError(null); 
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleBatchUpload = async () => {
    if (files.length === 0) { 
      setError("Please select at least one resume file"); 
      return; 
    }
    if (!jobDescription.trim()) { 
      setError("Please provide a job description"); 
      return; 
    }

    setLoading(true); 
    setError(null); 
    setProgress({ current: 0, total: files.length, percent: 0 });

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setCurrentFile(file.name);
        
        setProcessingStep("📄 Reading resume..."); 
        await new Promise(r => setTimeout(r, 300));
        
        setProcessingStep("🔍 Extracting text & skills..."); 
        await new Promise(r => setTimeout(r, 400));
        
        setProcessingStep("🧠 Analyzing against JD..."); 
        await new Promise(r => setTimeout(r, 500));
        
        setProcessingStep("📊 Calculating score..."); 
        await new Promise(r => setTimeout(r, 300));

        const formData = new FormData();
        formData.append("resume", file);
        formData.append("job_description", jobDescription);
        
        // FIX: AbortController prevents infinite hanging if backend is slow
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

        try {
          const res = await fetch("http://127.0.0.1:8000/api/upload/", { 
            method: "POST", 
            body: formData,
            signal: controller.signal 
          });
          clearTimeout(timeoutId);
          
          if (!res.ok) { 
            const errData = await res.json().catch(() => ({})); 
            throw new Error(errData.detail || `Server responded with ${res.status}`); 
          }

          const data: Record<string, any> = await res.json();
          
          const fields = ['matched_keywords', 'keywords', 'skills', 'matched_skills'];
          const matchedField = fields.find(field => Array.isArray(data[field])); 
          const keywords = matchedField ? data[matchedField] : [];

          const candidate: Candidate = {
            id: data.id || `temp-${Date.now()}-${i}`,
            name: data.name || file.name.replace(/\.[^/.]+$/, ""),
            score: typeof data.score === 'number' ? data.score : 0,
            skills: keywords,
            resume_url: data.resume_url,
            matched_keywords: keywords,
            ...Object.fromEntries(
              Object.entries(data).filter(([k]) => 
                !['id','name','score','skills','resume_url','matched_keywords'].includes(k)
              )
            )
          };
          
          // ✅ FIX: Force React to flush state update before continuing loop
          setProgress({ current: i + 1, total: files.length, percent: Math.round(((i + 1) / files.length) * 100) });
          await new Promise(r => setTimeout(r, 10)); // Micro-yield for React 18 batching
          
          if (onUpload) {
            console.log("📤 Sending candidate to dashboard:", candidate);
            onUpload(candidate);
          }
        } catch (fetchErr: any) {
          clearTimeout(timeoutId);
          if (fetchErr.name === 'AbortError') {
            throw new Error("Backend didn't respond in 30s. Check if Django server is running.");
          }
          throw fetchErr;
        }

        setProcessingStep("✅ Complete!"); 
        await new Promise(r => setTimeout(r, 200));
      }
      
      setProcessingStep("🎉 All done! Redirecting to dashboard...");
      await new Promise(r => setTimeout(r, 800));
      
      if (onBatchComplete) onBatchComplete();
      navigate("/dashboard");

    } catch (err: any) {
      console.error("❌ Upload error:", err);
      setError(err.message || "Processing failed");
      // ✅ FIX: Always reset loading state on error
      setLoading(false);
      setCurrentFile("");
      setProcessingStep("");
      setProgress({ current: 0, total: 0, percent: 0 });
    }
  };

  return (
    // ✅ MATCHES HOME PAGE: bg-blue-600
    <div className="min-h-screen bg-blue-600 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white/95 backdrop-blur-sm p-6 rounded-xl shadow-lg relative">
          
          {/* Loading Overlay */}
          {loading && (
            <div className="absolute inset-0 bg-white/95 backdrop-blur-sm z-40 flex flex-col items-center justify-center p-6 rounded-xl">
              <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-200 border-t-blue-600 mb-6"></div>
              <h3 className="text-xl font-bold text-gray-800 mb-2">
                Processing {files.length} resume{files.length > 1 ? 's' : ''}...
              </h3>
              {currentFile && (
                <p className="text-sm text-gray-600 mb-1">📁 {currentFile}</p>
              )}
              {processingStep && (
                <p className="text-blue-600 font-medium mb-4 animate-pulse">
                  {processingStep}
                </p>
              )}
              {progress.total > 0 && (
                <div className="w-full max-w-md mb-4">
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Resume {progress.current} of {progress.total}</span>
                    <span className="font-semibold text-blue-600">{progress.percent}%</span>
                  </div>
                  <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-600 rounded-full transition-all duration-300" 
                      style={{ width: `${progress.percent}%` }} 
                    />
                  </div>
                </div>
              )}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                <p className="text-xs text-blue-700">💡 Tip: Most resumes take 5-15 seconds.</p>
              </div>
            </div>
          )}

          {/* Form Content */}
          <div className={loading ? "opacity-30 pointer-events-none" : ""}>
            <h2 className="text-xl font-bold text-gray-800 mb-4">📋 Batch Resume Screening</h2>
            
            {/* Job Description */}
            <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <label className="block text-sm font-medium text-blue-900 mb-2">
                🎯 Job Description
              </label>
              <textarea 
                placeholder="Paste job description here..." 
                value={jobDescription} 
                onChange={(e) => setJobDescription(e.target.value)} 
                className="w-full p-3 border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none min-h-[120px]" 
                disabled={loading} 
              />
            </div>
            
            {/* File Upload */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📁 Select Resumes ({files.length})
              </label>
              <div className="border-2 border-dashed border-blue-300 rounded-xl p-6 text-center hover:border-blue-500 cursor-pointer bg-blue-50/50">
                <input 
                  type="file" 
                  multiple 
                  accept=".pdf,.doc,.docx" 
                  onChange={handleFileChange} 
                  className="hidden" 
                  id="upload" 
                  disabled={loading} 
                />
                <label htmlFor="upload" className="cursor-pointer flex flex-col items-center">
                  <span className="text-4xl mb-2">📄</span>
                  <span className="text-blue-600 font-medium">Click to select files</span>
                  <span className="text-xs text-gray-500 mt-1">PDF, DOC, DOCX</span>
                </label>
              </div>
              
              {/* File List */}
              {files.length > 0 && (
                <div className="mt-4 space-y-2 max-h-48 overflow-y-auto">
                  {files.map((f, i) => (
                    <div key={i} className="flex justify-between p-2 bg-gray-50 rounded text-sm">
                      <span className="truncate flex-1">{f.name}</span>
                      <button 
                        onClick={() => removeFile(i)} 
                        className="text-red-500 ml-2 text-xs hover:text-red-700" 
                        disabled={loading}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Error Message */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                ⚠️ {error}
              </div>
            )}
            
            {/* Submit Button */}
            <button 
              onClick={handleBatchUpload} 
              disabled={loading || files.length === 0 || !jobDescription.trim()} 
              className="w-full bg-blue-600 text-white font-semibold py-3 px-6 rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2 shadow-lg"
            >
              {loading ? (
                <>
                  <span className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></span>
                  Processing...
                </>
              ) : (
                `🚀 Analyze ${files.length} Resume${files.length > 1 ? 's' : ''}`
              )}
            </button>
            
            <p className="text-sm text-gray-600 text-center mt-4">
              You'll be redirected to the dashboard after processing.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}