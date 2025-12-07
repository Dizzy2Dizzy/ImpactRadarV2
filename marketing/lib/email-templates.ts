// Email templates for onboarding sequences

export type EmailTemplate = {
  subject: string;
  html: string;
  text: string;
};

export function getWelcomeEmail(userEmail: string, userName?: string): EmailTemplate {
  const name = userName || userEmail.split('@')[0];
  
  return {
    subject: "Welcome to Impact Radar - Your Event-Driven Trading Journey Starts Now",
    html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to Impact Radar</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0a0a0a; color: #ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1a1a1a; border-radius: 16px; border: 1px solid #2a2a2a;">
          
          <!-- Header -->
          <tr>
            <td style="padding: 40px 40px 20px; text-align: center;">
              <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #00e5ff;">
                Welcome to Impact Radar
              </h1>
            </td>
          </tr>
          
          <!-- Body -->
          <tr>
            <td style="padding: 20px 40px;">
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #e0e0e0;">
                Hi ${name},
              </p>
              
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #e0e0e0;">
                Thank you for joining Impact Radar! You now have access to the most advanced event-driven signal engine for equity and biotech traders.
              </p>
              
              <p style="margin: 0 0 24px; font-size: 16px; line-height: 1.6; color: #e0e0e0;">
                Here's what you can do right now:
              </p>
              
              <!-- Features -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
                <tr>
                  <td style="padding: 16px; background-color: #0a0a0a; border-radius: 8px; margin-bottom: 12px;">
                    <h3 style="margin: 0 0 8px; font-size: 16px; font-weight: 600; color: #00e5ff;">📊 Real-Time Event Feed</h3>
                    <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #a0a0a0;">
                      Access 650+ real events from SEC filings, FDA announcements, and company press releases.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 16px; background-color: #0a0a0a; border-radius: 8px; margin-bottom: 12px;">
                    <h3 style="margin: 0 0 8px; font-size: 16px; font-weight: 600; color: #00e5ff;">🎯 Impact Scoring</h3>
                    <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #a0a0a0;">
                      Every event scored 0-100 with directional confidence and ML-enhanced predictions (85%+ accuracy).
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 16px; background-color: #0a0a0a; border-radius: 8px;">
                    <h3 style="margin: 0 0 8px; font-size: 16px; font-weight: 600; color: #00e5ff;">🔔 Custom Alerts</h3>
                    <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #a0a0a0;">
                      Set up email and SMS alerts for high-impact events on your watchlist tickers.
                    </p>
                  </td>
                </tr>
              </table>
              
              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 32px 0;">
                <tr>
                  <td align="center">
                    <a href="https://impactradar.co/app" style="display: inline-block; padding: 16px 32px; background-color: #00e5ff; color: #000000; text-decoration: none; font-weight: 600; border-radius: 8px; font-size: 16px;">
                      Open Dashboard →
                    </a>
                  </td>
                </tr>
              </table>
              
              <p style="margin: 24px 0 0; font-size: 14px; line-height: 1.6; color: #a0a0a0;">
                Need help getting started? Check out our <a href="https://impactradar.co/guide" style="color: #00e5ff; text-decoration: none;">Quick Start Guide</a> or reply to this email.
              </p>
            </td>
          </tr>
          
          <!-- Footer -->
          <tr>
            <td style="padding: 32px 40px; border-top: 1px solid #2a2a2a; text-align: center;">
              <p style="margin: 0 0 8px; font-size: 14px; color: #606060;">
                Impact Radar - Event-Driven Signal Engine
              </p>
              <p style="margin: 0; font-size: 12px; color: #404040;">
                <a href="https://impactradar.co/privacy" style="color: #606060; text-decoration: none;">Privacy Policy</a> · 
                <a href="https://impactradar.co/terms" style="color: #606060; text-decoration: none;">Terms of Service</a>
              </p>
            </td>
          </tr>
          
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
    `,
    text: `Welcome to Impact Radar!

Hi ${name},

Thank you for joining Impact Radar! You now have access to the most advanced event-driven signal engine for equity and biotech traders.

Here's what you can do right now:

📊 Real-Time Event Feed
Access 650+ real events from SEC filings, FDA announcements, and company press releases.

🎯 Impact Scoring
Every event scored 0-100 with directional confidence and ML-enhanced predictions (85%+ accuracy).

🔔 Custom Alerts
Set up email and SMS alerts for high-impact events on your watchlist tickers.

Get started: https://impactradar.co/app

Need help? Check out our Quick Start Guide: https://impactradar.co/guide

Best regards,
The Impact Radar Team
    `,
  };
}

export function getDay2OnboardingEmail(userName?: string): EmailTemplate {
  const name = userName || 'there';
  
  return {
    subject: "Quick Win: Set Up Your First Alert in 2 Minutes",
    html: `
<!DOCTYPE html>
<html>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0a0a0a; color: #ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1a1a1a; border-radius: 16px; border: 1px solid #2a2a2a;">
          <tr>
            <td style="padding: 40px;">
              <h2 style="margin: 0 0 20px; font-size: 24px; color: #00e5ff;">Never miss a high-impact event again</h2>
              
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #e0e0e0;">
                Hi ${name},
              </p>
              
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #e0e0e0;">
                You're now tracking market-moving events, but are you getting notified instantly when they happen?
              </p>
              
              <p style="margin: 0 0 24px; font-size: 16px; line-height: 1.6; color: #e0e0e0;">
                <strong>Set up your first alert in 2 minutes:</strong>
              </p>
              
              <ol style="margin: 0 0 24px; padding-left: 20px; font-size: 15px; line-height: 1.8; color: #e0e0e0;">
                <li>Add tickers to your watchlist (e.g., NVDA, AAPL, MRNA)</li>
                <li>Click "Create Alert" and choose your criteria (Impact Score ≥ 70)</li>
                <li>Select delivery method (Email or SMS)</li>
                <li>You're done! 🎉</li>
              </ol>
              
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 32px 0;">
                <tr>
                  <td align="center">
                    <a href="https://impactradar.co/app?tab=alerts" style="display: inline-block; padding: 16px 32px; background-color: #00e5ff; color: #000000; text-decoration: none; font-weight: 600; border-radius: 8px; font-size: 16px;">
                      Create Your First Alert →
                    </a>
                  </td>
                </tr>
              </table>
              
              <p style="margin: 24px 0 0; font-size: 14px; line-height: 1.6; color: #a0a0a0;">
                Pro tip: Start with high-impact events (score ≥ 70) to avoid alert fatigue.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
    `,
    text: `Never miss a high-impact event again

Hi ${name},

You're now tracking market-moving events, but are you getting notified instantly when they happen?

Set up your first alert in 2 minutes:

1. Add tickers to your watchlist (e.g., NVDA, AAPL, MRNA)
2. Click "Create Alert" and choose your criteria (Impact Score ≥ 70)
3. Select delivery method (Email or SMS)
4. You're done! 🎉

Create your first alert: https://impactradar.co/app?tab=alerts

Pro tip: Start with high-impact events (score ≥ 70) to avoid alert fatigue.

Best,
Impact Radar Team
    `,
  };
}

export function getDay5ProUpgradeEmail(userName?: string): EmailTemplate {
  const name = userName || 'there';
  
  return {
    subject: "Unlock Real-Time Alerts & ML Predictions (2 Days Left on Trial)",
    html: `
<!DOCTYPE html>
<html>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0a0a0a; color: #ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1a1a1a; border-radius: 16px; border: 1px solid #2a2a2a;">
          <tr>
            <td style="padding: 40px;">
              <h2 style="margin: 0 0 20px; font-size: 24px; color: #00e5ff;">Your trial ends in 2 days</h2>
              
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #e0e0e0;">
                Hi ${name},
              </p>
              
              <p style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #e0e0e0;">
                You've been using Impact Radar for 5 days. Here's what you're getting with Pro:
              </p>
              
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 24px 0;">
                <tr>
                  <td style="padding: 12px; background-color: #0a0a0a; border-left: 3px solid #00e5ff;">
                    <strong style="color: #00e5ff;">✓</strong> <span style="color: #e0e0e0;">Real-time alerts (zero delay)</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 12px; background-color: #0a0a0a; border-left: 3px solid #00e5ff;">
                    <strong style="color: #00e5ff;">✓</strong> <span style="color: #e0e0e0;">ML-enhanced predictions (85%+ accuracy)</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 12px; background-color: #0a0a0a; border-left: 3px solid #00e5ff;">
                    <strong style="color: #00e5ff;">✓</strong> <span style="color: #e0e0e0;">Unlimited watchlists</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 12px; background-color: #0a0a0a; border-left: 3px solid #00e5ff;">
                    <strong style="color: #00e5ff;">✓</strong> <span style="color: #e0e0e0;">Backtesting & correlation analysis</span>
                  </td>
                </tr>
              </table>
              
              <table width="100%" cellpadding="0" cellspacing="0" style="margin: 32px 0;">
                <tr>
                  <td align="center">
                    <a href="https://impactradar.co/pricing" style="display: inline-block; padding: 16px 32px; background-color: #00e5ff; color: #000000; text-decoration: none; font-weight: 600; border-radius: 8px; font-size: 16px;">
                      Upgrade to Pro - $49/mo →
                    </a>
                  </td>
                </tr>
              </table>
              
              <p style="margin: 24px 0 0; font-size: 14px; line-height: 1.6; color: #a0a0a0; text-align: center;">
                Cancel anytime. No questions asked.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
    `,
    text: `Your trial ends in 2 days

Hi ${name},

You've been using Impact Radar for 5 days. Here's what you're getting with Pro:

✓ Real-time alerts (zero delay)
✓ ML-enhanced predictions (85%+ accuracy)
✓ Unlimited watchlists
✓ Backtesting & correlation analysis

Upgrade to Pro - $49/mo: https://impactradar.co/pricing

Cancel anytime. No questions asked.

Best,
Impact Radar Team
    `,
  };
}
