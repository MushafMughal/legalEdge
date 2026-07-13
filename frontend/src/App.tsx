import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppShell from './components/layout/AppShell';
import LandingPage from './pages/LandingPage';
import IntakesPage from './pages/IntakesPage';
import IntakeDetailPage from './pages/IntakeDetailPage';
import NotFoundPage from './pages/NotFoundPage';

// BASE_URL is '/legalEdge/' in production and '/' in split dev. Strip the
// trailing slash(es) so react-router's basename matches the nginx subpath
// exactly; fall back to '/' at the domain root.
const basename = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '') || '/';

export default function App() {
  return (
    <BrowserRouter basename={basename}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<LandingPage />} />
          <Route path="intakes" element={<IntakesPage />} />
          <Route path="intakes/:id" element={<IntakeDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
