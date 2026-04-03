import { useState } from "react";
import UploadResume from "./UploadResume";
import ChatBot from "./ChatBot";
import CandidateCard from "./CandidateCard";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function Dashboard() {
  const [candidates, setCandidates] = useState([
    { name: "Aman", skills: ["React", "Node"], score: 85 },
    { name: "Riya", skills: ["Python", "ML"], score: 70 },
  ]);

  const [search, setSearch] = useState("");
  const [minScore, setMinScore] = useState(0);

  // Upload handler
  const handleUpload = (newCandidate: any) => {
    setCandidates((prev) => [...prev, newCandidate]);
  };

  // Filter + ranking
  const filteredCandidates = candidates
    .filter((c) => {
      return (
        c.name.toLowerCase().includes(search.toLowerCase()) &&
        c.score >= minScore
      );
    })
    .sort((a, b) => b.score - a.score);

  return (
    <>
      <div className="p-6">
        <h1 className="text-4xl font-extrabold text-center text-gray-800 mb-6">
          🚀 AI Resume Screening System
        </h1>

        {/* Upload */}
        <UploadResume onUpload={handleUpload} />

        {/* Filters */}
        <div className="bg-white p-4 rounded-xl shadow mt-6 flex flex-col md:flex-row gap-4">
          <input
            type="text"
            placeholder="Search candidate..."
            className="border p-2 rounded w-full"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <select
            className="border p-2 rounded w-full md:w-60"
            onChange={(e) => setMinScore(Number(e.target.value))}
          >
            <option value={0}>All Scores</option>
            <option value={60}>Above 60</option>
            <option value={75}>Above 75</option>
            <option value={85}>Above 85</option>
          </select>
        </div>

        {/* Candidate List */}
        <div className="grid md:grid-cols-3 gap-4 mt-6">
          {filteredCandidates.map((c, i) => (
            <div key={i} className="relative">
              {i === 0 && (
                <span className="absolute top-2 right-2 bg-yellow-400 text-white px-2 py-1 text-xs rounded">
                  🏆 Top
                </span>
              )}
              <CandidateCard {...c} />
            </div>
          ))}
        </div>

        {/* Empty State */}
        {filteredCandidates.length === 0 && (
          <p className="text-center text-gray-500 mt-6 text-lg font-medium">
            🚫 No candidates match your filter
          </p>
        )}

        {/* Graph */}
        <div className="bg-white p-4 rounded-2xl shadow-lg mt-8 max-w-3xl mx-auto">
          <h2 className="text-xl font-bold mb-4 text-purple-600 text-center">
            Candidate Scores
          </h2>

          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={filteredCandidates}>
              <XAxis dataKey="name" stroke="#555" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="score" fill="#6366F1" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chatbot */}
    </>
  );
}
