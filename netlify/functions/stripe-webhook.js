// netlify/functions/stripe-webhook.js
const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // ⚠️ must be service role key, NOT anon
);

exports.handler = async (event) => {
  console.log("⚡ Incoming webhook event");
  console.log("Headers:", event.headers);
  console.log("isBase64Encoded:", event.isBase64Encoded);

  // Stripe signature header
  const sig = event.headers["stripe-signature"];
  console.log("Stripe signature header:", sig);

  let stripeEvent;
  try {
    // Use rawBody if Netlify provides it, otherwise fall back
    const rawBody = event.rawBody || event.body;
    console.log("Using raw body length:", rawBody.length);

    stripeEvent = stripe.webhooks.constructEvent(
      rawBody,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("❌ Webhook signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  console.log("✅ Verified Stripe event:", stripeEvent.type);

  // ✅ Handle checkout session completed
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;

    const email = session.customer_details?.email;
    if (!email) {
      console.error("⚠️ No email found in session");
      return { statusCode: 400, body: "No email found" };
    }

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

  return { statusCode: 200, body: "success" };
};

