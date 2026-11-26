"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Plus, ShieldCheck, Trash2, User, Users } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import {
  AuthPromptCard,
  LoadingCard,
  UnavailableBanner,
} from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { api } from "@/lib/api";
import { AqiStandard, FamilyMember } from "@/types";

export default function ProfilePage() {
  const { token, user, location, setAqiStandard, setSession } = useBreatheWise();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [city, setCity] = useState(location.name);
  const [ageGroup, setAgeGroup] = useState("adult");
  const [occupation, setOccupation] = useState("working_professional");
  const [transport, setTransport] = useState("mixed");
  const [exercise, setExercise] = useState("morning_outdoor");
  const [householdSize, setHouseholdSize] = useState(3);
  const [hasPurifier, setHasPurifier] = useState(false);
  const [std, setStd] = useState<AqiStandard>("indian_naqi");
  const [personalPrefs, setPersonalPrefs] = useState("");

  const [family, setFamily] = useState<FamilyMember[]>([]);
  const [memberName, setMemberName] = useState("");
  const [memberType, setMemberType] = useState<"adult" | "child" | "elderly">(
    "child"
  );
  const [memberNotes, setMemberNotes] = useState("");
  const [memberMinutes, setMemberMinutes] = useState("45");

  const loadProfile = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getProfile(token);
      setName(res.user.name);
      setCity(res.user.city);
      setAgeGroup(res.user.age_group || "adult");
      setOccupation(res.user.occupation || "working_professional");
      setTransport(res.user.transport_preference || "mixed");
      setExercise(res.user.exercise_habit || "morning_outdoor");
      setHouseholdSize(res.user.household_size || 3);
      setHasPurifier(res.user.has_air_purifier);
      setStd(res.user.preferred_aqi_standard || "indian_naqi");
      setPersonalPrefs(res.preferences.personal_preferences || "");
      setFamily(res.family_profiles || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const res = await api.updateProfile(
        {
          name,
          city,
          age_group: ageGroup,
          occupation,
          transport_preference: transport,
          exercise_habit: exercise,
          household_size: Number(householdSize),
          has_air_purifier: hasPurifier,
          preferred_aqi_standard: std,
          personal_preferences: personalPrefs,
        },
        token
      );
      setSession(token, res.user);
      setAqiStandard(std);
      setMessage("Profile and household preferences saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !memberName.trim()) return;
    try {
      const res = await api.addFamilyMember(
        {
          name: memberName.trim(),
          member_type: memberType,
          sensitivity_notes: memberNotes.trim(),
          daily_outdoor_minutes: Number(memberMinutes) || 30,
        },
        token
      );
      setFamily((prev) => [res.family_member, ...prev]);
      setMemberName("");
      setMemberNotes("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not add family profile."
      );
    }
  };

  const handleDeleteMember = async (id: string) => {
    if (!token) return;
    try {
      await api.deleteFamilyMember(id, token);
      setFamily((prev) => prev.filter((m) => m.id !== id));
    } catch {
      // ignore
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2.5">
            <User className="h-6 w-6 text-bw-accent" />
            User Profile & Family Mode
          </h1>
          <p className="text-sm text-bw-muted mt-1">
            Configure lifestyle preferences and caregiver profiles for adults,
            children, and elderly family members
          </p>
        </div>

        {!token ? (
          <AuthPromptCard
            title="Sign in to manage your Household & Family Profiles"
            description="Save your air purifier setup, commute preferences, and caregiver profiles so BreatheWise AI tailors every daily routine to your family."
            ctaLabel="Sign In / Register"
          />
        ) : loading && !user ? (
          <LoadingCard lines={6} />
        ) : (
          <>
            {error && <UnavailableBanner title="Profile Error" message={error} />}
            {message && (
              <div
                role="status"
                aria-live="polite"
                className="rounded-xl border border-bw-teal/30 bg-bw-teal/10 px-4 py-2.5 text-xs text-bw-teal"
              >
                {message}
              </div>
            )}

            <div className="grid lg:grid-cols-12 gap-6">
              {/* Main Profile Form */}
              <form
                onSubmit={handleSaveProfile}
                className="lg:col-span-7 bw-surface rounded-2xl p-6 space-y-4"
              >
                <h2 className="text-base font-semibold">Personal & Lifestyle</h2>

                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label
                      htmlFor="profile-full-name"
                      className="text-xs text-bw-muted block mb-1"
                    >
                      Full Name
                    </label>
                    <input
                      id="profile-full-name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="profile-home-city"
                      className="text-xs text-bw-muted block mb-1"
                    >
                      Home City
                    </label>
                    <input
                      id="profile-home-city"
                      type="text"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="profile-age-group"
                      className="text-xs text-bw-muted block mb-1"
                    >
                      Age Group
                    </label>
                    <select
                      id="profile-age-group"
                      value={ageGroup}
                      onChange={(e) => setAgeGroup(e.target.value)}
                      className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-sm"
                    >
                      <option value="young_adult">Young Adult / Student</option>
                      <option value="adult">Adult</option>
                      <option value="senior">Senior / Elderly</option>
                    </select>
                  </div>
                  <div>
                    <label
                      htmlFor="profile-occupation"
                      className="text-xs text-bw-muted block mb-1"
                    >
                      Occupation
                    </label>
                    <input
                      id="profile-occupation"
                      type="text"
                      value={occupation}
                      onChange={(e) => setOccupation(e.target.value)}
                      className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="profile-transport"
                      className="text-xs text-bw-muted block mb-1"
                    >
                      Primary Transport
                    </label>
                    <select
                      id="profile-transport"
                      value={transport}
                      onChange={(e) => setTransport(e.target.value)}
                      className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-sm"
                    >
                      <option value="public_transit">Metro / Bus</option>
                      <option value="walk_cycle">Walk / Cycle</option>
                      <option value="two_wheeler">Two-Wheeler</option>
                      <option value="car">Car / Cab</option>
                      <option value="mixed">Mixed</option>
                    </select>
                  </div>
                  <div>
                    <label
                      htmlFor="profile-exercise"
                      className="text-xs text-bw-muted block mb-1"
                    >
                      Exercise Habit
                    </label>
                    <select
                      id="profile-exercise"
                      value={exercise}
                      onChange={(e) => setExercise(e.target.value)}
                      className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-sm"
                    >
                      <option value="morning_outdoor">Morning Outdoor</option>
                      <option value="evening_outdoor">Evening Outdoor</option>
                      <option value="indoor_gym">Indoor / Home Workout</option>
                      <option value="light_walks">Light Walks</option>
                    </select>
                  </div>
                  <div>
                    <label
                      htmlFor="profile-household-size"
                      className="text-xs text-bw-muted block mb-1"
                    >
                      Household Size
                    </label>
                    <input
                      id="profile-household-size"
                      type="number"
                      min={1}
                      max={20}
                      value={householdSize}
                      onChange={(e) => setHouseholdSize(Number(e.target.value))}
                      className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-sm font-mono"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="profile-aqi-standard"
                      className="text-xs text-bw-muted block mb-1"
                    >
                      Preferred AQI Standard
                    </label>
                    <select
                      id="profile-aqi-standard"
                      value={std}
                      onChange={(e) => setStd(e.target.value as AqiStandard)}
                      className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-sm"
                    >
                      <option value="indian_naqi">
                        CPCB Indian National AQI (NAQI)
                      </option>
                      <option value="us_aqi">US EPA AQI</option>
                    </select>
                  </div>
                </div>

                <label className="flex items-center gap-3 text-sm pt-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasPurifier}
                    onChange={(e) => setHasPurifier(e.target.checked)}
                    className="h-4 w-4 accent-[#B7F36B]"
                  />
                  <span>Indoor HEPA air filtration available at home</span>
                </label>

                <div>
                  <label
                    htmlFor="profile-notes"
                    className="text-xs text-bw-muted block mb-1"
                  >
                    Personal Preferences & Notes
                  </label>
                  <textarea
                    id="profile-notes"
                    rows={2}
                    value={personalPrefs}
                    onChange={(e) => setPersonalPrefs(e.target.value)}
                    placeholder="e.g., Prefer morning walks before 8 AM if safe; balcony faces main road"
                    className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-xs"
                  />
                </div>

                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2.5 rounded-xl bg-bw-accent text-bw-bg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save Profile"}
                </button>
              </form>

              {/* Family Profiles Caregiver Panel */}
              <div className="lg:col-span-5 bw-surface rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold flex items-center gap-2">
                    <Users className="h-4 w-4 text-bw-teal" />
                    Family Mode Profiles
                  </h2>
                  <span className="font-mono text-xs text-bw-muted">
                    {family.length} members
                  </span>
                </div>

                <form
                  onSubmit={handleAddMember}
                  className="rounded-xl bg-bw-secondary border border-white/[0.07] p-4 space-y-3"
                >
                  <div className="grid grid-cols-2 gap-2.5">
                    <input
                      type="text"
                      value={memberName}
                      onChange={(e) => setMemberName(e.target.value)}
                      placeholder="Member name"
                      aria-label="Family member name"
                      required
                      className="rounded-lg bg-bw-bg border border-white/10 px-3 py-2 text-xs"
                    />
                    <select
                      value={memberType}
                      onChange={(e) =>
                        setMemberType(
                          e.target.value as "adult" | "child" | "elderly"
                        )
                      }
                      aria-label="Family member group"
                      className="rounded-lg bg-bw-bg border border-white/10 px-3 py-2 text-xs"
                    >
                      <option value="child">Child</option>
                      <option value="elderly">Elderly</option>
                      <option value="adult">Adult</option>
                    </select>
                  </div>
                  <div className="grid grid-cols-3 gap-2.5">
                    <input
                      type="text"
                      value={memberNotes}
                      onChange={(e) => setMemberNotes(e.target.value)}
                      placeholder="Precaution notes (optional)"
                      aria-label="Precaution notes"
                      className="col-span-2 rounded-lg bg-bw-bg border border-white/10 px-3 py-2 text-xs"
                    />
                    <input
                      type="number"
                      min={0}
                      max={720}
                      value={memberMinutes}
                      onChange={(e) => setMemberMinutes(e.target.value)}
                      placeholder="Min/day"
                      aria-label="Typical outdoor minutes per day"
                      className="rounded-lg bg-bw-bg border border-white/10 px-3 py-2 text-xs font-mono"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full inline-flex items-center justify-center gap-1.5 py-2 rounded-lg bg-bw-teal/15 border border-bw-teal/30 text-bw-teal text-xs font-semibold hover:bg-bw-teal/20"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Add Family Member
                  </button>
                </form>

                <div className="space-y-2.5">
                  {family.length === 0 ? (
                    <p className="text-xs text-bw-muted">
                      No family profiles added yet. Add children or elderly
                      relatives to factor their needs into AI advisories.
                    </p>
                  ) : (
                    family.map((m) => (
                      <div
                        key={m.id}
                        className="rounded-xl bg-bw-secondary border border-white/10 p-3.5 flex items-start justify-between gap-2"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{m.name}</span>
                            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-white/5 text-bw-teal">
                              {m.member_type}
                            </span>
                          </div>
                          {m.sensitivity_notes && (
                            <p className="text-xs text-bw-muted mt-1">
                              {m.sensitivity_notes}
                            </p>
                          )}
                          <p className="text-[11px] font-mono text-bw-muted mt-1">
                            Typical outdoor time: {m.daily_outdoor_minutes} min/day
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeleteMember(m.id)}
                          className="p-1.5 rounded-lg text-bw-muted hover:text-bw-danger"
                          title={`Remove ${m.name}`}
                          aria-label={`Remove ${m.name}`}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                <p className="text-[11px] text-bw-muted flex items-start gap-1.5 pt-2 border-t border-white/[0.06]">
                  <ShieldCheck className="h-3.5 w-3.5 text-bw-teal shrink-0 mt-0.5" />
                  BreatheWise provides general environmental precaution guidance,
                  not medical diagnosis or clinical advice.
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
