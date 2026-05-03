import { Redirect } from "expo-router";
import { useUserProfileStore } from "@/store/userProfileStore";

export default function IndexPage() {
  const profile = useUserProfileStore((state) => state.profile);

  if (!profile) {
    return <Redirect href="/profile-setup" />;
  }

  if (!profile.is_profile_complete) {
    return <Redirect href="/onboarding" />;
  }

  return <Redirect href="/landing" />;
}