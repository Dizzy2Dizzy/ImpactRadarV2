// Email scheduling service for onboarding sequences

export type EmailSequenceStep = {
  id: string;
  delayDays: number;
  templateName: 'welcome' | 'day2-alerts' | 'day5-upgrade';
  condition?: (user: any) => boolean;
};

export const onboardingSequence: EmailSequenceStep[] = [
  {
    id: 'welcome',
    delayDays: 0, // Send immediately
    templateName: 'welcome',
  },
  {
    id: 'day2-alerts',
    delayDays: 2,
    templateName: 'day2-alerts',
    condition: (user) => !user.hasCreatedAlert, // Only if no alert created
  },
  {
    id: 'day5-upgrade',
    delayDays: 5,
    templateName: 'day5-upgrade',
    condition: (user) => user.plan === 'free' && user.isTrialing, // Only for trial users
  },
];

export async function scheduleOnboardingEmails(userId: string, userEmail: string) {
  // This would integrate with a job queue system like:
  // - BullMQ
  // - Celery
  // - AWS SQS
  // - Vercel Cron
  
  // For now, we'll create a database record that a cron job can process
  try {
    const response = await fetch('/api/email-sequences/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userId,
        userEmail,
        sequence: 'onboarding',
      }),
    });

    if (!response.ok) {
      console.error('Failed to schedule onboarding emails');
    }
  } catch (error) {
    console.error('Error scheduling onboarding emails:', error);
  }
}

export function calculateNextEmailDate(signupDate: Date, delayDays: number): Date {
  const nextDate = new Date(signupDate);
  nextDate.setDate(nextDate.getDate() + delayDays);
  return nextDate;
}
