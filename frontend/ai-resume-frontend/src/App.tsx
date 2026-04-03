import { BrowserRouter, Routes, Route, Link } from "react-router-dom";

import DashboardPage from "./pages/Dashboard";
import UploadPage from "./pages/Upload";
import HomePage from "./pages/Home";

export default function App() {
  return (
    <BrowserRouter>
      {/* Navbar */}
      <nav className="bg-black text-white p-4 flex justify-center gap-6">
        <a href="/">Home</a>
        <a href="/upload">Upload</a>
        <a href="/dashboard">Dashboard</a>
      </nav>

      {/* Routes */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  );
}
