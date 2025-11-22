import os
from supabase import create_client, Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def send_email(to_email, subject, content):
    message = Mail(
    from_email=('newsletter@em3764.datagaffer.com', 'DataGaffer'),
    to_emails=to_email,
    subject=subject,
    html_content=content
)

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"✔ Sent to {to_email} ({response.status_code})")
    except Exception as e:
        print(f"❌ Error sending to {to_email}: {str(e)}")


def send_newsletter():
    # Pull all emails from Supabase profiles table
    emails = supabase.table("profiles").select("email").execute()

    if not emails.data:
        print("No emails found.")
        return

    print(f"📧 Sending newsletter to {len(emails.data)} users...")

    subject = "This Weekend’s Projections — DataGaffer"

    content = """
<div style="width:100%; background:#f7f7f7; padding:0; margin:0;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" 
         style="margin:0; padding:0; background:#f7f7f7;">
    <tr>
      <td align="center" style="margin:0; padding:0;">

        <table width="600" cellpadding="0" cellspacing="0" border="0" 
               style="background:white; padding:0; margin:0; border-radius:12px;">

          <!-- LOGO -->
          <tr>
            <td align="center" style="padding:25px 0 10px 0;">
              <img src="https://cdn.prod.website-files.com/682236b4aa8cdb4803142afd/68b8aa71d38f0c8d4c140700_everything-236.png"
                   width="130"
                   alt="DataGaffer Logo"
                   style="display:block; margin:0 auto;">
            </td>
          </tr>

          <!-- TITLE -->
          <tr>
            <td style="padding:0 30px 10px 30px; text-align:center;">
              <h2 style="font-size:26px; margin:0; color:#004225; font-weight:700;">
                This Weekend’s Projections — DataGaffer
              </h2>
            </td>
          </tr>

          <!-- SUBTITLE -->
          <tr>
            <td style="padding:0 30px 10px 30px; text-align:center;">
              <h3 style="font-size:18px; margin:0; color:#222; font-weight:600;">
                Your Weekend Simulations Are Ready!
              </h3>
            </td>
          </tr>

          <!-- BODY TEXT -->
          <tr>
            <td style="padding:0 30px 20px 30px; font-size:17px; line-height:1.5; color:#333;">
              Visit <a href="https://www.datagaffer.com" style="color:#004225; font-weight:600;">
                DataGaffer.com
              </a>
              for today’s updated projections, sim cards, xG data, and player models.<br><br>
              Thanks for being part of the DG Community!
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 30px 30px 30px; text-align:center; font-size:13px; color:#777;">
              <hr style="border:0; border-top:1px solid #ddd; margin-bottom:10px;">
              DataGaffer LLC<br>
              Jackson, New Jersey<br>
              © 2025 DataGaffer. All rights reserved.
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>
</div>
"""

    count = 0
    for row in emails.data:
        send_email(row["email"], subject, content)
        count += 1

        # Print progress every 50 sends
        if count % 50 == 0:
            print(f"🟩 {count} sent...")

    print("🎉 Done sending all emails!")


if __name__ == "__main__":
    send_newsletter()
