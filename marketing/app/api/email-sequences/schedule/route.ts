import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { scheduledEmails } from "@/lib/schema";
import { 
  onboardingSequence, 
  calculateNextEmailDate 
} from "@/lib/email-scheduler";
import { logger } from "@/lib/logger";

// NOTE: This endpoint requires the scheduled_emails table to exist in the database.
// If you encounter a "table does not exist" error, run: npm run db:push
// This will create the required database tables based on the schema.
export async function POST(request: Request) {
  try {
    // Guard: Check if RESEND_API_KEY is configured
    if (!process.env.RESEND_API_KEY) {
      logger.error("Cannot schedule emails: RESEND_API_KEY not configured");
      return NextResponse.json(
        { error: "Email service not configured. Please contact support." },
        { status: 503 }
      );
    }

    const body = await request.json();
    const { userId, userEmail, userName, sequence } = body;

    // Validate required fields
    if (!userId || !userEmail) {
      return NextResponse.json(
        { error: "Missing required fields: userId and userEmail are required" },
        { status: 400 }
      );
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(userEmail)) {
      return NextResponse.json(
        { error: "Invalid email format" },
        { status: 400 }
      );
    }

    // Currently only support onboarding sequence
    if (sequence !== "onboarding") {
      return NextResponse.json(
        { error: "Invalid sequence type. Supported: 'onboarding'" },
        { status: 400 }
      );
    }

    const signupDate = new Date();
    const scheduledEmailsData = [];

    // Create scheduled email records for each step in the sequence
    for (const step of onboardingSequence) {
      const scheduledFor = calculateNextEmailDate(signupDate, step.delayDays);

      try {
        const [scheduledEmail] = await db
          .insert(scheduledEmails)
          .values({
            userId: parseInt(userId),
            userEmail,
            userName: userName || null,
            templateName: step.templateName,
            scheduledFor,
            status: "pending",
          })
          .returning();

        scheduledEmailsData.push({
          id: scheduledEmail.id,
          templateName: step.templateName,
          scheduledFor: scheduledFor.toISOString(),
          delayDays: step.delayDays,
        });

        logger.info("Email scheduled successfully", {
          templateName: step.templateName,
          userId,
          emailId: scheduledEmail.id,
          scheduledFor: scheduledFor.toISOString(),
        });
      } catch (dbError: any) {
        // Check for missing table error
        const errorMessage = dbError?.message || String(dbError);
        if (errorMessage.includes("does not exist") || 
            errorMessage.includes("relation") || 
            errorMessage.includes("no such table")) {
          logger.error("Database table 'scheduled_emails' does not exist", { error: dbError });
          return NextResponse.json(
            { 
              error: "Database table 'scheduled_emails' does not exist",
              details: "Please run 'npm run db:push' to create the required database tables",
              instruction: "This error occurs when the database schema hasn't been applied. Run the database migration command to fix this."
            },
            { status: 503 }
          );
        }
        
        logger.error("Database error scheduling email", { templateName: step.templateName, error: dbError });
        // Continue scheduling other emails even if one fails (for non-critical errors)
      }
    }

    if (scheduledEmailsData.length === 0) {
      return NextResponse.json(
        { error: "Failed to schedule any emails" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      scheduled: scheduledEmailsData,
      message: `Successfully scheduled ${scheduledEmailsData.length} emails`,
    });
  } catch (error) {
    logger.error("Email schedule error", { error });
    return NextResponse.json(
      { error: "Failed to schedule emails" },
      { status: 500 }
    );
  }
}

// GET endpoint to retrieve scheduled emails for a user
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const userId = searchParams.get("userId");

    if (!userId) {
      return NextResponse.json(
        { error: "Missing userId parameter" },
        { status: 400 }
      );
    }

    try {
      const userScheduledEmails = await db.query.scheduledEmails.findMany({
        where: (scheduledEmails, { eq }) => eq(scheduledEmails.userId, parseInt(userId)),
        orderBy: (scheduledEmails, { asc }) => [asc(scheduledEmails.scheduledFor)],
      });

      return NextResponse.json({
        success: true,
        scheduledEmails: userScheduledEmails,
      });
    } catch (dbError: any) {
      // Check for missing table error
      const errorMessage = dbError?.message || String(dbError);
      if (errorMessage.includes("does not exist") || 
          errorMessage.includes("relation") || 
          errorMessage.includes("no such table")) {
        logger.error("Database table 'scheduled_emails' does not exist", { error: dbError });
        return NextResponse.json(
          { 
            error: "Database table 'scheduled_emails' does not exist",
            details: "Please run 'npm run db:push' to create the required database tables",
            instruction: "This error occurs when the database schema hasn't been applied. Run the database migration command to fix this."
          },
          { status: 503 }
        );
      }
      
      // Re-throw other database errors to be caught by outer catch
      throw dbError;
    }
  } catch (error) {
    logger.error("Error fetching scheduled emails", { error });
    return NextResponse.json(
      { error: "Failed to fetch scheduled emails" },
      { status: 500 }
    );
  }
}
