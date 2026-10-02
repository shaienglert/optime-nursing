"use client";
import { useEffect } from "react";
import { reportClientIncident } from "@/lib/user-incidents";

export function UserIncidentMonitor() {
  useEffect(() => {
    const error = () => reportClientIncident("CLIENT_RUNTIME_ERROR");
    const rejection = () => reportClientIncident("UNHANDLED_REJECTION");
    window.addEventListener("error", error);
    window.addEventListener("unhandledrejection", rejection);
    return () => {
      window.removeEventListener("error", error);
      window.removeEventListener("unhandledrejection", rejection);
    };
  }, []);
  return null;
}
