import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import dynamic from "next/dynamic";

// Dynamic import with ssr:false — fixes hydration mismatch
const LandingPage = dynamic(() => import("@/components/LandingPage"), {
  ssr: false,
});

export default async function Home() {
  const { userId } = await auth();

  // Logged in → dashboard
  if (userId) redirect("/dashboard");

  // Logged out → landing page
  return <LandingPage />;
}