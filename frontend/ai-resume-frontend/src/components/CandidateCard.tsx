type Props = {
  name: string;
  skills: string[];
  score: number;
};

export default function CandidateCard({ name, skills, score }: Props) {
  return (
    <div className="bg-white shadow-lg rounded-2xl p-4 hover:scale-105 transition border-l-4 border-purple-500">
      <h2 className="text-xl font-semibold text-blue-600">{name}</h2>

      {/* Skills */}
      <div className="mt-2 flex flex-wrap gap-2">
        {skills.map((skill, i) => (
          <span
            key={i}
            className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-sm"
          >
            {skill}
          </span>
        ))}
      </div>

      {/* Score */}
      <div className="mt-3">
        <span className="text-sm font-medium">ATS Score:</span>
        <div className="w-full bg-gray-200 rounded-full h-3 mt-1">
          <div
            className={`h-3 rounded-full ${
              score > 80 ? "bg-green-500" : "bg-yellow-400"
            }`}
            style={{ width: `${score}%` }}
          ></div>
        </div>
        <p className="text-right text-sm mt-1">{score}%</p>
      </div>

      {/* Status */}
      <p
        className={`mt-2 font-semibold ${
          score > 75 ? "text-green-600" : "text-red-500"
        }`}
      >
        {score > 75 ? "Selected ✅" : "Rejected ❌"}
      </p>
    </div>
  );
}
