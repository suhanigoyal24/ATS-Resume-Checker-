import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const initialData = [
  { name: "Aman", score: 85 },
  { name: "Riya", score: 70 },
  { name: "Rahul", score: 90 },
  { name: "Sneha", score: 60 },
];

const colors = ["#6366F1", "#22C55E", "#F59E0B", "#EF4444"];

export default function Dashboard() {
  const [search, setSearch] = useState("");
  const [minScore, setMinScore] = useState(0);

  const filtered = initialData
    .filter(
      (c) =>
        c.name.toLowerCase().includes(search.toLowerCase()) &&
        c.score >= minScore,
    )
    .sort((a, b) => b.score - a.score);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-3xl font-bold text-center text-indigo-600 mb-6">
        📊 Dashboard
      </h1>

      {/* Filters */}
      <div className="bg-white p-4 rounded-xl shadow flex flex-col md:flex-row gap-4 mb-6">
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

      {/* Cards */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {filtered.map((c, i) => (
          <div key={i} className="bg-white p-4 rounded-xl shadow text-center">
            <h3 className="font-bold text-lg">{c.name}</h3>
            <p className="text-gray-600">Score: {c.score}</p>

            {i === 0 && (
              <span className="inline-block mt-2 bg-yellow-400 px-2 py-1 text-xs rounded">
                🏆 Top
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Colorful Graph */}
      <div className="bg-white p-6 rounded-2xl shadow max-w-3xl mx-auto">
        <h2 className="text-xl font-bold mb-4 text-center text-purple-600">
          Candidate Scores
        </h2>

        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={filtered}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />

            <Bar dataKey="score" radius={[8, 8, 0, 0]}>
              {filtered.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={colors[index % colors.length]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Empty */}
      {filtered.length === 0 && (
        <p className="text-center mt-6 text-gray-500">🚫 No candidates found</p>
      )}
    </div>
  );
}
