import { clerkMiddleware, createRouteMatcher, clerkClient } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher([
  "/login(.*)",
  "/signup(.*)",
  "/",
  "/pricing(.*)",
  "/privacy(.*)",
  "/terms(.*)",
]);

const isAdminRoute = createRouteMatcher(["/admin(.*)"]);

export default clerkMiddleware(async (auth, request) => {
  // Public routes — no auth needed
  if (isPublicRoute(request)) return NextResponse.next();

  const { userId } = await auth();

  // Not logged in — redirect to login
  if (!userId) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Admin routes — fetch user directly from Clerk API (bypasses JWT cache)
  if (isAdminRoute(request)) {
    try {
      const client = await clerkClient();
      const user = await client.users.getUser(userId);
      const role = (user.publicMetadata as { role?: string })?.role;

      console.log("[middleware] userId:", userId, "role:", role);

      if (role !== "admin") {
        console.log("[middleware] NOT admin — redirecting to /dashboard");
        return NextResponse.redirect(new URL("/dashboard", request.url));
      }

      console.log("[middleware] ADMIN ACCESS GRANTED ✅");
    } catch (e) {
      console.error("[middleware] Error:", e);
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!.*\\..*|_next).*)", "/", "/(api|trpc)(.*)"],
};