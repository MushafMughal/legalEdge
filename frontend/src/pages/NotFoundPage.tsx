import { Link } from 'react-router-dom';
import { ArrowLeft, Compass } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="mx-auto flex min-h-[60vh] w-full max-w-6xl flex-col items-center justify-center px-6 py-20 text-center lg:px-8">
      <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-panel2 text-primary">
        <Compass className="h-7 w-7" aria-hidden />
      </span>
      <p className="mt-6 font-display text-6xl text-ink">404</p>
      <h1 className="mt-3 font-display text-2xl text-ink">Page not found</h1>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-muted">
        The page you're looking for doesn't exist or may have moved. Let's get you back to your
        intakes.
      </p>
      <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row">
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 font-medium text-white shadow-sm transition hover:bg-primary-deep focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-canvas"
        >
          Go home
        </Link>
        <Link
          to="/intakes"
          className="inline-flex items-center gap-1.5 rounded-xl px-5 py-2.5 font-medium text-muted transition hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          View intakes
        </Link>
      </div>
    </div>
  );
}
