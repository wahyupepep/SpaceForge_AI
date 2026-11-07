import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const hasSession = request.cookies.has("spaceforge_session");
  const isLogin = request.nextUrl.pathname === "/login";
  if (!hasSession && !isLogin) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (hasSession && isLogin) {
    return NextResponse.redirect(new URL("/projects", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // API requests include login/register and must reach FastAPI. Page redirects
  // must not turn API responses into HTML or prevent setting the session cookie.
  matcher: ["/((?!api/|api$|_next/static|_next/image|favicon.ico).*)"],
};
