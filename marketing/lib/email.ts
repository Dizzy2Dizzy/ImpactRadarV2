import { Resend } from 'resend';

async function getCredentials(): Promise<{ apiKey: string; fromEmail: string }> {
  const hostname = process.env.REPLIT_CONNECTORS_HOSTNAME;
  const xReplitToken = process.env.REPL_IDENTITY 
    ? 'repl ' + process.env.REPL_IDENTITY 
    : process.env.WEB_REPL_RENEWAL 
    ? 'depl ' + process.env.WEB_REPL_RENEWAL 
    : null;

  if (!xReplitToken) {
    throw new Error('X_REPLIT_TOKEN not found for repl/depl');
  }

  const connectionSettings = await fetch(
    'https://' + hostname + '/api/v2/connection?include_secrets=true&connector_names=resend',
    {
      headers: {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': xReplitToken
      }
    }
  ).then(res => res.json()).then(data => data.items?.[0]);

  if (!connectionSettings || !connectionSettings.settings.api_key) {
    throw new Error('Resend not connected');
  }
  
  return {
    apiKey: connectionSettings.settings.api_key, 
    fromEmail: connectionSettings.settings.from_email
  };
}

export async function getResendClient() {
  const { apiKey, fromEmail } = await getCredentials();
  return {
    client: new Resend(apiKey),
    fromEmail
  };
}

export async function sendVerificationEmail(email: string, code: string): Promise<void> {
  const { client, fromEmail } = await getResendClient();
  
  const expiresInMinutes = 15;
  
  console.log(`[EMAIL DEBUG] Attempting to send email to ${email} from ${fromEmail}`);
  
  try {
    const response = await client.emails.send({
      from: fromEmail,
      to: email,
      subject: 'Verify your Impact Radar account',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0a0a0a; color: #e5e5e5;">
            <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
              <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="color: #60a5fa; margin: 0; font-size: 24px; font-weight: 700;">Impact Radar</h1>
              </div>
              
              <div style="background-color: #1a1a1a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 32px;">
                <h2 style="margin: 0 0 16px 0; font-size: 20px; font-weight: 600; color: #e5e5e5;">Verify your email address</h2>
                
                <p style="margin: 0 0 24px 0; font-size: 14px; color: #a3a3a3; line-height: 1.5;">
                  Enter this verification code to complete your account setup:
                </p>
                
                <div style="background-color: #0a0a0a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 24px; text-align: center; margin-bottom: 24px;">
                  <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #60a5fa; font-family: 'Courier New', monospace;">
                    ${code}
                  </div>
                </div>
                
                <p style="margin: 0 0 16px 0; font-size: 14px; color: #a3a3a3; line-height: 1.5;">
                  This code will expire in <strong style="color: #e5e5e5;">${expiresInMinutes} minutes</strong>.
                </p>
                
                <div style="background-color: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.2); border-radius: 8px; padding: 16px; margin-top: 24px;">
                  <p style="margin: 0; font-size: 13px; color: #fbbf24; line-height: 1.5;">
                    <strong>Security Notice:</strong> Never share this code with anyone. Impact Radar will never ask you for this code.
                  </p>
                </div>
              </div>
              
              <div style="text-align: center; margin-top: 32px; padding-top: 24px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
                <p style="margin: 0; font-size: 12px; color: #737373;">
                  If you didn't request this code, you can safely ignore this email.
                </p>
              </div>
            </div>
          </body>
        </html>
      `,
    });
    
    console.log(`[EMAIL DEBUG] Resend response:`, JSON.stringify(response));
    
    if (response.error) {
      console.error(`[EMAIL ERROR] Resend returned error:`, response.error);
      throw new Error(`Email sending failed: ${JSON.stringify(response.error)}`);
    }
    
    console.log(`[EMAIL SUCCESS] Email sent successfully to ${email}, ID: ${response.data?.id}`);
  } catch (error) {
    console.error(`[EMAIL EXCEPTION] Failed to send email to ${email}:`, error);
    throw error;
  }
}

export async function sendPasswordResetEmail(email: string, resetToken: string): Promise<void> {
  const { client, fromEmail } = await getResendClient();
  
  const resetUrl = `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:5000'}/reset-password?token=${resetToken}&email=${encodeURIComponent(email)}`;
  const expiresInMinutes = 60;
  
  console.log(`[EMAIL DEBUG] Attempting to send password reset email to ${email} from ${fromEmail}`);
  
  try {
    const response = await client.emails.send({
      from: fromEmail,
      to: email,
      subject: 'Reset your Impact Radar password',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0a0a0a; color: #e5e5e5;">
            <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
              <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="color: #60a5fa; margin: 0; font-size: 24px; font-weight: 700;">Impact Radar</h1>
              </div>
              
              <div style="background-color: #1a1a1a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 32px;">
                <h2 style="margin: 0 0 16px 0; font-size: 20px; font-weight: 600; color: #e5e5e5;">Reset your password</h2>
                
                <p style="margin: 0 0 24px 0; font-size: 14px; color: #a3a3a3; line-height: 1.5;">
                  We received a request to reset your password. Click the button below to create a new password:
                </p>
                
                <div style="text-align: center; margin: 32px 0;">
                  <a href="${resetUrl}" style="display: inline-block; background-color: #60a5fa; color: #0a0a0a; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                    Reset Password
                  </a>
                </div>
                
                <p style="margin: 0 0 16px 0; font-size: 14px; color: #a3a3a3; line-height: 1.5;">
                  This link will expire in <strong style="color: #e5e5e5;">${expiresInMinutes} minutes</strong>.
                </p>
                
                <p style="margin: 0 0 24px 0; font-size: 13px; color: #737373; line-height: 1.5;">
                  If the button doesn't work, copy and paste this link into your browser:
                </p>
                
                <div style="background-color: #0a0a0a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 12px; word-break: break-all;">
                  <a href="${resetUrl}" style="color: #60a5fa; text-decoration: none; font-size: 12px;">
                    ${resetUrl}
                  </a>
                </div>
                
                <div style="background-color: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.2); border-radius: 8px; padding: 16px; margin-top: 24px;">
                  <p style="margin: 0; font-size: 13px; color: #fbbf24; line-height: 1.5;">
                    <strong>Security Notice:</strong> If you didn't request this password reset, you can safely ignore this email. Your password will not be changed.
                  </p>
                </div>
              </div>
              
              <div style="text-align: center; margin-top: 32px; padding-top: 24px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
                <p style="margin: 0; font-size: 12px; color: #737373;">
                  This email was sent because a password reset was requested for your Impact Radar account.
                </p>
              </div>
            </div>
          </body>
        </html>
      `,
    });
    
    console.log(`[EMAIL DEBUG] Resend response:`, JSON.stringify(response));
    
    if (response.error) {
      console.error(`[EMAIL ERROR] Resend returned error:`, response.error);
      throw new Error(`Email sending failed: ${JSON.stringify(response.error)}`);
    }
    
    console.log(`[EMAIL SUCCESS] Password reset email sent successfully to ${email}, ID: ${response.data?.id}`);
  } catch (error) {
    console.error(`[EMAIL EXCEPTION] Failed to send password reset email to ${email}:`, error);
    throw error;
  }
}
