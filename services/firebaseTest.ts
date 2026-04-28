import { getDatabase, get, ref, set } from "firebase/database";

export async function verifyFirebaseConnection(): Promise<void> {
  const db = getDatabase();
  const testRef = ref(db, "_connection_test");

  await set(testRef, { ts: Date.now() });
  const snap = await get(testRef);

  console.log("[Firebase Test] Connection OK. Value:", snap.val());
}
