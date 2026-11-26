"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bot,
  CalendarClock,
  ChevronDown,
  Compass,
  Home,
  Leaf,
  LogOut,
  MapPin,
  Menu,
  Navigation,
  Search,
  TrendingUp,
  User,
  X,
} from "lucide-react";
import { BrandMark } from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { api } from "@/lib/api";
import { PRESET_CITIES } from "@/lib/constants";
import { LocationSearchResult } from "@/types";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: Activity },
  { href: "/advisor", label: "AI Advisor", icon: Bot },
  { href: "/routine", label: "Daily Routine", icon: CalendarClock },
  { href: "/indoor", label: "Indoor Air", icon: Home },
  { href: "/sustainable", label: "Alternatives", icon: Leaf },
  { href: "/impact", label: "Impact", icon: TrendingUp },
  { href: "/profile", label: "Family & Profile", icon: User },
];

export function LocationPickerModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { location, setLocation, detectGeolocation, geoError } = useBreatheWise();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<LocationSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchErr, setSearchErr] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length < 2) return;
    setSearching(true);
    setSearchErr(null);
    try {
      const res = await api.searchLocations(query.trim());
      setResults(res.results);
      if (res.results.length === 0) {
        setSearchErr("No matching cities found. Try another city name.");
      }
    } catch (err) {
      setSearchErr(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="location-modal-title"
        className="w-full max-w-lg rounded-2xl bg-bw-secondary border border-white/10 p-6 shadow-glass"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2
              id="location-modal-title"
              className="text-base font-semibold text-bw-text"
            >
              Select Monitoring Location
            </h2>
            <p className="text-xs text-bw-muted">
              Current: {location.name} ({location.latitude.toFixed(2)},{" "}
              {location.longitude.toFixed(2)})
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-bw-muted hover:text-bw-text hover:bg-white/5"
            aria-label="Close location modal"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <button
          type="button"
          onClick={async () => {
            await detectGeolocation();
            onClose();
          }}
          className="w-full mb-4 flex items-center justify-center gap-2 rounded-xl border border-bw-accent/30 bg-bw-accent/10 px-4 py-2.5 text-sm font-medium text-bw-accent hover:bg-bw-accent/15 transition-colors"
        >
          <Navigation className="h-4 w-4" aria-hidden="true" />
          Use Browser Geolocation
        </button>

        {geoError && (
          <p role="alert" className="text-xs text-bw-warning mb-3">
            {geoError}
          </p>
        )}

        <form onSubmit={handleSearch} className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <label htmlFor="city-search-input" className="sr-only">
              Search monitoring city
            </label>
            <Search
              className="h-4 w-4 text-bw-muted absolute left-3 top-1/2 -translate-y-1/2"
              aria-hidden="true"
            />
            <input
              id="city-search-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search city (e.g. Pune, Delhi, Jaipur)..."
              className="w-full rounded-xl bg-bw-bg border border-white/10 pl-9 pr-3 py-2.5 text-sm text-bw-text placeholder:text-bw-muted focus:outline-none focus:border-bw-accent/50"
            />
          </div>
          <button
            type="submit"
            disabled={searching}
            className="px-4 py-2.5 rounded-xl bg-bw-accent text-bw-bg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
          >
            {searching ? "..." : "Search"}
          </button>
        </form>

        {searchErr && <p className="text-xs text-bw-muted mb-3">{searchErr}</p>}

        {results.length > 0 && (
          <div className="mb-4 max-h-48 overflow-y-auto space-y-1.5">
            {results.map((r) => (
              <button
                key={r.id}
                onClick={() => {
                  setLocation({
                    name: r.label,
                    latitude: r.latitude,
                    longitude: r.longitude,
                    source: "search",
                  });
                  onClose();
                }}
                className="w-full text-left px-3 py-2 rounded-lg bg-bw-card/60 hover:bg-bw-card border border-white/5 flex items-center justify-between text-sm"
              >
                <span className="text-bw-text">{r.label}</span>
                <span className="font-mono text-xs text-bw-muted">
                  {r.latitude.toFixed(2)}, {r.longitude.toFixed(2)}
                </span>
              </button>
            ))}
          </div>
        )}

        <div>
          <p className="text-[11px] uppercase tracking-wider text-bw-muted mb-2">
            Quick Indian Cities
          </p>
          <div className="grid grid-cols-2 gap-2">
            {PRESET_CITIES.map((city) => (
              <button
                key={city.name}
                onClick={() => {
                  setLocation(city);
                  onClose();
                }}
                className={`px-3 py-2 rounded-lg border text-left text-xs font-medium transition-colors ${
                  location.name.startsWith(city.name)
                    ? "border-bw-accent/50 bg-bw-accent/10 text-bw-accent"
                    : "border-white/10 bg-bw-card/50 text-bw-text hover:bg-bw-card"
                }`}
              >
                {city.name}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { location, aqiStandard, setAqiStandard, user, logout } = useBreatheWise();
  const [locOpen, setLocOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-bw-bg text-bw-text bw-ambient-grid flex flex-col">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2 focus:rounded-lg focus:bg-bw-accent focus:text-bw-bg focus:text-xs focus:font-semibold"
      >
        Skip to main content
      </a>
      <header className="sticky top-0 z-40 border-b border-white/[0.07] bg-bw-bg/85 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2.5 shrink-0">
              <BrandMark className="h-8 w-8" />
              <div className="leading-tight">
                <span className="font-semibold tracking-tight text-bw-text block text-sm">
                  BreatheWise
                </span>
                <span className="text-[10px] text-bw-muted hidden sm:block">
                  Urban Air Intelligence
                </span>
              </div>
            </Link>

            <nav aria-label="Primary navigation" className="hidden lg:flex items-center gap-1">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      active
                        ? "bg-bw-accent/15 text-bw-accent border border-bw-accent/25"
                        : "text-bw-muted hover:text-bw-text hover:bg-white/5"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setLocOpen(true)}
              aria-label={`Change monitoring location (${location.name})`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bw-secondary border border-white/10 hover:border-bw-accent/40 text-xs text-bw-text transition-colors"
            >
              <MapPin className="h-3.5 w-3.5 text-bw-accent" aria-hidden="true" />
              <span className="max-w-[120px] truncate">{location.name}</span>
              <ChevronDown className="h-3 w-3 text-bw-muted" aria-hidden="true" />
            </button>

            <div
              role="group"
              aria-label="AQI Methodology Standard"
              className="hidden sm:flex items-center rounded-lg bg-bw-secondary border border-white/10 p-0.5 text-[11px]"
              title="Switch AQI Methodology Standard"
            >
              <button
                type="button"
                aria-pressed={aqiStandard === "indian_naqi"}
                onClick={() => setAqiStandard("indian_naqi")}
                className={`px-2 py-1 rounded-md font-medium transition-colors ${
                  aqiStandard === "indian_naqi"
                    ? "bg-bw-accent text-bw-bg"
                    : "text-bw-muted hover:text-bw-text"
                }`}
              >
                IN NAQI
              </button>
              <button
                type="button"
                aria-pressed={aqiStandard === "us_aqi"}
                onClick={() => setAqiStandard("us_aqi")}
                className={`px-2 py-1 rounded-md font-medium transition-colors ${
                  aqiStandard === "us_aqi"
                    ? "bg-bw-accent text-bw-bg"
                    : "text-bw-muted hover:text-bw-text"
                }`}
              >
                US AQI
              </button>
            </div>

            {user ? (
              <div className="hidden sm:flex items-center gap-2">
                <Link
                  href="/profile"
                  className="px-2.5 py-1.5 rounded-lg bg-bw-card border border-white/10 text-xs font-medium text-bw-text hover:border-bw-teal/40"
                >
                  {user.name.split(" ")[0]}
                </Link>
                <button
                  type="button"
                  onClick={logout}
                  className="p-1.5 rounded-lg text-bw-muted hover:text-bw-danger hover:bg-white/5"
                  title="Sign out"
                  aria-label="Sign out"
                >
                  <LogOut className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            ) : (
              <Link
                href="/auth"
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bw-accent text-bw-bg text-xs font-semibold hover:opacity-90"
              >
                Sign In
              </Link>
            )}

            <button
              type="button"
              onClick={() => setMobileNavOpen(!mobileNavOpen)}
              className="lg:hidden p-2 rounded-lg text-bw-muted hover:text-bw-text hover:bg-white/5"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileNavOpen}
              aria-controls="mobile-navigation"
            >
              {mobileNavOpen ? (
                <X className="h-5 w-5" aria-hidden="true" />
              ) : (
                <Menu className="h-5 w-5" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {mobileNavOpen && (
          <nav
            id="mobile-navigation"
            aria-label="Mobile navigation"
            className="lg:hidden border-t border-white/10 bg-bw-secondary px-4 py-3 space-y-1"
          >
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setMobileNavOpen(false)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                    active
                      ? "bg-bw-accent/15 text-bw-accent"
                      : "text-bw-muted hover:text-bw-text"
                  }`}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
            <div className="pt-2 border-t border-white/10 flex items-center justify-between">
              <div
                role="group"
                aria-label="AQI Methodology Standard"
                className="flex items-center gap-1 text-xs"
              >
                <button
                  type="button"
                  aria-pressed={aqiStandard === "indian_naqi"}
                  onClick={() => setAqiStandard("indian_naqi")}
                  className={`px-2.5 py-1 rounded ${
                    aqiStandard === "indian_naqi"
                      ? "bg-bw-accent text-bw-bg font-medium"
                      : "text-bw-muted"
                  }`}
                >
                  IN NAQI
                </button>
                <button
                  type="button"
                  aria-pressed={aqiStandard === "us_aqi"}
                  onClick={() => setAqiStandard("us_aqi")}
                  className={`px-2.5 py-1 rounded ${
                    aqiStandard === "us_aqi"
                      ? "bg-bw-accent text-bw-bg font-medium"
                      : "text-bw-muted"
                  }`}
                >
                  US AQI
                </button>
              </div>
              {user ? (
                <button
                  type="button"
                  onClick={logout}
                  className="text-xs text-bw-danger font-medium"
                >
                  Sign Out ({user.name.split(" ")[0]})
                </button>
              ) : (
                <Link
                  href="/auth"
                  onClick={() => setMobileNavOpen(false)}
                  className="text-xs text-bw-accent font-semibold"
                >
                  Sign In / Register
                </Link>
              )}
            </div>
          </nav>
        )}
      </header>

      <main
        id="main-content"
        className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8"
      >
        {children}
      </main>

      <footer className="border-t border-white/[0.06] bg-bw-secondary/60 py-5 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-bw-muted">
          <div className="flex items-center gap-2">
            <Compass className="h-3.5 w-3.5 text-bw-teal" />
            <span>
              BreatheWise — Environmental data via Open-Meteo; AI reasoning via Google Gemini.
            </span>
          </div>
          <span>General environmental guidance only — not medical diagnosis.</span>
        </div>
      </footer>

      <LocationPickerModal open={locOpen} onClose={() => setLocOpen(false)} />
    </div>
  );
}
