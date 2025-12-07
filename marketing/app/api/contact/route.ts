import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { contactMessages } from "@/lib/schema";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { name, email, message } = body;

    if (!name || !name.trim()) {
      return NextResponse.json(
        { error: "Name is required" },
        { status: 400 }
      );
    }

    if (!email || !email.includes("@")) {
      return NextResponse.json(
        { error: "Valid email is required" },
        { status: 400 }
      );
    }

    if (!message || !message.trim()) {
      return NextResponse.json(
        { error: "Message is required" },
        { status: 400 }
      );
    }

    await db.insert(contactMessages).values({
      name: name.trim(),
      email: email.trim(),
      message: message.trim(),
    });

    return NextResponse.json(
      { success: true, message: "Message sent successfully!" },
      { status: 201 }
    );
  } catch (error) {
    logger.error("Contact form error", { error });
    return NextResponse.json(
      { error: "Failed to send message" },
      { status: 500 }
    );
  }
}
