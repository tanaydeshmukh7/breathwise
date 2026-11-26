"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api } from "@/lib/api";
import { DEFAULT_LOCATION } from "@/lib/constants";
import {
  AirQualityForecastResponse,
  AirQualityResponse,
  AqiStandard,
  HouseholdContext,
  LocationState,
  UserProfile,
  WeatherResponse,
} from "@/types";

interface BreatheWiseContextValue {
  token: string | null;
  user: UserProfile | null;
  authLoading: boolean;
  setSession: (token: string, user: UserProfile) => void;
  logout: () => void;
  location: LocationState;
  setLocation: (loc: LocationState) => void;
  detectGeolocation: () => Promise<void>;
  geoError: string | null;
  aqiStandard: AqiStandard;
  setAqiStandard: (std: AqiStandard) => void;
  householdContext: HouseholdContext;
  setHouseholdContext: (ctx: HouseholdContext) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  availableModels: string[];
  airQuality: AirQualityResponse | null;
  forecast: AirQualityForecastResponse | null;
  weather: WeatherResponse | null;
  envLoading: boolean;
  envError: string | null;
  refreshEnvironment: () => Promise<void>;
}

const BreatheWiseContext = createContext<BreatheWiseContextValue | undefined>(
  undefined
);

const TOKEN_KEY = "bw_token";
const LOCATION_KEY = "bw_location";
const STANDARD_KEY = "bw_aqi_standard";

export function BreatheWiseProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [location, setLocationState] = useState<LocationState>(DEFAULT_LOCATION);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [aqiStandard, setAqiStandardState] = useState<AqiStandard>("indian_naqi");
  const [householdContext, setHouseholdContext] =
    useState<HouseholdContext>("general");

  const [selectedModel, setSelectedModel] = useState("gemini-2.5-flash");
  const [availableModels, setAvailableModels] = useState<string[]>([
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
  ]);

  const [airQuality, setAirQuality] = useState<AirQualityResponse | null>(null);
  const [forecast, setForecast] = useState<AirQualityForecastResponse | null>(
    null
  );
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [envLoading, setEnvLoading] = useState(true);
  const [envError, setEnvError] = useState<string | null>(null);

  useEffect(() => {
    const savedLoc = localStorage.getItem(LOCATION_KEY);
    if (savedLoc) {
      try {
        const parsed = JSON.parse(savedLoc) as LocationState;
        if (parsed?.latitude && parsed?.longitude) {
          setLocationState(parsed);
        }
      } catch {
        // ignore invalid stored location
      }
    }
    const savedStd = localStorage.getItem(STANDARD_KEY) as AqiStandard | null;
    if (savedStd === "indian_naqi" || savedStd === "us_aqi") {
      setAqiStandardState(savedStd);
    }
    const savedToken = localStorage.getItem(TOKEN_KEY);
    if (savedToken) {
      setToken(savedToken);
      api
        .getMe(savedToken)
        .then((u) => {
          setUser(u);
          if (u.preferred_aqi_standard) {
            setAqiStandardState(u.preferred_aqi_standard);
          }
        })
        .catch(() => {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
          setUser(null);
        })
        .finally(() => setAuthLoading(false));
    } else {
      setAuthLoading(false);
    }

    api
      .listModels()
      .then((res) => {
        if (res.active_model) setSelectedModel(res.active_model);
        if (res.available_models?.length) setAvailableModels(res.available_models);
      })
      .catch(() => {
        // fallback list already initialized
      });
  }, []);

  const setLocation = useCallback((loc: LocationState) => {
    setLocationState(loc);
    setGeoError(null);
    localStorage.setItem(LOCATION_KEY, JSON.stringify(loc));
  }, []);

  const setAqiStandard = useCallback((std: AqiStandard) => {
    setAqiStandardState(std);
    localStorage.setItem(STANDARD_KEY, std);
  }, []);

  const setSession = useCallback((newToken: string, newUser: UserProfile) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    setUser(newUser);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const refreshEnvironment = useCallback(async () => {
    setEnvLoading(true);
    setEnvError(null);
    try {
      const [aqRes, fcRes, wxRes] = await Promise.all([
        api.getCurrentAqi(location.latitude, location.longitude, location.name),
        api.getAqiForecast(location.latitude, location.longitude, 36, 1),
        api.getCurrentWeather(location.latitude, location.longitude),
      ]);
      setAirQuality(aqRes);
      setForecast(fcRes);
      setWeather(wxRes);
    } catch (err) {
      setEnvError(
        err instanceof Error
          ? err.message
          : "Unable to load live environmental telemetry."
      );
      setAirQuality(null);
      setForecast(null);
      setWeather(null);
    } finally {
      setEnvLoading(false);
    }
  }, [location.latitude, location.longitude, location.name]);

  useEffect(() => {
    refreshEnvironment();
  }, [refreshEnvironment]);

  const detectGeolocation = useCallback(async () => {
    if (typeof window === "undefined" || !navigator.geolocation) {
      setGeoError("Browser geolocation is not supported on this device.");
      return;
    }
    setGeoError(null);
    await new Promise<void>((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = Number(pos.coords.latitude.toFixed(4));
          const lon = Number(pos.coords.longitude.toFixed(4));
          setLocation({
            name: `Current Location (${lat}, ${lon})`,
            latitude: lat,
            longitude: lon,
            source: "geolocation",
          });
          resolve();
        },
        (err) => {
          setGeoError(
            err.code === 1
              ? "Location permission denied. Search or select a city manually."
              : "Could not determine your GPS coordinates. Please search a city."
          );
          resolve();
        },
        { enableHighAccuracy: false, timeout: 8000 }
      );
    });
  }, [setLocation]);

  return (
    <BreatheWiseContext.Provider
      value={{
        token,
        user,
        authLoading,
        setSession,
        logout,
        location,
        setLocation,
        detectGeolocation,
        geoError,
        aqiStandard,
        setAqiStandard,
        householdContext,
        setHouseholdContext,
        selectedModel,
        setSelectedModel,
        availableModels,
        airQuality,
        forecast,
        weather,
        envLoading,
        envError,
        refreshEnvironment,
      }}
    >
      {children}
    </BreatheWiseContext.Provider>
  );
}

export function useBreatheWise() {
  const ctx = useContext(BreatheWiseContext);
  if (!ctx) {
    throw new Error("useBreatheWise must be used inside BreatheWiseProvider");
  }
  return ctx;
}
