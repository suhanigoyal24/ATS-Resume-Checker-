// src/App.tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import './index.css';
import type { Candidate } from "./types";

// Import all pages
import Header from "./components/Header";
import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";  

export default function App() {
  const [_candidates, setCandidates] = useState<Candidate[]>([]);

  return (
    <Router>
      <div className="min-h-screen bg-surface">
        {/* Global Header on ALL pages */}
        <Header />
        
        {/* pt-16 pushes content below fixed header */}
        <main className="pt-16">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route 
              path="/upload" 
              element={
                <Upload 
                  onUpload={(candidate: Candidate) => setCandidates(prev => [...prev, candidate])} 
                />
              } 
            />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}