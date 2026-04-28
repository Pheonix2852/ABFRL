import { getApps, initializeApp } from "firebase/app";
import { getDatabase, onValue, ref } from "firebase/database";

import { FIREBASE_CONFIG } from "@/constants/config";
import type { ReservationStatus } from "@/types/reservation";

const REQUIRED_FIREBASE_KEYS = [
  FIREBASE_CONFIG.apiKey,
  FIREBASE_CONFIG.authDomain,
  FIREBASE_CONFIG.databaseURL,
  FIREBASE_CONFIG.projectId,
  FIREBASE_CONFIG.storageBucket,
  FIREBASE_CONFIG.messagingSenderId,
  FIREBASE_CONFIG.appId,
];

function hasRealFirebaseConfig(): boolean {
  return REQUIRED_FIREBASE_KEYS.every(
    (value) => typeof value === "string" && !value.includes("PLACEHOLDER"),
  );
}

let databaseInstance: ReturnType<typeof getDatabase> | null = null;

function getDb() {
  if (!hasRealFirebaseConfig()) {
    return null;
  }

  if (databaseInstance) {
    return databaseInstance;
  }

  const app = getApps().length === 0 ? initializeApp(FIREBASE_CONFIG) : getApps()[0];
  databaseInstance = getDatabase(app);
  return databaseInstance;
}

export function subscribeToReservation(
  reservationId: string,
  onUpdate: (status: ReservationStatus, room?: string) => void,
  onError?: (err: Error) => void,
): () => void {
  const db = getDb();

  if (!db) {
    onError?.(
      new Error(
        "Firebase is not fully configured. Fill EXPO_PUBLIC_FIREBASE_* before enabling live listener.",
      ),
    );
    return () => undefined;
  }

  const reservationRef = ref(db, `reservations/${reservationId}`);

  const unsubscribe = onValue(
    reservationRef,
    (snapshot) => {
      const data = snapshot.val() as
        | { status?: ReservationStatus; room?: string }
        | null;

      if (data?.status) {
        onUpdate(data.status, data.room);
      }
    },
    (error) => {
      onError?.(new Error(error.message));
    },
  );

  return unsubscribe;
}
