// netlify/functions/stripe-webhook.js
const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // ⚠️ must be service role key, NOT anon
);

exports.handler = async (event) => {
  console.log("⚡ Incoming webhook event");
  console.log("Headers:", JSON.stringify(event.headers, null, 2));
  console.log("isBase64Encoded:", event.isBase64Encoded);

  let body = event.body;
  if (event.isBase64Encoded) {
    body = Buffer.from(body, "base64").toString("utf8");
  }
  console.log("Body (truncated to 500 chars):", body.slice(0, 500));

  const sig = event.headers["stripe-signature"];
  console.log("Stripe signature header:", sig);

  let stripeEvent;
  try {
    stripeEvent = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
    console.log("✅ Stripe event verified:", stripeEvent.type);
  } catch (err) {
    console.error("❌ Webhook signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  // ✅ Handle checkout session completed
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;
    const email = session.customer_details?.email;

    console.log("Checkout session completed for:", email);

    if (email) {
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
  }

  // ✅ Handle subscription deleted
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;
    const customer = await stripe.customers.retrieve(subscription.customer);
    const email = customer.email;

    console.log("Subscription canceled for:", email);

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


