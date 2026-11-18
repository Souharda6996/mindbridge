import { StrictMode, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "@fontsource/cormorant-garamond/500.css";
import "@fontsource/cormorant-garamond/600.css";
import "@fontsource/cormorant-garamond/500-italic.css";
import "@fontsource-variable/manrope";
import "@fontsource/ibm-plex-mono/400.css";
import "./styles.css";
import { ThemeProvider } from "./theme";
import Layout from "./components/Layout";
import Home from "./pages/Home";

// Heavier pages load on demand (the face model in Companion is ~6 MB).
const Companion = lazy(() => import("./pages/Companion"));
const Journal = lazy(() => import("./pages/Journal"));
const Toolkit = lazy(() => import("./pages/Toolkit"));
const Counselor = lazy(() => import("./pages/Counselor"));
const HowItWorks = lazy(() => import("./pages/HowItWorks"));
const Settings = lazy(() => import("./pages/Settings"));
const Report = lazy(() => import("./pages/Report"));

const Loading = () => (
  <div className="stack" style={{ gap: 16 }}>
    <div className="skeleton" style={{ height: 46, width: 320 }} />
    <div className="skeleton" style={{ height: 180 }} />
    <div className="skeleton" style={{ height: 260 }} />
  </div>
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <Suspense fallback={<div className="page"><Loading /></div>}>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="companion" element={<Companion />} />
              <Route path="journal" element={<Journal />} />
              <Route path="toolkit" element={<Toolkit />} />
              <Route path="counselor" element={<Counselor />} />
              <Route path="how-it-works" element={<HowItWorks />} />
              <Route path="settings" element={<Settings />} />
              <Route path="report" element={<Report />} />
              <Route path="*" element={<Home />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
);
