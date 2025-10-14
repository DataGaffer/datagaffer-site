const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // ✅ Only use service role key server-side
);

exports.handler = async (event) => {
  try {
    if (event.httpMethod !== "POST") {
      return { statusCode: 405, body: "Method Not Allowed" };
    }

    const { user_id } = JSON.parse(event.body);
    if (!user_id) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: "Missing user_id" }),
      };
    }

    // 🔎 Fetch customer_id and email from Supabase
    const { data: profile, error } = await supabase
      .from("profiles")
      .select("customer_id, email")
      .eq("id", user_id)
      .single();

    if (error) {
      console.error("❌ Supabase lookup error:", error.message);
      return { statusCode: 400, body: JSON.stringify({ error: error.message }) };
    }

    if (!profile?.customer_id) {
      // No Stripe customer yet → redirect to subscribe page
      return {
        statusCode: 200,
        body: JSON.stringify({ redirect: "/subscribe.html" }),
      };
    }

    // ✅ Create a Stripe billing portal session
    const portalSession = await stripe.billingPortal.sessions.create({
      customer: profile.customer_id,
      return_url: `${process.env.SITE_URL}/dashboard.html`,
    });

    return {
      statusCode: 200,
      body: JSON.stringify({ url: portalSession.url }),
    };
  } catch (err) {
    console.error("❌ Portal session error:", err);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "Internal server error" }),
    };
  }
};



