const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

exports.handler = async (event) => {
  try {
    const { user_id } = JSON.parse(event.body);

    // look up customer_id from profiles
    const { data, error } = await supabase
      .from("profiles")
      .select("customer_id, email")
      .eq("id", user_id)
      .single();

    if (error || !data?.customer_id) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: "No customer found" }),
      };
    }

    // create billing portal session
    const portalSession = await stripe.billingPortal.sessions.create({
      customer: data.customer_id,
      return_url: "https://www.datagaffer.com/index.html", // 🔹 where to send them back
    });

    return {
      statusCode: 200,
      body: JSON.stringify({ url: portalSession.url }),
    };
  } catch (err) {
    console.error("Portal session error:", err);
    return { statusCode: 500, body: JSON.stringify({ error: err.message }) };
  }
};


