import { NavLink } from 'react-router-dom';
import { BRAND_PARENT } from '../../lib/brand';
import Logo from '../ui/Logo';

/**
 * Navbar — dark evergreen app bar: LegalEdge mark (home link) on the left,
 * Home / Intakes nav in the middle-right, "by Traxccel" hint on the far right.
 * (SPEC §7.1 layout: logo · nav · "by Traxccel".)
 */
const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/intakes', label: 'Intakes', end: false },
];

export default function Navbar() {
  return (
    <header className="sticky top-0 z-40 bg-primary-deep text-[#EAF2EE] shadow-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-6 lg:px-8">
        <NavLink
          to="/"
          className="rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          aria-label="LegalEdge home"
        >
          <Logo tone="light" size={30} />
        </NavLink>

        <nav className="ml-2 flex items-center gap-1" aria-label="Primary">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                  isActive
                    ? 'bg-white/10 text-white'
                    : 'text-[#EAF2EE]/75 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>

        <span className="ml-auto hidden text-xs font-medium tracking-wide text-[#EAF2EE]/55 sm:block">
          by {BRAND_PARENT}
        </span>
      </div>
    </header>
  );
}
