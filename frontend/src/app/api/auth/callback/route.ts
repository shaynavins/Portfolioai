import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get("code");
  const token = searchParams.get("token");

  // If backend already redirected with token, just pass it through
  if (token) {
    const response = NextResponse.redirect(
      new URL(`/dashboard?token=${encodeURIComponent(token)}`, request.url)
    );
    response.cookies.set("portfolioai_token", decodeURIComponent(token), {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 7 * 24 * 60 * 60,
    });
    return response;
  }

  if (!code) {
    return NextResponse.json({ error: "No authorization code" }, { status: 400 });
  }

  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    
    // Redirect to backend to handle GitHub OAuth
    return NextResponse.redirect(
      new URL(`/api/auth/github/callback?code=${code}`, API_URL)
    );
  } catch (error) {
    console.error("Auth callback error:", error);
    return NextResponse.json(
      { error: "Authentication failed" },
      { status: 500 }
    );
  }
}
