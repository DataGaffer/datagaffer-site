// netlify/functions/stripe-webhook.js
const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // ⚠️ must be service role key
);

exports.handler = async (event) => {
  // ✅ Ensure raw body for Stripe signature validation
  let body = event.body;
  if (event.isBase64Encoded) {
    body = Buffer.from(body, "base64").toString("utf8");
  }

  const sig = event.headers["stripe-signature"];
  let stripeEvent;

  try {
    stripeEvent = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("⚠️ Webhook signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  // ✅ Handle checkout session completed
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;

    // Always get customer from Stripe to ensure correct email
    const customer = await stripe.customers.retrieve(session.customer);
    const email = customer.email || session.customer_details?.email;

    if (!email) {
      console.error("⚠️ No email found in session");
      return { statusCode: 400, body: "No email found" };
    }

    // Update Supabase profile
    const { error } = await supabase
      .from("profiles")
      .update({ is_subscribed: true })
      .eq("email", email);

    if (error) {
      console.error("❌ Error updating Supabase:", error);
      return { statusCode: 500, body: "Supabase update failed" };
    }

    console.log(`✅ Subscription activated for ${email}`);
  }

  // ✅ Handle subscription canceled
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;
    const customer = await stripe.customers.retrieve(subscription.customer);
    const email = customer.email;

    if (email) {
      const { error } = await supabase
        .from("profiles")
        .update({ is_subscribed: false })
        .eq("email", email);

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log(`✅ Subscription canceled for ${email}`);
    }
  }

  return { statusCode: 200, body: "success" };
};


