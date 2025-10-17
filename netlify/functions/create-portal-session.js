const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

exports.handler = async (event) => {
  try {
    if (event.httpMethod !== "POST") {
      return { statusCode: 405, body: "Method Not Allowed" };
    }

    const { user_id } = JSON.parse(event.body);
    if (!user_id) {
      return { statusCode: 400, body: JSON.stringify({ error: "Missing user_id" }) };
    }

    // 🔎 Step 1: Try to find by id
    let { data: profile, error } = await supabase
      .from("profiles")
      .select("customer_id, email")
      .eq("id", user_id)
      .maybeSingle();

    // 🔎 Step 2: Fallback to find by auth user's email
    if ((!profile || !profile.customer_id) && !error) {
      const { data: userData } = await supabase.auth.admin.getUserById(user_id);
      const email = userData?.user?.email?.toLowerCase();
      if (email) {
        const { data: byEmail } = await supabase
          .from("profiles")
          .select("customer_id, email")
          .eq("email", email)
          .maybeSingle();
        profile = byEmail;
      }
    }

    if (!profile || !profile.customer_id) {
      return {
        statusCode: 200,
        body: JSON.stringify({ redirect: "/subscribe.html" }),
      };
    }

    // ✅ Create billing portal
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
      body: JSON.stringify({ error: err.message || "Internal server error" }),
    };
  }
};



