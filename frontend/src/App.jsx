import { Navigate, Route, Routes } from "react-router-dom";

import NotFoundPage from "./pages/NotFoundPage";
import WelcomePage from "./pages/WelcomePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route path="/home" element={<Navigate to="/" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
