import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { LandingPage } from "./pages/LandingPage";
import { TranslatePage } from "./pages/TranslatePage";
import { GettingStartedPage } from "./pages/GettingStartedPage";
import { ApiReferencePage } from "./pages/ApiReferencePage";
import { StatusPage } from "./pages/StatusPage";
import { ArchitecturePage } from "./pages/ArchitecturePage";
import { AdminPage } from "./pages/AdminPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-dlv-surface">
        <Header />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/translate" element={<TranslatePage />} />
            <Route path="/getting-started" element={<GettingStartedPage />} />
            <Route path="/api-reference" element={<ApiReferencePage />} />
            <Route path="/architecture" element={<ArchitecturePage />} />
            <Route path="/status" element={<StatusPage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
