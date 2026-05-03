export const BACKEND_BASE_URL =
  process.env.EXPO_PUBLIC_BACKEND_URL ??
  "https://final-yr-proj.onrender.com";

export const CHAT_ENDPOINT = `${BACKEND_BASE_URL}/chat`;

export const RESERVATION_ENDPOINT =
  process.env.EXPO_PUBLIC_RESERVATION_ENDPOINT ??
  `${BACKEND_BASE_URL}/PLACEHOLDER_RESERVATION_PATH`;

export const DEV_USER_ID =
  process.env.EXPO_PUBLIC_DEV_USER_ID ?? "user_priya_001";

export const FIREBASE_CONFIG = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  databaseURL: process.env.EXPO_PUBLIC_FIREBASE_DATABASE_URL,
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID,
};
