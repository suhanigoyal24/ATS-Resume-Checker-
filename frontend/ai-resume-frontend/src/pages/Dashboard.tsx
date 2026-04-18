// src/pages/Dashboard.tsx
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

interface DashboardCandidate {
  id: number;
  name: string;
  score: number;              // SINGLE SCORE
  verdict: string;
  file_url?: string;
  skills: string[];
  matched_keywords: string[];
  missing_keywords: string[];
  analyzed_at?: string;
}

interface Summary {
  total_candidates: number;
  avg_score: number;          // SINGLE AVERAGE
  pass_rate: number;
  top_candidate: string | null;
  analyzed_at?: string;
}

export default function Dashboard() {
  const [candidates, setCandidates] = useState<DashboardCandidate[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLatest = async () => {
      try {
        setLoading(true);
        const res = await fetch("http://127.0.0.1:8000/api/dashboard/latest/");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const data = await res.json();
        setCandidates(data.candidates);
        setSummary(data.summary);
        setChartData(data.charts?.comparison || []);
      } catch (err: any) {
        console.error("Failed to fetch dashboard:", err);
        setError("Could not load latest batch. Try uploading resumes first.");
      } finally {
        setLoading(false);
      }
    };

    fetchLatest();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600"></div>
      </div>
    );
  }

  if (error || candidates.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
        <p className="text-5xl mb-4">📊</p>
        <h2 className="text-xl font-bold text-gray-800 mb-2">No Recent Analyses</h2>
        <p className="text-gray-600 mb-6 max-w-md">
          {error || "Upload some resumes to see detailed comparisons and insights here."}
        </p>
        <div className="flex gap-4">
          <Link to="/upload" className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition">
            🚀 Upload Resumes
          </Link>
          <Link to="/history" className="px-6 py-3 bg-white text-blue-600 border border-blue-300 rounded-lg font-medium hover:bg-blue-50 transition">
            📚 View History
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">📊 Latest Analysis</h1>
            <p className="text-gray-600 mt-1">
              {summary?.analyzed_at && `Uploaded: ${new Date(summary.analyzed_at).toLocaleString()}`}
            </p>
          </div>
          <div className="flex gap-3">
            <Link to="/history" className="px-4 py-2 bg-white text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50 transition font-medium">
              📚 View All History
            </Link>
            <Link to="/upload" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
              + New Upload
            </Link>
          </div>
        </div>

        {/*Summary Cards - Single Score */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
              <p className="text-sm text-gray-500">Total Candidates</p>
              <p className="text-2xl font-bold text-blue-600">{summary.total_candidates}</p>
            </div>
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
              <p className="text-sm text-gray-500">Avg. Score</p>
              <p className="text-2xl font-bold text-green-600">{summary.avg_score}%</p>
            </div>
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
              <p className="text-sm text-gray-500">Pass Rate (≥60%)</p>
              <p className="text-2xl font-bold text-purple-600">{summary.pass_rate}%</p>
            </div>
          </div>
        )}

        {/*Comparison Chart - Single Bar */}
        {chartData.length > 0 && (
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-8">
            <h3 className="text-lg font-bold text-gray-800 mb-4">📈 Match Scores</h3>
            <div className="space-y-4">
              {chartData.map((item, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  <span className="w-32 text-sm font-medium text-gray-700 truncate" title={item.name}>
                    {item.name}
                  </span>
                  
                  {/* ✅ Single Score Bar */}
                  <div className="flex-1">
                    <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-500" 
                        style={{ width: `${item.score}%` }}
                        title={`Match Score: ${item.score}%`}
                      />
                    </div>
                  </div>
                  
                  {/* Score + Verdict */}
                  <div className="flex items-center gap-3 w-40 justify-end">
                    <span className="text-lg font-bold text-blue-600">
                      {item.score}%
                    </span>
                    <span className={`text-sm font-medium px-2 py-0.5 rounded-full ${
                      item.verdict === 'Shortlist' 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      {item.verdict}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ✅ Detailed Candidate List - Single Score Badge */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-200 flex justify-between items-center">
            <h3 className="font-semibold text-gray-800">📋 Candidate Details</h3>
            <span className="text-sm text-gray-500">{candidates.length} candidates</span>
          </div>
          
          <div className="divide-y divide-gray-100">
            {candidates.map((candidate) => (
              <div key={candidate.id} className="p-4 hover:bg-gray-50 transition">
                <div className="flex justify-between items-start gap-4">
                  <div className="flex-1">
                    {/* Single Score Badge */}
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-medium text-gray-900">{candidate.name}</h4>
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${
                        candidate.score >= 70 ? 'bg-green-100 text-green-800' :
                        candidate.score >= 40 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {candidate.score}% Match
                      </span>
                      <span className={`text-sm font-medium ${
                        candidate.verdict === 'Shortlist' ? 'text-green-600' : 'text-gray-500'
                      }`}>
                        • {candidate.verdict}
                      </span>
                    </div>
                    
                    {/* Skills */}
                    {candidate.skills.length > 0 && (
                      <div className="mb-2">
                        <p className="text-xs text-gray-500 mb-1">Skills:</p>
                        <div className="flex flex-wrap gap-1">
                          {candidate.skills.slice(0, 6).map((skill, i) => (
                            <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                              {skill}
                            </span>
                          ))}
                          {candidate.skills.length > 6 && (
                            <span className="text-xs text-gray-400">+{candidate.skills.length - 6} more</span>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Match Report */}
                    <div className="grid grid-cols-2 gap-4 mt-3">
                      <div>
                        <p className="text-xs font-medium text-green-700 mb-1">✅ Matched</p>
                        <div className="flex flex-wrap gap-1">
                          {candidate.matched_keywords.slice(0, 4).map((kw, i) => (
                            <span key={i} className="px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-red-700 mb-1">❌ Missing</p>
                        <div className="flex flex-wrap gap-1">
                          {candidate.missing_keywords.slice(0, 4).map((kw, i) => (
                            <span key={i} className="px-2 py-0.5 bg-red-50 text-red-700 rounded text-xs">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex flex-col items-end gap-2">
                    {candidate.file_url && (
                      <a 
                        href={candidate.file_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                      >
                        📄 View Resume
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}