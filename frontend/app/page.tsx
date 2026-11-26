"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  Bot,
  CalendarClock,
  CheckCircle2,
  Droplets,
  Home,
  Leaf,
  MapPin,
  ShieldCheck,
  TrendingUp,
  Wind,
} from "lucide-react";
import { BrandMark } from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { getActiveIndexInfo, getBadgeClasses } from "@/lib/aqi";

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-40px" },
  transition: { duration: 0.45 },
};

export default function LandingPage() {
  const { airQuality, weather, envLoading, envError, aqiStandard, location } =
    useBreatheWise();
  const activeIdx = getActiveIndexInfo(airQuality, aqiStandard);

  return (
    <div className="min-h-screen bg-bw-bg text-bw-text bw-ambient-grid">
      {/* 1. Navbar */}
      <header className="sticky top-0 z-40 border-b border-white/[0.07] bg-bw-bg/85 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <BrandMark className="h-8 w-8" />
            <div>
              <span className="font-semibold tracking-tight text-sm block">
                BreatheWise
              </span>
              <span className="text-[10px] text-bw-muted hidden sm:block">
                Breathe Smarter. Live Better.
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-7 text-xs font-medium text-bw-muted">
            <a href="#live-preview" className="hover:text-bw-text transition-colors">
              Live Telemetry
            </a>
            <a href="#how-it-works" className="hover:text-bw-text transition-colors">
              How It Works
            </a>
            <a href="#advisor-preview" className="hover:text-bw-text transition-colors">
              AI Advisor
            </a>
            <a href="#indoor" className="hover:text-bw-text transition-colors">
              Indoor & Lifestyle
            </a>
            <a href="#impact" className="hover:text-bw-text transition-colors">
              Impact
            </a>
          </nav>

          <div className="flex items-center gap-2.5">
            <Link
              href="/auth"
              className="px-3.5 py-2 rounded-lg text-xs font-medium text-bw-muted hover:text-bw-text transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-bw-accent text-bw-bg text-xs font-semibold hover:opacity-90 transition-opacity"
            >
              Explore Your Air
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pt-14 pb-16 sm:pt-20 sm:pb-24">
        <div className="grid lg:grid-cols-12 gap-10 items-center">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="lg:col-span-7 space-y-6"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-bw-secondary border border-white/10 text-xs text-bw-teal font-medium">
              <MapPin className="h-3.5 w-3.5" />
              <span>Initial Focus: Pune & Indian Urban Corridors</span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight leading-[1.12] text-bw-text">
              The air around you matters. Know what to do.
            </h1>

            <p className="text-base sm:text-lg text-bw-muted max-w-2xl leading-relaxed">
              BreatheWise transforms live atmospheric and weather telemetry into
              clear daily decisions for families, children, elderly parents, and
              urban commuters navigating winter smog.
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-bw-accent text-bw-bg text-sm font-semibold hover:opacity-90 transition-opacity"
              >
                Explore Your Air
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-bw-secondary border border-white/10 text-sm font-medium text-bw-text hover:border-white/20 transition-colors"
              >
                How It Works
              </a>
            </div>

            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/[0.07] max-w-xl">
              <div>
                <p className="text-xs text-bw-muted">Index Standards</p>
                <p className="text-sm font-semibold text-bw-text mt-0.5">
                  CPCB NAQI & US EPA
                </p>
              </div>
              <div>
                <p className="text-xs text-bw-muted">Telemetry Source</p>
                <p className="text-sm font-semibold text-bw-text mt-0.5">
                  Open-Meteo CAMS
                </p>
              </div>
              <div>
                <p className="text-xs text-bw-muted">AI Reasoning</p>
                <p className="text-sm font-semibold text-bw-text mt-0.5">
                  Google Gemini 2.5
                </p>
              </div>
            </div>
          </motion.div>

          {/* 3. Live Air Quality Preview */}
          <motion.div
            id="live-preview"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.1 }}
            className="lg:col-span-5"
          >
            <div className="bw-surface rounded-2xl p-6 shadow-glass space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-bw-teal font-medium">
                    Verified Live Reading
                  </span>
                  <h2 className="text-base font-semibold text-bw-text mt-0.5">
                    {airQuality?.location.name || location.name}
                  </h2>
                </div>
                <span
                  className={`px-2.5 py-1 rounded-md border text-xs font-medium ${getBadgeClasses(
                    activeIdx.color
                  )}`}
                >
                  {envLoading ? "Loading..." : activeIdx.category}
                </span>
              </div>

              {envError ? (
                <div className="rounded-xl border border-bw-danger/30 bg-bw-danger/10 p-4 text-xs text-bw-muted">
                  <p className="font-semibold text-bw-danger mb-1">
                    Live telemetry unavailable
                  </p>
                  <p>{envError}</p>
                </div>
              ) : (
                <>
                  <div className="flex items-end justify-between border-b border-white/[0.07] pb-4">
                    <div>
                      <p className="text-xs text-bw-muted">
                        {activeIdx.methodology}
                      </p>
                      <p className="font-mono text-4xl font-semibold text-bw-text mt-1">
                        {envLoading ? "—" : activeIdx.value ?? "N/A"}
                      </p>
                    </div>
                    <div className="text-right text-xs text-bw-muted space-y-1">
                      <p className="flex items-center justify-end gap-1.5 text-bw-text">
                        <Wind className="h-3.5 w-3.5 text-bw-teal" />
                        {weather?.wind.speed ?? "—"} {weather?.wind.speed_unit || "km/h"}
                      </p>
                      <p className="flex items-center justify-end gap-1.5">
                        <Droplets className="h-3.5 w-3.5 text-bw-accent" />
                        {weather?.humidity.value ?? "—"}% RH ·{" "}
                        {weather?.temperature.value ?? "—"}°C
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    {[
                      { label: "PM2.5", val: airQuality?.pollutants.pm2_5.value },
                      { label: "PM10", val: airQuality?.pollutants.pm10.value },
                      {
                        label: "NO2",
                        val: airQuality?.pollutants.nitrogen_dioxide.value,
                      },
                      { label: "O3", val: airQuality?.pollutants.ozone.value },
                    ].map((p) => (
                      <div
                        key={p.label}
                        className="rounded-lg bg-bw-secondary border border-white/5 p-2.5"
                      >
                        <span className="text-[11px] text-bw-muted block">
                          {p.label}
                        </span>
                        <span className="font-mono text-sm font-semibold text-bw-text">
                          {p.val !== null && p.val !== undefined ? p.val : "—"}
                        </span>
                        <span className="text-[10px] text-bw-muted ml-1">
                          μg/m³
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-bw-muted pt-1">
                    <span>Source: Open-Meteo Air Quality & Weather</span>
                    <span className="font-mono">
                      {airQuality?.timestamp || "Checking..."}
                    </span>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        </div>
      </section>

      {/* 4. How BreatheWise Works */}
      <section
        id="how-it-works"
        className="border-t border-white/[0.06] bg-bw-secondary/50 py-16 sm:py-20"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <motion.div {...fadeUp} className="max-w-2xl mb-10">
            <span className="text-xs uppercase tracking-wider text-bw-accent font-medium">
              How It Works
            </span>
            <h2 className="text-2xl sm:text-3xl font-semibold mt-2">
              Grounded intelligence from atmospheric data to daily action
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Activity,
                title: "1. Measure & Standardize",
                body: "Fetches hourly PM2.5, PM10, NO2, O3, CO, SO2 and weather from Open-Meteo, cleanly separating CPCB Indian NAQI from US EPA AQI.",
              },
              {
                icon: Bot,
                title: "2. Contextualize with Gemini AI",
                body: "Combines verified ambient conditions with your household profile — children, elderly parents, purifier access, and commute style.",
              },
              {
                icon: CalendarClock,
                title: "3. Act & Track Exposure",
                body: "Turns forecasts into hour-by-hour outdoor windows, indoor ventilation checklists, and factor-backed sustainable swaps.",
              },
            ].map((step) => {
              const Icon = step.icon;
              return (
                <motion.div
                  key={step.title}
                  {...fadeUp}
                  className="bw-surface rounded-xl p-6 space-y-3"
                >
                  <div className="h-10 w-10 rounded-lg bg-bw-accent/10 border border-bw-accent/25 flex items-center justify-center text-bw-accent">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold">{step.title}</h3>
                  <p className="text-sm text-bw-muted leading-relaxed">
                    {step.body}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 5. AI Air Advisor Preview */}
      <section id="advisor-preview" className="py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 grid lg:grid-cols-12 gap-8 items-center">
          <motion.div {...fadeUp} className="lg:col-span-5 space-y-4">
            <span className="text-xs uppercase tracking-wider text-bw-teal font-medium">
              AI Air Advisor
            </span>
            <h2 className="text-2xl sm:text-3xl font-semibold">
              Ask practical questions, get structured answers
            </h2>
            <p className="text-sm text-bw-muted leading-relaxed">
              Instead of vague chat replies, BreatheWise validates Gemini
              outputs with Pydantic schemas into risk levels, concrete actions,
              and clear reasons tied directly to verified pollutant readings.
            </p>
            <Link
              href="/advisor"
              className="inline-flex items-center gap-2 text-sm font-semibold text-bw-accent hover:underline"
            >
              Open AI Air Advisor <ArrowRight className="h-4 w-4" />
            </Link>
          </motion.div>

          <motion.div {...fadeUp} className="lg:col-span-7 bw-surface rounded-2xl p-6 space-y-4">
            <div className="rounded-xl bg-bw-secondary border border-white/10 p-4 text-sm text-bw-text">
              <span className="text-xs text-bw-muted block mb-1">
                Example Household Question
              </span>
              &ldquo;Is it safe for my father to take his 7:00 AM walk today, or should we wait?&rdquo;
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="rounded-xl bg-bw-bg/80 border border-white/10 p-4 space-y-1.5">
                <span className="text-[11px] font-medium text-bw-warning uppercase">
                  High Priority Action
                </span>
                <p className="text-sm font-semibold">Delay outdoor walk until afternoon dispersion</p>
                <p className="text-xs text-bw-muted">
                  Morning temperature inversions trap PM2.5 near street level; warm midday mixing typically lowers surface concentration.
                </p>
              </div>
              <div className="rounded-xl bg-bw-bg/80 border border-white/10 p-4 space-y-1.5">
                <span className="text-[11px] font-medium text-bw-teal uppercase">
                  Indoor Alternative
                </span>
                <p className="text-sm font-semibold">Gentle indoor mobility + HEPA filtration</p>
                <p className="text-xs text-bw-muted">
                  Keep traffic-facing windows closed during peak morning commute and verify hourly trends before stepping out.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 6 & 7. Indoor Air Quality + Sustainable Lifestyle */}
      <section
        id="indoor"
        className="border-t border-white/[0.06] bg-bw-secondary/50 py-16 sm:py-20"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 grid md:grid-cols-2 gap-8">
          <motion.div {...fadeUp} className="bw-surface rounded-2xl p-7 space-y-4">
            <div className="flex items-center gap-2.5 text-bw-teal">
              <Home className="h-5 w-5" />
              <span className="text-xs uppercase tracking-wider font-semibold">
                Indoor Air Quality Guide
              </span>
            </div>
            <h3 className="text-xl font-semibold">
              Know when to open windows and when to seal & filter
            </h3>
            <p className="text-sm text-bw-muted leading-relaxed">
              Outdoor pollution enters homes fast during winter smog, while cooking
              and incense add indoor particulates. Get room-by-room checklists
              grounded in outdoor readings without claiming unmeasured indoor sensors.
            </p>
            <ul className="space-y-2 text-xs text-bw-text">
              {[
                "Outdoor-triggered cross-ventilation verdicts",
                "Kitchen exhaust & damp-mopping source control",
                "Room-by-room HEPA & dust checklist",
              ].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-bw-teal shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <Link
              href="/indoor"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-bw-teal hover:underline pt-1"
            >
              View Indoor Guide <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </motion.div>

          <motion.div {...fadeUp} className="bw-surface rounded-2xl p-7 space-y-4">
            <div className="flex items-center gap-2.5 text-bw-accent">
              <Leaf className="h-5 w-5" />
              <span className="text-xs uppercase tracking-wider font-semibold">
                Sustainable Lifestyle
              </span>
            </div>
            <h3 className="text-xl font-semibold">
              Practical urban swaps that cut local smog & emissions
            </h3>
            <p className="text-sm text-bw-muted leading-relaxed">
              Explore six actionable categories — transportation, energy,
              household practices, shopping, waste, and community — rated by
              practical difficulty and real pollution relevance.
            </p>
            <ul className="space-y-2 text-xs text-bw-text">
              {[
                "Metro, bus & non-motorized short-trip shifts",
                "Zero-burning society waste & composting alternatives",
                "Transparent difficulty & qualitative benefit context",
              ].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-bw-accent shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <Link
              href="/sustainable"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-bw-accent hover:underline pt-1"
            >
              Explore Alternatives <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* 8. Environmental Impact Section */}
      <section id="impact" className="py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 bw-surface rounded-2xl p-8 sm:p-10 grid lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-7 space-y-4">
            <div className="inline-flex items-center gap-2 text-xs text-bw-accent font-medium">
              <TrendingUp className="h-4 w-4" />
              <span>Personal Impact Tracker</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-semibold">
              Honest sustainability tracking without inflated numbers
            </h2>
            <p className="text-sm text-bw-muted leading-relaxed">
              Log public transit commutes, walking or cycling kilometers, and
              energy savings. Quantitative CO2e estimates use documented DEFRA and
              India CEA grid factors, clearly separated from measured air exposure.
            </p>
          </div>
          <div className="lg:col-span-5 grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-bw-secondary border border-white/10 p-4">
              <p className="text-xs text-bw-muted">Car-to-Walk Factor</p>
              <p className="font-mono text-lg font-semibold text-bw-accent mt-1">
                0.171 kg
              </p>
              <p className="text-[11px] text-bw-muted mt-0.5">CO2e / km (est.)</p>
            </div>
            <div className="rounded-xl bg-bw-secondary border border-white/10 p-4">
              <p className="text-xs text-bw-muted">India Grid Factor</p>
              <p className="font-mono text-lg font-semibold text-bw-teal mt-1">
                0.716 kg
              </p>
              <p className="text-[11px] text-bw-muted mt-0.5">CO2 / kWh (CEA)</p>
            </div>
            <div className="col-span-2 rounded-xl bg-bw-secondary border border-white/10 p-4 flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 text-bw-teal shrink-0" />
              <p className="text-xs text-bw-muted">
                Every logged action persists to MongoDB Atlas with explicit calculation assumptions.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 9. CTA Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-20">
        <div className="rounded-2xl border border-bw-accent/25 bg-gradient-to-br from-bw-card to-bw-secondary p-8 sm:p-12 text-center space-y-5">
          <h2 className="text-2xl sm:text-3xl font-semibold">
            Ready to plan safer, cleaner days for your household?
          </h2>
          <p className="text-sm text-bw-muted max-w-xl mx-auto">
            Check live local air quality, build your family care profile, and get
            grounded daily schedules in under a minute.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-bw-accent text-bw-bg text-sm font-semibold hover:opacity-90"
            >
              Explore Your Air
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/auth"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-bw-bg border border-white/10 text-sm font-medium text-bw-text hover:border-white/25"
            >
              Create Family Account
            </Link>
          </div>
        </div>
      </section>

      {/* 10. Footer */}
      <footer className="border-t border-white/[0.07] bg-bw-secondary/70 py-8 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs text-bw-muted">
          <div className="flex items-center gap-2.5">
            <BrandMark className="h-6 w-6" />
            <span>BreatheWise — Breathe Smarter. Live Better.</span>
          </div>
          <div className="flex flex-wrap gap-5">
            <Link href="/dashboard" className="hover:text-bw-text">
              Dashboard
            </Link>
            <Link href="/advisor" className="hover:text-bw-text">
              AI Advisor
            </Link>
            <Link href="/routine" className="hover:text-bw-text">
              Smart Routine
            </Link>
            <Link href="/indoor" className="hover:text-bw-text">
              Indoor Guide
            </Link>
            <Link href="/impact" className="hover:text-bw-text">
              Impact Tracker
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
