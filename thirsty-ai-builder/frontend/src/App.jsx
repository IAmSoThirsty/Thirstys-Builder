import React from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import ThirstyLogo from "./components/ThirstyLogo";
import Footer from "./components/Footer";
import AuthTokenControl from "./components/AuthTokenControl";
import Home from "./pages/Home";
import Commander from "./pages/Commander";
import Dove from "./pages/Dove";
import Holli from "./pages/Holli";
import Architecture from "./pages/Architecture";
import AppStore from "./pages/AppStore";
import BusinessManager from "./pages/BusinessManager";
import Socials from "./pages/Socials";
import Marketing from "./pages/Marketing";
import RAG from "./pages/Rag";
import About from "./pages/About";

const PAGES = [
  { to: "/", label: "Home", end: true },
  { to: "/commander", label: "Commander" },
  { to: "/dove", label: "Little Dove" },
  { to: "/holli", label: "Holli" },
  { to: "/architecture", label: "Architecture" },
  { to: "/appstore", label: "App Store" },
  { to: "/business", label: "Business Manager" },
  { to: "/socials", label: "Socials" },
  { to: "/marketing", label: "Marketing" },
  { to: "/rag", label: "RAG" },
  { to: "/about", label: "About" },
];

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-white/5 backdrop-blur sticky top-0 z-10">
        <div className="max-w-[1100px] mx-auto px-6 py-3 flex items-center gap-6">
          <NavLink to="/" className="flex items-center gap-2">
            <ThirstyLogo className="w-8 h-8" />
            <span className="font-semibold tracking-tight">ThirstyAi Builder</span>
          </NavLink>
          <nav className="flex flex-wrap gap-1 ml-2 text-sm">
            {PAGES.map((p) => (
              <NavLink
                key={p.to}
                to={p.to}
                end={p.end}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-full transition ${
                    isActive
                      ? "bg-brand-700 text-white"
                      : "text-brand-200 hover:bg-white/5"
                  }`
                }
              >
                {p.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto">
            <AuthTokenControl />
          </div>
        </div>
      </header>
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/commander" element={<Commander />} />
          <Route path="/dove" element={<Dove />} />
          <Route path="/holli" element={<Holli />} />
          <Route path="/architecture" element={<Architecture />} />
          <Route path="/appstore" element={<AppStore />} />
          <Route path="/business" element={<BusinessManager />} />
          <Route path="/socials" element={<Socials />} />
          <Route path="/marketing" element={<Marketing />} />
          <Route path="/rag" element={<RAG />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}
