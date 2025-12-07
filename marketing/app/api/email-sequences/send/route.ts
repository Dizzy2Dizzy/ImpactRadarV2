import { NextResponse } from "next/server";
import { Resend } from "resend";
import {
  getWelcomeEmail,
  getDay2OnboardingEmail,
  getDay5ProUpgradeEmail,
} from "@/lib/email-templates";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    // Guard: Check if RESEND_API_KEY is configured before instantiating Resend
    if (!process.env.RESEND_API_KEY) {
      logger.error("Cannot send email: RESEND_API_KEY not configured");
      return NextResponse.json(
        { error: "Email service not configured. Please contact support." },
        { status: 503 }
      );
    }

    // Initialize Resend only after confirming API key exists (prevents crash)
    const resend = new Resend(process.env.RESEND_API_KEY);

    const { userId, userEmail, userName, templateName } = await request.json();

    if (!userEmail || !templateName) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    let emailTemplate;
    switch (templateName) {
      case "welcome":
        emailTemplate = getWelcomeEmail(userEmail, userName);
        break;
      case "day2-alerts":
        emailTemplate = getDay2OnboardingEmail(userName);
        break;
      case "day5-upgrade":
        emailTemplate = getDay5ProUpgradeEmail(userName);
        break;
      default:
        return NextResponse.json(
          { error: "Unknown template" },
          { status: 400 }
        );
    }

    const { data, error } = await resend.emails.send({
      from: "Impact Radar <onboarding@impactradar.co>",
      to: [userEmail],
      subject: emailTemplate.subject,
      html: emailTemplate.html,
      text: emailTemplate.text,
    });

    if (error) {
      logger.error("Resend error", { error });
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    logger.info("Email sent successfully", { templateName, userEmail, emailId: data?.id });

    return NextResponse.json({
      success: true,
      emailId: data?.id,
    });
  } catch (error) {
    logger.error("Email send error", { error });
    return NextResponse.json(
      { error: "Failed to send email" },
      { status: 500 }
    );
  }
}
