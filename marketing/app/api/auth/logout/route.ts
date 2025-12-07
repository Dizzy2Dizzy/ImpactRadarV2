import { NextResponse } from "next/server";
import { deleteSession } from "@/lib/auth";
import { logger } from "@/lib/logger";

export async function POST() {
  try {
    await deleteSession();
    return NextResponse.json({ success: true }, { status: 200 });
  } catch (error) {
    logger.error("Logout error", { error });
    return NextResponse.json({ error: "Failed to logout" }, { status: 500 });
  }
}
