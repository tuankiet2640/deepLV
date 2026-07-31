import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { TranslatePage } from "./pages/TranslatePage";
import { DocumentTranslatePage } from "./pages/DocumentTranslatePage";
import { SettingsPage } from "./pages/SettingsPage";
import { ApiKeysPage } from "./pages/ApiKeysPage";
import { GettingStartedPage } from "./pages/GettingStartedPage";
import { ApiReferencePage } from "./pages/ApiReferencePage";
import { StatusPage } from "./pages/StatusPage";
import { ArchitecturePage } from "./pages/ArchitecturePage";
import { AdminPage } from "./pages/AdminPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
        <div className="min-h-screen flex flex-col bg-dlv-surface dark:bg-dlv-dark-bg transition-colors">
          <Header />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/translate" element={<TranslatePage />} />
              <Route path="/documents" element={<DocumentTranslatePage />} />
              <Route
                path="/settings"
                element={
                  <ProtectedRoute>
                    <SettingsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/api-keys"
                element={
                  <ProtectedRoute>
                    <ApiKeysPage />
                  </ProtectedRoute>
                }
              />
              <Route path="/getting-started" element={<GettingStartedPage />} />
              <Route path="/api-reference" element={<ApiReferencePage />} />
              <Route path="/architecture" element={<ArchitecturePage />} />
              <Route path="/status" element={<StatusPage />} />
              <Route
                path="/admin"
                element={
                  <ProtectedRoute>
                    <AdminPage />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </main>
          <Footer />
        </div>
        </ThemeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
