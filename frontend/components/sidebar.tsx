import Link from "next/link";

const links = [
  { href: "/", label: "Overview" },
  { href: "/projects", label: "Projects" },
];

export function Sidebar() {
  return (
    <aside className="border-b border-ink/10 bg-ink px-6 py-6 text-white lg:min-h-screen lg:border-b-0 lg:border-r">
      <Link href="/" className="block text-xl font-bold tracking-tight">
        SpecForge <span className="text-accent">AI</span>
      </Link>
      <p className="mt-1 text-xs uppercase tracking-[0.2em] text-white/50">System Analyst Workspace</p>
      <nav className="mt-8 flex gap-2 lg:flex-col">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded-lg px-3 py-2 text-sm text-white/75 transition hover:bg-white/10 hover:text-white"
          >
            {link.label}
          </Link>
        ))}
      </nav>
      <div className="mt-8 hidden rounded-xl border border-white/10 bg-white/5 p-4 lg:block">
        <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Current capability</p>
        <p className="mt-2 text-sm text-white/75">Phase 1 · Context intake</p>
      </div>
    </aside>
  );
}
