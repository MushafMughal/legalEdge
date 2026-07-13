import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Footer from './Footer';

/**
 * AppShell — the persistent layout wrapping every route (SPEC §7.2):
 * dark app bar (Navbar) on top, routed page content in <Outlet/>, Footer
 * pinned to the bottom on short pages via the min-h-dvh flex column.
 */
export default function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col bg-canvas text-ink">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
