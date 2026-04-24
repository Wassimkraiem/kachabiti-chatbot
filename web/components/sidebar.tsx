"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  {
    href: "/chat",
    label: "Conversation",
    caption: "Simple chat",
    shortcut: "Enter sends"
  },
  {
    href: "/questions",
    label: "Resources",
    caption: "Qdrant vectors",
    shortcut: "Search and edit"
  }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar-shell">
      <div className="sidebar-brand">
        <p className="sidebar-kicker">Kachabiti</p>
        <h1>Chat space</h1>
        <p className="sidebar-copy">
          Switch between conversation and vector resources from one clean workspace.
        </p>
      </div>

      <nav className="sidebar-nav" aria-label="Primary">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link className={`nav-card ${isActive ? "active" : ""}`} href={item.href} key={item.href}>
              <div>
                <strong>{item.label}</strong>
                <span>{item.caption}</span>
              </div>
              <em>{item.shortcut}</em>
            </Link>
          );
        })}
      </nav>

    </aside>
  );
}
