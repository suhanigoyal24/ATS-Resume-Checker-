// Mock data (you can keep this for dashboard)
export const getCandidates = async () => {
  return [
    {
      id: 1,
      name: "Sarah Johnson",
      email: "sarah@email.com",
      role: "Frontend Developer",
      score: 92,
      status: "Shortlisted",
      skills: "React, TypeScript",
    },
    {
      id: 2,
      name: "David Kim",
      email: "david@email.com",
      role: "Backend Developer",
      score: 88,
      status: "Pending",
      skills: "Python, Django",
    },
  ];
};

// REAL BACKEND API CALL
export const uploadResume = async (file: File, jobDesc: string) => {
  const formData = new FormData();
  formData.append("resume", file);
  formData.append("job_description", jobDesc);

  const res = await fetch("http://127.0.0.1:8000/api/analyze/", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error("Failed to analyze resume");
  }

  return res.json();
};