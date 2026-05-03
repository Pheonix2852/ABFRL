const REQUIRED_ENV_VARS = [
  "EXPO_PUBLIC_FIREBASE_API_KEY",
  "EXPO_PUBLIC_FIREBASE_DATABASE_URL",
  "EXPO_PUBLIC_FIREBASE_PROJECT_ID",
  "EXPO_PUBLIC_RESERVATION_ENDPOINT",
];

export function validateEnv(): void {
  const missing: string[] = [];

  const backendUrl =
    process.env.EXPO_PUBLIC_BACKEND_URL ?? "https://final-yr-proj.onrender.com";
      if (!backendUrl || backendUrl.includes("PLACEHOLDER")) {
    missing.push("EXPO_PUBLIC_BACKEND_URL");
  }

  for (const key of REQUIRED_ENV_VARS) {
    const val = process.env[key];

    if (!val || val.includes("PLACEHOLDER")) {
      missing.push(key);
    }
  }

  if (missing.length > 0) {
    console.warn(
      `[validateEnv] Missing or placeholder env vars: ${missing.join(", ")}. Some features will not work until these are set.`,
    );
  }
}
