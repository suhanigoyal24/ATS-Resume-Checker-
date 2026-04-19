// src/pages/Dashboard.tsx
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

// Defines the structure of a single candidate object received from the backend
interface DashboardCandidate {
  id: number;                    // Unique database ID for the candidate
  name: string;                  // Candidate/resume filename
  score: number;                 // Final blended match score (0-100)
  verdict: string;               // Hiring recommendation: "Shortlist" or "Review"
  file_url?: string;             // Optional URL to view/download the resume file
  skills: string[];              // List of skills extracted from the resume
  matched_keywords: string[];    // Keywords that matched the job description
  missing_keywords: string[];    // Keywords from JD that were missing in resume
  analyzed_at?: string;          // ISO timestamp when analysis was completed
}

// Defines the structure of summary statistics for the dashboard header
interface Summary {
  total_candidates: number;      // Total number of candidates in this batch
  avg_score: number;             // Average match score across all candidates
  pass_rate: number;             // Percentage of candidates with score >= 60%
  top_candidate: string | null;  // Name of the highest-scoring candidate
  analyzed_at?: string;          // Timestamp of the most recent analysis
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function Dashboard() {
  // -------------------------------------------------------------------------
  // STATE MANAGEMENT
  // -------------------------------------------------------------------------
  
  // Stores the list of candidates to display in the table
  const [candidates, setCandidates] = useState<DashboardCandidate[]>([]);
  
  // Stores summary statistics for the header cards
  const [summary, setSummary] = useState<Summary | null>(null);
  
  // Stores data for the comparison bar chart visualization
  const [chartData, setChartData] = useState<any[]>([]);
  
  // Controls the loading spinner visibility while fetching data
  const [loading, setLoading] = useState(true);
  
  // Stores any error message to display to the user
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // DATA FETCHING: Load latest batch from backend on component mount
  // -------------------------------------------------------------------------
  useEffect(() => {
    const fetchLatest = async () => {
      try {
        // Show loading spinner while fetching
        setLoading(true);
        
        // Fetch the latest batch of candidates from the backend API
        const res = await fetch("http://127.0.0.1:8000/api/dashboard/latest/");
        
        // Throw error if HTTP status is not 2xx (e.g., 404, 500)
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        // Parse the JSON response from the backend
        const data = await res.json();
        
        // Update state with the fetched data
        setCandidates(data.candidates);      // Populate candidate list
        setSummary(data.summary);            // Populate summary cards
        setChartData(data.charts?.comparison || []);  // Populate comparison chart
        
      } catch (err: any) {
        // Log error to console for debugging
        console.error("Failed to fetch dashboard:", err);
        
        // Show user-friendly error message in the UI
        setError("Could not load latest batch. Try uploading resumes first.");
        
      } finally {
        // Hide loading spinner regardless of success or failure
        setLoading(false);
      }
    };

    // Execute the fetch function when component first mounts (empty dependency array)
    fetchLatest();
  }, []);  // Empty array = run only once on mount

  // -------------------------------------------------------------------------
  // RENDER: Loading State - Show spinner while data is fetching
  // -------------------------------------------------------------------------
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600"></div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // RENDER: Empty/Error State - Show message if no data or error occurred
  // -------------------------------------------------------------------------
  if (error || candidates.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
        <p className="text-5xl mb-4">📊</p>
        <h2 className="text-xl font-bold text-gray-800 mb-2">No Recent Analyses</h2>
        <p className="text-gray-600 mb-6 max-w-md">
          {error || "Upload some resumes to see detailed comparisons and insights here."}
        </p>
        {/* Action buttons to guide user to next steps */}
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

  // -------------------------------------------------------------------------
  // RENDER: Main Dashboard UI - Display data when successfully loaded
  // -------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        
        {/* -----------------------------------------------------------------
            HEADER SECTION: Page title and navigation buttons
            ----------------------------------------------------------------- */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">📊 Latest Analysis</h1>
            <p className="text-gray-600 mt-1">
              {summary?.analyzed_at && `Uploaded: ${new Date(summary.analyzed_at).toLocaleString()}`}
            </p>
          </div>
          <div className="flex gap-3">
            {/* Link to view all historical analyses (paginated) */}
            <Link to="/history" className="px-4 py-2 bg-white text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50 transition font-medium">
              📚 View All History
            </Link>
            {/* Link to upload new resumes */}
            <Link to="/upload" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
              + New Upload
            </Link>
          </div>
        </div>

        {/* -----------------------------------------------------------------
            SUMMARY CARDS: Display key metrics at a glance
            ----------------------------------------------------------------- */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {/* Card 1: Total number of candidates in this batch */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
              <p className="text-sm text-gray-500">Total Candidates</p>
              <p className="text-2xl font-bold text-blue-600">{summary.total_candidates}</p>
            </div>
            
            {/* Card 2: Average match score across all candidates */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
              <p className="text-sm text-gray-500">Avg. Score</p>
              <p className="text-2xl font-bold text-green-600">{summary.avg_score}%</p>
            </div>
            
            {/* Card 3: Percentage of candidates who passed the threshold (>=60%) */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
              <p className="text-sm text-gray-500">Pass Rate (≥60%)</p>
              <p className="text-2xl font-bold text-purple-600">{summary.pass_rate}%</p>
            </div>
          </div>
        )}

        {/* -----------------------------------------------------------------
            COMPARISON CHART: Visual bar chart comparing candidate scores
            ----------------------------------------------------------------- */}
        {chartData.length > 0 && (
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-8">
            <h3 className="text-lg font-bold text-gray-800 mb-4">📈 Match Scores</h3>
            <div className="space-y-4">
              {chartData.map((item, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  {/* Candidate name (truncated if too long) */}
                  <span className="w-32 text-sm font-medium text-gray-700 truncate" title={item.name}>
                    {item.name}
                  </span>
                  
                  {/* Visual progress bar showing the match score percentage */}
                  <div className="flex-1">
                    <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-500" 
                        style={{ width: `${item.score}%` }}
                        title={`Match Score: ${item.score}%`}
                      />
                    </div>
                  </div>
                  
                  {/* Score percentage + verdict badge displayed to the right */}
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

        {/* -----------------------------------------------------------------
            CANDIDATE DETAILS TABLE: Detailed list of all candidates with info
            ----------------------------------------------------------------- */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {/* Table header with title and candidate count */}
          <div className="p-4 border-b border-gray-200 flex justify-between items-center">
            <h3 className="font-semibold text-gray-800">📋 Candidate Details</h3>
            <span className="text-sm text-gray-500">{candidates.length} candidates</span>
          </div>
          
          {/* Scrollable list of candidate cards */}
          <div className="divide-y divide-gray-100">
            {candidates.map((candidate) => (
              <div key={candidate.id} className="p-4 hover:bg-gray-50 transition">
                <div className="flex justify-between items-start gap-4">
                  <div className="flex-1">
                    
                    {/* Candidate name + score badge + verdict */}
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-medium text-gray-900">{candidate.name}</h4>
                      
                      {/* Color-coded score badge: green >=70%, yellow >=40%, red <40% */}
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${
                        candidate.score >= 70 ? 'bg-green-100 text-green-800' :
                        candidate.score >= 40 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {candidate.score}% Match
                      </span>
                      
                      {/* Verdict text: "Shortlist" in green, "Review" in gray */}
                      <span className={`text-sm font-medium ${
                        candidate.verdict === 'Shortlist' ? 'text-green-600' : 'text-gray-500'
                      }`}>
                        • {candidate.verdict}
                      </span>
                    </div>
                    
                    {/* Skills section: List extracted skills as tags */}
                    {candidate.skills.length > 0 && (
                      <div className="mb-2">
                        <p className="text-xs text-gray-500 mb-1">Skills:</p>
                        <div className="flex flex-wrap gap-1">
                          {/* Show first 6 skills, then "+X more" if there are additional */}
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
                    
                    {/* Match Report: Two-column layout showing matched vs missing keywords */}
                    <div className="grid grid-cols-2 gap-4 mt-3">
                      {/* Left column: Keywords that matched the job description */}
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
                      
                      {/* Right column: Keywords from JD that were missing in resume */}
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
                  
                  {/* -----------------------------------------------------------------
                      ACTIONS COLUMN: Buttons for candidate-specific actions
                      ----------------------------------------------------------------- */}
                  <div className="flex flex-col items-end gap-2">
                    {/* View Resume link - opens PDF in new tab */}
                    {candidate.file_url && (
                      <a 
                        href={candidate.file_url} 
                        target="_blank" 
                        rel="noopener noreferrer"  // Security: Prevents reverse tabnabbing attacks
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                      >
                        📄 View Resume
                      </a>
                    )}
                    {/* DUPLICATE VERDICT REMOVED - Already shown in the main card header */}
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